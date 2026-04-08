from __future__ import annotations

import json
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from .pncp_client import PNCPClientError
from .schemas import (
    HealthResponse,
    LocalBackfillRequest,
    MarketSearchRequest,
    MarketSearchResponse,
)
from .service import market_search, market_search_stream
from .local_index import backfill_local_index, local_index_stats, local_item_search, local_search

router = APIRouter(prefix="/pncp-research", tags=["pncp-research"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(ok=True)


@router.post("/market-search", response_model=MarketSearchResponse)
async def market_search_endpoint(body: MarketSearchRequest) -> MarketSearchResponse:
    try:
        data = await market_search(body)
        return MarketSearchResponse(**data)
    except PNCPClientError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/market-search/stream")
async def market_search_stream_endpoint(body: MarketSearchRequest):
    """
    Streaming NDJSON: envia progresso por página e resultado final.
    """
    async def event_gen():
        try:
            async for event in market_search_stream(body):
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except PNCPClientError as e:
            yield json.dumps({"type": "error", "detail": str(e)}, ensure_ascii=False) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "detail": str(e)}, ensure_ascii=False) + "\n"

    return StreamingResponse(event_gen(), media_type="application/x-ndjson")


@router.get("/local-index/stats")
async def local_index_stats_endpoint():
    try:
        return local_index_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/local-index/backfill")
async def local_index_backfill_endpoint(body: LocalBackfillRequest):
    try:
        return await backfill_local_index(
            months=body.months,
            max_paginas=body.max_paginas,
            tamanho_pagina=body.tamanho_pagina,
            uf=body.uf,
            codigo_municipio_ibge=body.codigo_municipio_ibge,
            include_items=body.include_items,
        )
    except PNCPClientError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/local-index/search")
async def local_index_search_endpoint(body: MarketSearchRequest):
    try:
        return local_search(
            body.termo_busca,
            uf=body.uf,
            codigo_modalidade=body.codigo_modalidade,
            limit=max(100, body.max_paginas * body.tamanho_pagina),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/local-index/search-items")
async def local_index_search_items_endpoint(body: MarketSearchRequest):
    try:
        return local_item_search(
            body.termo_busca,
            uf=body.uf,
            codigo_modalidade=body.codigo_modalidade,
            limit=max(200, body.max_paginas * body.tamanho_pagina),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def create_app() -> FastAPI:
    app = FastAPI(title="PNCP Researcher Service", version="1.0.0")
    app.include_router(router, prefix="/api")
    return app
