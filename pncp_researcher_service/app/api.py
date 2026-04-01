from __future__ import annotations

import json
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from .pncp_client import PNCPClientError
from .schemas import HealthResponse, MarketSearchRequest, MarketSearchResponse
from .service import market_search, market_search_stream

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


def create_app() -> FastAPI:
    app = FastAPI(title="PNCP Researcher Service", version="1.0.0")
    app.include_router(router, prefix="/api")
    return app
