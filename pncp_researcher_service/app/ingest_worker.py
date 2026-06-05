"""Worker asyncio: processa fila catalog_page → contract_items."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

from .config import (
    PNCP_INGEST_ITEMS_BACKLOG_PAUSE_CATALOG,
    PNCP_INGEST_WORKER_CATALOG_BATCH,
    PNCP_INGEST_WORKER_ENABLED,
    PNCP_INGEST_WORKER_ITEMS_BATCH,
    PNCP_INGEST_WORKER_ITEMS_BATCH_MAX,
    PNCP_INGEST_WORKER_POLL_SECONDS,
    PNCP_LOCAL_INCLUDE_ITEMS,
)
from .ingest_planner import plan_ingest_queue
from .ingest_queue import (
    TASK_CATALOG_PAGE,
    TASK_CONTRACT_ITEMS,
    claim_tasks,
    enqueue_contract_items,
    mark_task_done,
    mark_task_failed,
    pending_by_task_type,
    queue_stats,
)
from .local_index import (
    _mark_ingest_error,
    _mark_ingest_success,
    ensure_local_index,
    upsert_contract_items,
    upsert_contracts,
)
from .pncp_client import PNCPClientError, create_pncp_http_client, get_contract_items, search_contracts

logger = logging.getLogger(__name__)


async def _load_contract_raw(numero_pncp: str) -> Optional[Dict[str, Any]]:
    from .ingest_queue import _queue_conn

    with _queue_conn() as c:
        row = c.execute(
            "SELECT raw_json FROM pncp_contratos WHERE numero_pncp = ?",
            (str(numero_pncp).strip(),),
        ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row["raw_json"])
    except Exception:
        return None


async def process_catalog_page_task(task: Dict[str, Any], *, client: Any) -> None:
    uf = str(task.get("uf") or "").strip().upper()
    modalidade = int(task["modalidade"])
    pagina = int(task["pagina"])
    data_inicial = str(task["data_inicial"])
    data_final = str(task["data_final"])
    payload = {}
    if task.get("payload_json"):
        try:
            payload = json.loads(task["payload_json"])
        except Exception:
            payload = {}
    tamanho = max(10, min(int(payload.get("tamanho_pagina") or 50), 50))

    batch = await search_contracts(
        data_inicial,
        data_final,
        codigo_modalidade=modalidade,
        uf=uf or None,
        pagina=pagina,
        tamanho_pagina=tamanho,
        tolerate_rate_limit=False,
        client=client,
    )
    if not batch:
        _mark_ingest_success(
            uf or None,
            modalidade,
            data_inicial=data_inicial,
            data_final=data_final,
            page=0,
            add_upserts=0,
            add_item_upserts=0,
        )
        return

    upsert_contracts(batch)
    _mark_ingest_success(
        uf or None,
        modalidade,
        data_inicial=data_inicial,
        data_final=data_final,
        page=0 if len(batch) < 10 else pagina,
        add_upserts=len(batch),
        add_item_upserts=0,
    )

    if PNCP_LOCAL_INCLUDE_ITEMS:
        items_backlog = pending_by_task_type(TASK_CONTRACT_ITEMS)
        if items_backlog < max(0, int(PNCP_INGEST_ITEMS_BACKLOG_PAUSE_CATALOG)):
            for raw in batch:
                numero = str(raw.get("numeroControlePNCP") or "").strip()
                if numero:
                    enqueue_contract_items(numero_pncp=numero, priority=90)


async def process_contract_items_task(task: Dict[str, Any], *, client: Any) -> None:
    numero = str(task.get("numero_pncp") or "").strip()
    if not numero:
        return
    raw = await _load_contract_raw(numero)
    if not raw:
        raise PNCPClientError(f"Contrato {numero} não encontrado no índice local.")

    keys = raw.get("orgaoEntidade") or {}
    cnpj = (
        keys.get("cnpj")
        or keys.get("cnpjOrgaoEntidade")
        or raw.get("cnpjOrgaoEntidade")
    )
    numero_ctrl = str(raw.get("numeroControlePNCP") or "")
    if (not cnpj) and "-" in numero_ctrl:
        cnpj = numero_ctrl.split("-")[0]
    ano = raw.get("anoCompra")
    seq = raw.get("sequencialCompra")
    if not cnpj or ano is None or seq is None:
        return

    rows = await get_contract_items(str(cnpj), ano, seq, client=client)
    if rows:
        upsert_contract_items(raw, rows)


async def process_ingest_batch() -> Dict[str, Any]:
    ensure_local_index()
    items_backlog = pending_by_task_type(TASK_CONTRACT_ITEMS)
    pause_catalog = items_backlog >= max(0, int(PNCP_INGEST_ITEMS_BACKLOG_PAUSE_CATALOG))
    catalog_limit = 0 if pause_catalog else PNCP_INGEST_WORKER_CATALOG_BATCH
    item_limit = PNCP_INGEST_WORKER_ITEMS_BATCH
    if pause_catalog:
        item_limit = min(
            max(item_limit, PNCP_INGEST_WORKER_ITEMS_BATCH_MAX),
            PNCP_INGEST_WORKER_ITEMS_BATCH_MAX,
        )

    catalog_tasks = (
        claim_tasks(task_type=TASK_CATALOG_PAGE, limit=catalog_limit)
        if catalog_limit > 0
        else []
    )
    item_tasks = claim_tasks(
        task_type=TASK_CONTRACT_ITEMS,
        limit=item_limit,
    )
    if not catalog_tasks and not item_tasks:
        return {
            "catalog_ok": 0,
            "items_ok": 0,
            "errors": 0,
            "catalog_paused": pause_catalog,
            "items_backlog": items_backlog,
        }

    catalog_ok = items_ok = errors = 0
    async with create_pncp_http_client() as client:
        # Fase 2 primeiro — reduz sem_itens e backlog de contract_items.
        for task in item_tasks:
            tid = int(task["id"])
            try:
                await process_contract_items_task(task, client=client)
                mark_task_done(tid)
                items_ok += 1
            except Exception as exc:
                mark_task_failed(tid, str(exc))
                errors += 1
                logger.warning("ingest items task %s: %s", tid, exc)

        for task in catalog_tasks:
            tid = int(task["id"])
            try:
                await process_catalog_page_task(task, client=client)
                mark_task_done(tid)
                catalog_ok += 1
            except PNCPClientError as exc:
                mark_task_failed(tid, str(exc))
                _mark_ingest_error(
                    task.get("uf"),
                    int(task["modalidade"]),
                    data_inicial=str(task["data_inicial"]),
                    data_final=str(task["data_final"]),
                    page=int(task["pagina"]),
                    message=str(exc),
                )
                errors += 1
            except Exception as exc:
                mark_task_failed(tid, str(exc))
                errors += 1
                logger.exception("ingest catalog task %s: %s", tid, exc)

    return {
        "catalog_ok": catalog_ok,
        "items_ok": items_ok,
        "errors": errors,
        "catalog_paused": pause_catalog,
        "items_backlog": items_backlog,
        "queue": queue_stats(),
    }


async def ingest_worker_loop() -> None:
    """Loop em background: planeja periodicamente e processa a fila."""
    from .config import PNCP_INGEST_PLANNER_INTERVAL_SECONDS, PNCP_INGEST_QUEUE_ENABLED

    if not PNCP_INGEST_WORKER_ENABLED or not PNCP_INGEST_QUEUE_ENABLED:
        logger.info("ingest worker desligado (WORKER=%s QUEUE=%s)", PNCP_INGEST_WORKER_ENABLED, PNCP_INGEST_QUEUE_ENABLED)
        return

    logger.info("ingest worker iniciado poll=%.1fs", PNCP_INGEST_WORKER_POLL_SECONDS)
    # Evita planejamento imediato no boot (uvicorn sobe antes de estabilizar volume/DB).
    last_plan = time.monotonic()
    while True:
        try:
            now = time.monotonic()
            if now - last_plan >= float(PNCP_INGEST_PLANNER_INTERVAL_SECONDS):
                summary = plan_ingest_queue()
                logger.info(
                    "ingest planner catalog=%s items=%s paused_scopes=%s",
                    summary.get("catalog_pages_enqueued"),
                    summary.get("contract_items_enqueued"),
                    summary.get("catalog_scopes_paused"),
                )
                last_plan = now
            result = await process_ingest_batch()
            if (result.get("catalog_ok") or result.get("items_ok") or result.get("errors")):
                logger.info(
                    "ingest batch catalog_ok=%s items_ok=%s errors=%s pending=%s",
                    result.get("catalog_ok"),
                    result.get("items_ok"),
                    result.get("errors"),
                    (result.get("queue") or {}).get("pending"),
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("ingest worker tick falhou")
        await asyncio.sleep(max(0.5, float(PNCP_INGEST_WORKER_POLL_SECONDS)))
