from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException

from .config import PNCP_LOCAL_DB_PATH
from .ingest_coverage import ingest_coverage_status
from .ingest_planner import plan_ingest_queue
from .ingest_worker import process_ingest_batch
from .ingest_runtime import ingest_runtime_status
from .local_index import (
    backfill_local_index,
    count_contracts_needing_resultados,
    fts_index_status,
    ingest_operational_status,
    local_index_operational_status,
    local_index_stats,
    rebuild_fts_index,
    sync_catalog_metadata_from_raw_json,
)
from .pncp_client import PNCPClientError
from .schemas import HealthResponse, IngestPlanRequest, LocalBackfillRequest, LocalSyncCatalogRequest, TceRsIngestRequest
from .service_mode import (
    feed_platform,
    is_platform_feed,
    is_pncp_feed,
    service_name,
)

feed_router = APIRouter(prefix="/pncp-feed", tags=["price-index-feed"])
# Caminhos legados para scripts/cron que ainda usam /pncp-research/local-index/*
legacy_feed_router = APIRouter(prefix="/pncp-research", tags=["price-index-feed-legacy"])


def _require_pncp_feed() -> None:
    if not is_pncp_feed():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Rotas PNCP local-index indisponíveis neste processo "
                f"(feed_platform={feed_platform() or 'none'}). "
                "Use o container price_index_feed_pncp."
            ),
        )


def _require_platform_feed(platform_id: str) -> None:
    if not is_platform_feed(platform_id):
        raise HTTPException(
            status_code=404,
            detail=(
                f"Rotas da plataforma {platform_id} indisponíveis neste processo "
                f"(feed_platform={feed_platform() or 'none'}). "
                f"Use price_index_feed_{platform_id}."
            ),
        )


def _feed_health() -> HealthResponse:
    plat = feed_platform()
    if plat and plat != "pncp":
        # Feed batch (ex.: TCE-RS): health do índice da plataforma, sem misturar com PNCP.
        from .platform_index.registry import get_platform_spec
        from .platform_index.schema import platform_index_stats

        spec = get_platform_spec(plat)
        db_path = (spec.db_path if spec else "") or ""
        on_volume = db_path.startswith("/data/platforms/")
        db_bytes = 0
        if db_path and os.path.isfile(db_path):
            try:
                db_bytes = int(os.path.getsize(db_path))
            except OSError:
                db_bytes = 0
        stats = platform_index_stats(db_path) if db_path else {}
        hint = ""
        if not stats.get("search_ready"):
            hint = "Índice ainda sem itens search_ready — rode ingest."
        return HealthResponse(
            ok=True,
            service=service_name(),
            service_mode="feed",
            feed_platform=plat,
            db_path=db_path,
            db_bytes=db_bytes,
            db_on_data_volume=on_volume,
            index_hint=hint,
            ingest={"platform_index": stats},
            ia=None,
        )

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
        hint = "AVISO: SQLite em /tmp — monte volume /data/pncp."
    elif not on_volume:
        hint = "AVISO: db_path fora de /data/pncp."
    ingest = ingest_runtime_status()
    if ingest.get("stalled"):
        stall_hint = (
            f"INGEST parada ({ingest.get('seconds_since_progress')}s sem progresso, "
            f"pending={ingest.get('pending_last')})."
        )
        hint = f"{hint} {stall_hint}".strip() if hint else stall_hint
    return HealthResponse(
        ok=True,
        service=service_name(),
        service_mode="feed",
        feed_platform=plat or "pncp",
        db_path=db_path,
        db_bytes=db_bytes,
        db_on_data_volume=on_volume,
        index_hint=hint,
        ingest=ingest,
        ia=None,
    )


@feed_router.get("/health", response_model=HealthResponse)
async def feed_health() -> HealthResponse:
    return _feed_health()


@feed_router.get("/local-index/stats")
@legacy_feed_router.get("/local-index/stats")
async def local_index_stats_endpoint():
    _require_pncp_feed()
    try:
        return local_index_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@feed_router.get("/local-index/ingest-status")
@legacy_feed_router.get("/local-index/ingest-status")
async def local_index_ingest_status_endpoint(uf: str | None = None):
    _require_pncp_feed()
    try:
        return ingest_operational_status(uf=uf)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@feed_router.get("/local-index/coverage")
@legacy_feed_router.get("/local-index/coverage")
async def local_index_coverage_endpoint():
    _require_pncp_feed()
    try:
        return ingest_coverage_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@feed_router.post("/local-index/ingest/plan")
@legacy_feed_router.post("/local-index/ingest/plan")
async def local_index_ingest_plan_endpoint(body: IngestPlanRequest | None = None):
    _require_pncp_feed()
    try:
        req = body or IngestPlanRequest()
        return plan_ingest_queue(
            uf=req.uf,
            pages_per_scope=req.pages_per_scope,
            contracts_without_items_limit=req.contracts_without_items_limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@feed_router.post("/local-index/ingest/worker-tick")
@legacy_feed_router.post("/local-index/ingest/worker-tick")
async def local_index_ingest_worker_tick_endpoint():
    _require_pncp_feed()
    try:
        return await process_ingest_batch()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@feed_router.get("/local-index/operational-status")
@legacy_feed_router.get("/local-index/operational-status")
async def local_index_operational_status_endpoint(uf: str | None = None):
    _require_pncp_feed()
    try:
        return local_index_operational_status(uf=uf)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@feed_router.get("/local-index/fts-status")
@legacy_feed_router.get("/local-index/fts-status")
async def local_index_fts_status_endpoint():
    _require_pncp_feed()
    try:
        return fts_index_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@feed_router.post("/local-index/fts-rebuild")
@legacy_feed_router.post("/local-index/fts-rebuild")
async def local_index_fts_rebuild_endpoint():
    _require_pncp_feed()
    try:
        return rebuild_fts_index()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@feed_router.post("/local-index/sync-catalog-metadata")
@legacy_feed_router.post("/local-index/sync-catalog-metadata")
async def local_index_sync_catalog_metadata_endpoint(body: LocalSyncCatalogRequest):
    _require_pncp_feed()
    try:
        out = sync_catalog_metadata_from_raw_json(
            batch_size=body.batch_size,
            max_batches=body.max_batches,
        )
        out["contracts_needing_resultados"] = count_contracts_needing_resultados()
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@feed_router.post("/local-index/backfill")
@legacy_feed_router.post("/local-index/backfill")
async def local_index_backfill_endpoint(body: LocalBackfillRequest):
    _require_pncp_feed()
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


@feed_router.post("/price-platform-indexes/{platform_id}/ensure")
@legacy_feed_router.post("/price-platform-indexes/{platform_id}/ensure")
async def ensure_price_platform_index_endpoint(platform_id: str):
    from .platform_index.registry import get_platform_spec
    from .platform_index.schema import ensure_platform_index, platform_spec_with_stats

    _require_platform_feed(platform_id)
    spec = get_platform_spec(platform_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"plataforma desconhecida: {platform_id}")
    if spec.schema_kind == "legacy_pncp":
        raise HTTPException(
            status_code=400,
            detail="PNCP usa índice legacy em PNCP_LOCAL_DB_PATH (/local-index/*)",
        )
    if spec.schema_kind == "api_only":
        raise HTTPException(status_code=400, detail=f"plataforma {platform_id} não possui índice SQLite")
    try:
        path = ensure_platform_index(platform_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    updated = get_platform_spec(platform_id)
    return {
        "ok": True,
        "platform_id": platform_id,
        "db_path": path,
        "plataforma": platform_spec_with_stats(updated) if updated else None,
    }


@feed_router.get("/price-platform-indexes")
@legacy_feed_router.get("/price-platform-indexes")
async def list_price_platform_indexes_feed_endpoint():
    from .adapters.registry import list_platform_index_catalog

    return {
        "ok": True,
        "role": "feed",
        "feed_platform": feed_platform() or "all",
        "plataformas": list_platform_index_catalog(),
    }


@feed_router.get("/price-platform-indexes/tce_rs/ingest-status")
@legacy_feed_router.get("/price-platform-indexes/tce_rs/ingest-status")
async def tce_rs_ingest_status_endpoint():
    _require_platform_feed("tce_rs")
    from .platform_index.ingest.tce_rs import tce_rs_ingest_status

    return tce_rs_ingest_status()


@feed_router.post("/price-platform-indexes/tce_rs/ingest")
@legacy_feed_router.post("/price-platform-indexes/tce_rs/ingest")
async def tce_rs_ingest_endpoint(body: TceRsIngestRequest):
    _require_platform_feed("tce_rs")
    from .platform_index.ingest.tce_rs import ingest_tce_rs_from_directory, ingest_tce_rs_sample

    try:
        if body.use_sample:
            return ingest_tce_rs_sample()
        if not body.data_dir:
            raise HTTPException(
                status_code=400,
                detail="Informe data_dir ou use_sample=true",
            )
        return ingest_tce_rs_from_directory(body.data_dir, max_rows=body.max_rows)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:500]) from e


@feed_router.post("/price-platform-indexes/tce_rs/ingest-sample")
@legacy_feed_router.post("/price-platform-indexes/tce_rs/ingest-sample")
async def tce_rs_ingest_sample_endpoint():
    _require_platform_feed("tce_rs")
    from .platform_index.ingest.tce_rs import ingest_tce_rs_sample

    try:
        return ingest_tce_rs_sample()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:500]) from e
