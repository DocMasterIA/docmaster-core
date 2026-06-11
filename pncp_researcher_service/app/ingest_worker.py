"""Worker asyncio: processa fila catalog_page → contract_items."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

from .config import (
    PNCP_INGEST_BATCH_MAX_SECONDS,
    PNCP_INGEST_PLANNER_INTERVAL_SECONDS,
    PNCP_INGEST_QUEUE_ENABLED,
    PNCP_INGEST_SELF_HEAL_INTERVAL_SECONDS,
    PNCP_INGEST_TASK_TIMEOUT_SECONDS,
    PNCP_INGEST_WORKER_CATALOG_BATCH,
    PNCP_INGEST_WORKER_ENABLED,
    PNCP_INGEST_WORKER_ITEMS_BATCH,
    PNCP_INGEST_WORKER_ITEMS_BATCH_MAX,
    PNCP_INGEST_WORKER_ITEMS_CONCURRENCY,
    PNCP_INGEST_WORKER_POLL_SECONDS,
    PNCP_LOCAL_INCLUDE_ITEMS,
)
from .ingest_backpressure import compute_ingest_backpressure
from .ingest_maintenance import requeue_processing_tasks, run_ingest_self_healing
from .ingest_planner import plan_ingest_queue, topup_contract_items_if_starved
from .ingest_runtime import (
    configure_service_logging,
    mark_worker_started,
    maybe_log_heartbeat,
    record_batch_result,
    run_stall_recovery_if_needed,
)
from .ingest_queue import (
    TASK_CATALOG_PAGE,
    TASK_CONTRACT_ITEMS,
    backlog_by_task_type,
    claim_tasks,
    enqueue_contract_items,
    mark_task_done,
    mark_task_failed,
    queue_stats,
)
from .local_index import (
    _mark_ingest_error,
    _mark_ingest_success,
    contract_needs_items_refresh,
    ensure_local_index,
    upsert_contract_items,
    upsert_contracts,
)
from .pncp_client import PNCPClientError, create_pncp_http_client, get_contract_items, search_contracts

logger = logging.getLogger(__name__)

_last_topup_mono: float = 0.0
_last_gap_check_mono: float = 0.0
GAP_CHECK_INTERVAL_SECONDS: float = 120.0
TOPUP_MIN_INTERVAL_SECONDS: float = 30.0


def _maybe_contracts_without_items(*, items_backlog: int, pause_catalog: bool) -> int:
    """Gap SQLite — amostra barata, no máximo a cada 2 min quando fila de itens está baixa."""
    global _last_gap_check_mono
    if items_backlog >= 50 and not pause_catalog:
        return 0
    now = time.monotonic()
    if (now - _last_gap_check_mono) < GAP_CHECK_INTERVAL_SECONDS:
        return 0
    _last_gap_check_mono = now
    from .ingest_queue import count_contracts_without_items

    return count_contracts_without_items()


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
        items_backlog = backlog_by_task_type(TASK_CONTRACT_ITEMS)
        if items_backlog < max(0, int(PNCP_INGEST_ITEMS_BACKLOG_PAUSE_CATALOG)):
            for raw in batch:
                numero = str(raw.get("numeroControlePNCP") or "").strip()
                if numero and contract_needs_items_refresh(numero):
                    enqueue_contract_items(numero_pncp=numero, priority=90)


async def process_contract_items_task(task: Dict[str, Any], *, client: Any) -> None:
    numero = str(task.get("numero_pncp") or "").strip()
    if not numero:
        return
    if not contract_needs_items_refresh(numero):
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


async def _run_item_task(task: Dict[str, Any], *, client: Any, timeout: float) -> str:
    tid = int(task["id"])
    try:
        await asyncio.wait_for(
            process_contract_items_task(task, client=client),
            timeout=max(30.0, timeout),
        )
        mark_task_done(tid)
        return "ok"
    except asyncio.TimeoutError:
        mark_task_failed(tid, f"timeout após {timeout:.0f}s")
        logger.warning("ingest items task %s: timeout", tid)
        return "error"
    except Exception as exc:
        mark_task_failed(tid, str(exc))
        logger.warning("ingest items task %s: %s", tid, exc)
        return "error"


async def _run_catalog_task(task: Dict[str, Any], *, client: Any, timeout: float) -> str:
    tid = int(task["id"])
    try:
        await asyncio.wait_for(
            process_catalog_page_task(task, client=client),
            timeout=max(30.0, timeout),
        )
        mark_task_done(tid)
        return "ok"
    except asyncio.TimeoutError:
        mark_task_failed(tid, f"timeout após {timeout:.0f}s")
        logger.warning("ingest catalog task %s: timeout", tid)
        return "error"
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
        logger.warning("ingest catalog task %s: %s", tid, exc)
        return "error"
    except Exception as exc:
        mark_task_failed(tid, str(exc))
        logger.exception("ingest catalog task %s: %s", tid, exc)
        return "error"


async def process_ingest_batch() -> Dict[str, Any]:
    global _last_topup_mono
    ensure_local_index()
    task_timeout = max(30.0, float(PNCP_INGEST_TASK_TIMEOUT_SECONDS))
    now_mono = time.monotonic()

    bp = compute_ingest_backpressure()
    items_backlog = int(bp["items_backlog"])
    starving = bool(bp["starving"])
    catalog_heavy = bool(bp["catalog_heavy"])
    pause_catalog = bool(bp["pause_catalog"])

    if (now_mono - _last_topup_mono) >= TOPUP_MIN_INTERVAL_SECONDS and (
        starving or pause_catalog
    ):
        gap = _maybe_contracts_without_items(
            items_backlog=items_backlog,
            pause_catalog=pause_catalog,
        )
        if starving or (gap > 0 and items_backlog < 50):
            topped = topup_contract_items_if_starved(items_backlog=items_backlog)
            if topped:
                logger.info(
                    "ingest topup itens enfileirados=%s backlog_antes=%s gap_sqlite=%s",
                    topped,
                    items_backlog,
                    gap,
                )
            _last_topup_mono = now_mono
            bp = compute_ingest_backpressure()
            items_backlog = int(bp["items_backlog"])
            starving = bool(bp["starving"])
            catalog_heavy = bool(bp["catalog_heavy"])
            pause_catalog = bool(bp["pause_catalog"])

    if catalog_heavy and pause_catalog:
        logger.info(
            "ingest catálogo pausado (heavy): catalog_pending=%s items_backlog=%s",
            bp.get("catalog_pending"),
            items_backlog,
        )

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
        gap = _maybe_contracts_without_items(
            items_backlog=items_backlog,
            pause_catalog=pause_catalog,
        )
        return {
            "catalog_ok": 0,
            "items_ok": 0,
            "errors": 0,
            "catalog_paused": pause_catalog,
            "catalog_heavy": catalog_heavy,
            "items_backlog": items_backlog,
            "items_starved": starving,
            "contracts_without_items": gap,
            "queue": queue_stats(),
        }

    catalog_ok = items_ok = errors = 0
    async with create_pncp_http_client() as client:
        if item_tasks:
            conc = max(1, int(PNCP_INGEST_WORKER_ITEMS_CONCURRENCY))
            sem = asyncio.Semaphore(conc)

            async def _item_wrapped(t: Dict[str, Any]) -> str:
                async with sem:
                    return await _run_item_task(t, client=client, timeout=task_timeout)

            item_results = await asyncio.gather(
                *(_item_wrapped(t) for t in item_tasks),
                return_exceptions=False,
            )
            for st in item_results:
                if st == "ok":
                    items_ok += 1
                else:
                    errors += 1

        for task in catalog_tasks:
            st = await _run_catalog_task(task, client=client, timeout=task_timeout)
            if st == "ok":
                catalog_ok += 1
            else:
                errors += 1

    gap = _maybe_contracts_without_items(
        items_backlog=items_backlog,
        pause_catalog=pause_catalog,
    )
    return {
        "catalog_ok": catalog_ok,
        "items_ok": items_ok,
        "errors": errors,
        "catalog_paused": pause_catalog,
        "catalog_heavy": catalog_heavy,
        "items_backlog": items_backlog,
        "items_starved": starving,
        "contracts_without_items": gap,
        "queue": queue_stats(),
    }


async def ingest_worker_loop() -> None:
    """Loop em background: planeja periodicamente e processa a fila."""
    configure_service_logging()
    if not PNCP_INGEST_WORKER_ENABLED or not PNCP_INGEST_QUEUE_ENABLED:
        logger.info("ingest worker desligado (WORKER=%s QUEUE=%s)", PNCP_INGEST_WORKER_ENABLED, PNCP_INGEST_QUEUE_ENABLED)
        return

    mark_worker_started()
    try:
        await asyncio.to_thread(run_ingest_self_healing, mode="startup")
    except Exception:
        logger.exception("ingest self-heal (startup) falhou — worker continua")

    logger.info("ingest worker iniciado poll=%.1fs", PNCP_INGEST_WORKER_POLL_SECONDS)
    try:
        boot_plan = plan_ingest_queue()
        logger.info(
            "ingest planner (boot) catalog=%s items=%s paused_scopes=%s",
            boot_plan.get("catalog_pages_enqueued"),
            boot_plan.get("contract_items_enqueued"),
            boot_plan.get("catalog_scopes_paused"),
        )
    except Exception:
        logger.exception("ingest planner (boot) falhou")
    last_plan = time.monotonic()
    last_heal = time.monotonic()
    while True:
        try:
            now = time.monotonic()
            if now - last_heal >= float(PNCP_INGEST_SELF_HEAL_INTERVAL_SECONDS):
                try:
                    await asyncio.to_thread(run_ingest_self_healing, mode="periodic")
                except Exception:
                    logger.exception("ingest self-heal (periodic) falhou")
                last_heal = now
            if now - last_plan >= float(PNCP_INGEST_PLANNER_INTERVAL_SECONDS):
                summary = plan_ingest_queue()
                logger.info(
                    "ingest planner catalog=%s items=%s paused_scopes=%s",
                    summary.get("catalog_pages_enqueued"),
                    summary.get("contract_items_enqueued"),
                    summary.get("catalog_scopes_paused"),
                )
                last_plan = now
            run_stall_recovery_if_needed()
            batch_timeout = max(120.0, float(PNCP_INGEST_BATCH_MAX_SECONDS))
            try:
                result = await asyncio.wait_for(
                    process_ingest_batch(),
                    timeout=batch_timeout,
                )
            except asyncio.TimeoutError:
                n = await asyncio.to_thread(
                    requeue_processing_tasks,
                    stale_only=False,
                    stale_seconds=900,
                )
                logger.warning(
                    "ingest batch timeout (%.0fs) — %s tarefas processing devolvidas à fila",
                    batch_timeout,
                    n,
                )
                result = {
                    "catalog_ok": 0,
                    "items_ok": 0,
                    "errors": 1,
                    "batch_timeout": True,
                    "requeued_processing": n,
                    "queue": queue_stats(),
                }
            record_batch_result(result)
            maybe_log_heartbeat()
            if (result.get("catalog_ok") or result.get("items_ok") or result.get("errors")):
                logger.info(
                    "ingest batch catalog_ok=%s items_ok=%s errors=%s pending=%s "
                    "items_backlog=%s catalog_paused=%s catalog_heavy=%s",
                    result.get("catalog_ok"),
                    result.get("items_ok"),
                    result.get("errors"),
                    (result.get("queue") or {}).get("pending"),
                    result.get("items_backlog"),
                    result.get("catalog_paused"),
                    result.get("catalog_heavy"),
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("ingest worker tick falhou")
        await asyncio.sleep(max(0.5, float(PNCP_INGEST_WORKER_POLL_SECONDS)))
