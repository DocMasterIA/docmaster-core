from __future__ import annotations

import asyncio
import json
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from .adapters.contracts import FederatedSearchQuery
from .adapters.federated import federated_search
from .config import (
    PNCP_IA_BASE_URL,
    PNCP_IA_ITEM_RESUMO_ENABLED,
    PNCP_IA_RERANK_BULK_ENABLED,
    PNCP_IA_RERANK_ENABLED,
    PNCP_LOCAL_DB_PATH,
    PNCP_LOCAL_RERANK_ENABLED,
    PNCP_SEARCH_CODE_REV,
    PNCP_SEARCH_QUALITY_FIRST,
)
from .local_index import (
    add_items_to_research_session,
    create_research_session,
    enrich_local_search_result,
    fts_index_status,
    get_research_session,
    list_research_sessions,
    local_index_stats,
    local_item_search,
    local_search,
    update_research_session,
)
from .pncp_client import PNCPClientError
from .schemas import (
    HealthResponse,
    MarketSearchRequest,
    MarketSearchResponse,
    ResearchSessionAddItemsRequest,
    ResearchSessionCreateRequest,
    ResearchSessionUpdateRequest,
)
from .search_diagnose import diagnose_intelligent_search
from .service import market_search, market_search_intelligent, market_search_stream
from .service_mode import service_name

researcher_router = APIRouter(prefix="/pncp-research", tags=["price-researcher"])


def _researcher_health() -> HealthResponse:
    db_path = (PNCP_LOCAL_DB_PATH or "").strip()
    on_volume = db_path.startswith("/data/pncp/")
    db_bytes = 0
    hint = "Modo pesquisador: leitura do índice; alimentação no price_index_feed_service."
    if db_path and os.path.isfile(db_path):
        try:
            db_bytes = int(os.path.getsize(db_path))
        except OSError:
            db_bytes = 0
    if db_bytes < 5_000_000:
        hint = f"{hint} Índice pequeno (<5 MB) — verifique feed."
    return HealthResponse(
        ok=True,
        service=service_name(),
        service_mode="researcher",
        search_code_rev=PNCP_SEARCH_CODE_REV,
        db_path=db_path,
        db_bytes=db_bytes,
        db_on_data_volume=on_volume,
        index_hint=hint,
        ingest=None,
        ia={
            "base_url": PNCP_IA_BASE_URL,
            "rerank_enabled": PNCP_IA_RERANK_ENABLED,
            "rerank_bulk_enabled": PNCP_IA_RERANK_BULK_ENABLED,
            "local_rerank_enabled": PNCP_LOCAL_RERANK_ENABLED,
            "item_resumo_enabled": PNCP_IA_ITEM_RESUMO_ENABLED,
            "search_quality_first": PNCP_SEARCH_QUALITY_FIRST,
            "search_code_rev": PNCP_SEARCH_CODE_REV,
        },
    )


@researcher_router.get("/health", response_model=HealthResponse)
async def researcher_health() -> HealthResponse:
    return _researcher_health()


@researcher_router.post("/market-search", response_model=MarketSearchResponse)
async def market_search_endpoint(body: MarketSearchRequest) -> MarketSearchResponse:
    try:
        data = await market_search(body)
        return MarketSearchResponse(**data)
    except PNCPClientError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@researcher_router.post("/market-search/intelligent/diagnose")
async def market_search_intelligent_diagnose_endpoint(body: MarketSearchRequest):
    try:
        return await diagnose_intelligent_search(body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@researcher_router.post("/market-search/intelligent", response_model=MarketSearchResponse)
async def market_search_intelligent_endpoint(body: MarketSearchRequest) -> MarketSearchResponse:
    try:
        from .config import PNCP_BULK_SEARCH_MAX_SECONDS, PNCP_BULK_USE_INTELLIGENT_PIPELINE
        from .service import _bulk_search_timeout_response

        if body.busca_lote and float(PNCP_BULK_SEARCH_MAX_SECONDS or 0) > 0:
            tmo = max(8.0, float(PNCP_BULK_SEARCH_MAX_SECONDS))
            if PNCP_BULK_USE_INTELLIGENT_PIPELINE:
                tmo = max(tmo, 120.0)
            try:
                data = await asyncio.wait_for(market_search_intelligent(body), timeout=tmo)
            except asyncio.TimeoutError:
                data = _bulk_search_timeout_response(body)
        else:
            data = await market_search_intelligent(body)
        return MarketSearchResponse(**data)
    except PNCPClientError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@researcher_router.post("/market-search/federated", response_model=MarketSearchResponse)
async def market_search_federated_endpoint(body: MarketSearchRequest) -> MarketSearchResponse:
    try:
        from .config import PNCP_BULK_SEARCH_MAX_SECONDS, PNCP_BULK_USE_INTELLIGENT_PIPELINE
        from .service import _bulk_search_timeout_response

        query = FederatedSearchQuery.from_market_request(
            body,
            fontes_habilitadas=body.fontes_habilitadas,
        )
        if body.busca_lote and float(PNCP_BULK_SEARCH_MAX_SECONDS or 0) > 0:
            tmo = max(8.0, float(PNCP_BULK_SEARCH_MAX_SECONDS))
            if PNCP_BULK_USE_INTELLIGENT_PIPELINE:
                tmo = max(tmo, 120.0)
            try:
                data = await asyncio.wait_for(federated_search(query), timeout=tmo)
            except asyncio.TimeoutError:
                data = _bulk_search_timeout_response(body)
        else:
            data = await federated_search(query)
        return MarketSearchResponse(**data)
    except PNCPClientError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@researcher_router.post("/market-search/stream")
async def market_search_stream_endpoint(body: MarketSearchRequest):
    async def event_gen():
        try:
            async for event in market_search_stream(body):
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except PNCPClientError as e:
            yield json.dumps({"type": "error", "detail": str(e)}, ensure_ascii=False) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "detail": str(e)}, ensure_ascii=False) + "\n"

    return StreamingResponse(event_gen(), media_type="application/x-ndjson")


@researcher_router.get("/price-sources")
async def list_price_sources_endpoint():
    from .adapters.registry import get_adapters, list_adapter_ids

    ids = list_adapter_ids()
    adapters = get_adapters(ids)
    return {
        "ok": True,
        "role": "researcher",
        "fontes": [a.capabilities() for a in adapters],
    }


@researcher_router.get("/price-platform-indexes")
async def list_price_platform_indexes_endpoint():
    from .adapters.registry import list_platform_index_catalog
    from .platform_index.crosslink_db import crosslink_stats

    return {
        "ok": True,
        "role": "researcher",
        "plataformas": list_platform_index_catalog(),
        "crosslink": crosslink_stats(),
    }


@researcher_router.get("/local-index/stats")
async def local_index_stats_read_endpoint():
    """
    Leitura do índice PNCP + totais das demais plataformas (ex.: TCE-RS).

    `total_itens` permanece PNCP-only (compat). O front usa
    `total_itens_todas_fontes` para o volume agregado indexado.
    """
    try:
        from .platform_index.aggregate_stats import attach_federated_item_totals

        return attach_federated_item_totals(local_index_stats())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@researcher_router.get("/local-index/fts-status")
async def local_index_fts_status_read_endpoint():
    try:
        return fts_index_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@researcher_router.post("/local-index/search")
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


@researcher_router.post("/local-index/search-items")
async def local_index_search_items_endpoint(body: MarketSearchRequest):
    try:
        result = local_item_search(
            body.termo_busca,
            uf=body.uf,
            municipio=body.municipio,
            recortes_geograficos=body.recortes_geograficos,
            codigo_modalidade=body.codigo_modalidade,
            limit=max(200, body.max_paginas * body.tamanho_pagina),
            somente_homologados=body.somente_homologados,
        )
        return await enrich_local_search_result(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# Legacy FastAPI sessions (Django é fonte de verdade para cotações)
@researcher_router.post("/research/sessions")
async def research_session_create_endpoint(body: ResearchSessionCreateRequest):
    try:
        return create_research_session(
            titulo=body.titulo,
            termo_busca=body.termo_busca,
            modelo_cotacao=body.modelo_cotacao,
            filtros=body.filtros,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@researcher_router.post("/research/cotacoes")
async def cotacao_create_endpoint(body: ResearchSessionCreateRequest):
    return await research_session_create_endpoint(body)


@researcher_router.get("/research/sessions")
async def research_session_list_endpoint(limit: int = 100):
    try:
        return list_research_sessions(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@researcher_router.get("/research/sessions/{sessao_id}")
async def research_session_get_endpoint(sessao_id: int):
    try:
        data = get_research_session(sessao_id)
        if not data.get("ok"):
            raise HTTPException(status_code=404, detail=data.get("error", "Sessão não encontrada."))
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@researcher_router.post("/research/sessions/{sessao_id}/items")
async def research_session_add_items_endpoint(sessao_id: int, body: ResearchSessionAddItemsRequest):
    try:
        data = add_items_to_research_session(sessao_id, body.itens)
        if not data.get("ok"):
            raise HTTPException(status_code=404, detail=data.get("error", "Sessão não encontrada."))
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@researcher_router.post("/research/sessions/{sessao_id}/update")
async def research_session_update_endpoint(sessao_id: int, body: ResearchSessionUpdateRequest):
    try:
        data = update_research_session(
            sessao_id,
            titulo=body.titulo,
            status=body.status,
            termo_busca=body.termo_busca,
            modelo_cotacao=body.modelo_cotacao,
        )
        if not data.get("ok"):
            raise HTTPException(status_code=404, detail=data.get("error", "Sessão não encontrada."))
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
