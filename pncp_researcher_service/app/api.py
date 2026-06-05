from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from .config import PNCP_INGEST_WORKER_ENABLED
from .ingest_coverage import ingest_coverage_status
from .ingest_planner import plan_ingest_queue
from .ingest_worker import ingest_worker_loop, process_ingest_batch
from .pncp_client import PNCPClientError
from .schemas import (
    HealthResponse,
    IngestPlanRequest,
    LocalBackfillRequest,
    ResearchSessionAddItemsRequest,
    ResearchSessionCreateRequest,
    ResearchSessionUpdateRequest,
    MarketSearchRequest,
    MarketSearchResponse,
)
from .service import market_search, market_search_intelligent, market_search_stream
from .config import PNCP_LOCAL_DB_PATH
from .local_index import (
    add_items_to_research_session,
    backfill_local_index,
    create_research_session,
    get_research_session,
    list_research_sessions,
    update_research_session,
    local_index_stats,
    ingest_operational_status,
    local_index_operational_status,
    local_item_search,
    local_search,
    rebuild_fts_index,
    fts_index_status,
)

router = APIRouter(prefix="/pncp-research", tags=["pncp-research"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    db_path = (PNCP_LOCAL_DB_PATH or "").strip()
    on_volume = db_path.startswith("/data/pncp/")
    db_bytes = 0
    hint = ""
    if db_path and os.path.isfile(db_path):
        try:
            db_bytes = int(os.path.getsize(db_path))
        except OSError:
            db_bytes = 0
    if db_path.startswith("/tmp/"):
        hint = "AVISO: SQLite em /tmp — use PNCP_LOCAL_DB_PATH=/data/pncp/pncp_researcher_local.db e volume Docker."
    elif not on_volume:
        hint = "AVISO: db_path fora de /data/pncp — confira volume e docker-compose.pncp.override.yml."
    elif db_bytes < 5_000_000:
        hint = "Índice pequeno ou vazio (<5 MB) — confira volume correto (attach-pncp-volume.sh)."
    return HealthResponse(
        ok=True,
        db_path=db_path,
        db_bytes=db_bytes,
        db_on_data_volume=on_volume,
        index_hint=hint,
    )


@router.post("/market-search", response_model=MarketSearchResponse)
async def market_search_endpoint(body: MarketSearchRequest) -> MarketSearchResponse:
    try:
        data = await market_search(body)
        return MarketSearchResponse(**data)
    except PNCPClientError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/market-search/intelligent", response_model=MarketSearchResponse)
async def market_search_intelligent_endpoint(body: MarketSearchRequest) -> MarketSearchResponse:
    try:
        data = await market_search_intelligent(body)
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


@router.get("/local-index/ingest-status")
async def local_index_ingest_status_endpoint(uf: str | None = None):
    try:
        return ingest_operational_status(uf=uf)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/local-index/coverage")
async def local_index_coverage_endpoint():
    try:
        return ingest_coverage_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/local-index/ingest/plan")
async def local_index_ingest_plan_endpoint(body: IngestPlanRequest | None = None):
    try:
        req = body or IngestPlanRequest()
        return plan_ingest_queue(
            uf=req.uf,
            pages_per_scope=req.pages_per_scope,
            contracts_without_items_limit=req.contracts_without_items_limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/local-index/ingest/worker-tick")
async def local_index_ingest_worker_tick_endpoint():
    """Processa um lote da fila (útil para debug sem esperar o worker em background)."""
    try:
        return await process_ingest_batch()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/local-index/operational-status")
async def local_index_operational_status_endpoint(uf: str | None = None):
    try:
        return local_index_operational_status(uf=uf)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/local-index/fts-status")
async def local_index_fts_status_endpoint():
    try:
        return fts_index_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/local-index/fts-rebuild")
async def local_index_fts_rebuild_endpoint():
    try:
        return rebuild_fts_index()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/local-index/backfill")
async def local_index_backfill_endpoint(body: LocalBackfillRequest):
    try:
        return await backfill_local_index(
            months=body.months,
            days=body.days,
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
            municipio=body.municipio,
            recortes_geograficos=body.recortes_geograficos,
            codigo_modalidade=body.codigo_modalidade,
            limit=max(200, body.max_paginas * body.tamanho_pagina),
            somente_homologados=body.somente_homologados,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/research/sessions")
async def research_session_create_endpoint(body: ResearchSessionCreateRequest):
    """Cria cotação (ordem de pesquisa) persistida em `pesquisador_sessoes` (SQLite do serviço)."""
    try:
        return create_research_session(
            titulo=body.titulo,
            termo_busca=body.termo_busca,
            modelo_cotacao=body.modelo_cotacao,
            filtros=body.filtros,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/research/cotacoes")
async def cotacao_create_endpoint(body: ResearchSessionCreateRequest):
    """Alias semântico de `POST /research/sessions` para o domínio «cotação»."""
    return await research_session_create_endpoint(body)


@router.get("/research/sessions")
async def research_session_list_endpoint(limit: int = 100):
    try:
        return list_research_sessions(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/research/sessions/{sessao_id}")
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


@router.post("/research/sessions/{sessao_id}/items")
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


@router.post("/research/sessions/{sessao_id}/update")
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


def create_app() -> FastAPI:
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        worker_task: asyncio.Task | None = None
        if PNCP_INGEST_WORKER_ENABLED:
            worker_task = asyncio.create_task(ingest_worker_loop())
        yield
        if worker_task is not None:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass

    app = FastAPI(title="PNCP Researcher Service", version="1.1.0", lifespan=lifespan)
    app.include_router(router, prefix="/api")
    return app
