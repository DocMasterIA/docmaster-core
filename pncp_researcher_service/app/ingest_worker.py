"""Worker asyncio: processa fila catalog_page → contract_items."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

from .config import (
    PNCP_INGEST_BACKFILL_ITEMS_FIRST_BACKLOG,
    PNCP_INGEST_BACKFILL_TARGET_BACKLOG,
    PNCP_INGEST_BATCH_MAX_SECONDS,
    PNCP_INGEST_CATALOG_PAUSE_MIN_GAP,
    PNCP_INGEST_CATALOG_TASK_TIMEOUT_SECONDS,
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
    effective_backlog_pause_catalog,
    is_ingest_backfill_mode,
)
from .ingest_backpressure import compute_ingest_backpressure
from .ingest_maintenance import requeue_processing_tasks, run_ingest_self_healing
from .ingest_planner import (
    enqueue_contracts_needing_resultados,
    plan_ingest_queue,
    topup_contract_items_if_starved,
)
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
    count_contracts_without_items,
    enqueue_contract_items,
    mark_task_done,
    mark_task_failed,
    queue_stats,
)
from .local_index import (
    _mark_ingest_error,
    _mark_ingest_success,
    contract_has_items_needing_resultados,
    contract_needs_items_refresh,
    enrich_contract_resultados_only,
    ensure_local_index,
    mark_contract_items_verified,
    upsert_contract_items,
    upsert_contracts,
)
from .pncp_client import (
    PNCPClientError,
    create_pncp_http_client,
    fetch_contract_items_with_resultados,
    search_contracts,
)

logger = logging.getLogger(__name__)

_last_topup_mono: float = 0.0
_last_resultados_topup_mono: float = 0.0
_last_gap_check_mono: float = 0.0
GAP_CHECK_INTERVAL_SECONDS: float = 120.0
TOPUP_MIN_INTERVAL_SECONDS: float = 30.0


def _cap_catalog_batch_limit(requested: int, *, has_item_tasks: bool) -> int:
    """Evita batch > PNCP_INGEST_BATCH_MAX_SECONDS com N páginas × timeout HTTP."""
    req = max(0, int(requested))
    if req <= 0:
        return 0
    batch_t = max(120.0, float(PNCP_INGEST_BATCH_MAX_SECONDS))
    page_t = max(30.0, float(PNCP_INGEST_CATALOG_TASK_TIMEOUT_SECONDS))
    reserve = 45.0 + (25.0 if has_item_tasks else 0.0)
    slots = max(1, int((batch_t - reserve) // (page_t + 8.0)))
    return min(req, slots)


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


def _skip_catalog_task_if_slow(task: Dict[str, Any], task_id: int, message: str) -> bool:
    """Após 2 timeouts, marca done e avança watermark — páginas PNCP cronicamente lentas."""
    from .ingest_queue import _queue_conn

    with _queue_conn() as c:
        row = c.execute(
            "SELECT attempts FROM pncp_ingest_queue WHERE id = ?",
            (int(task_id),),
        ).fetchone()
        if not row or int(row["attempts"] or 0) < 2:
            return False
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        c.execute(
            """
            UPDATE pncp_ingest_queue
            SET status = 'done', last_error = ?, updated_at = ?
            WHERE id = ? AND task_type = 'catalog_page'
            """,
            (f"skip: {message}"[:800], now, int(task_id)),
        )
        c.commit()
    _mark_ingest_success(
        task.get("uf"),
        int(task["modalidade"]),
        data_inicial=str(task["data_inicial"]),
        data_final=str(task["data_final"]),
        page=int(task["pagina"]),
        add_upserts=0,
        add_item_upserts=0,
    )
    logger.info(
        "ingest catalog task %s pulada (timeout): uf=%s mod=%s pag=%s",
        task_id,
        task.get("uf"),
        task.get("modalidade"),
        task.get("pagina"),
    )
    return True


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
        tolerate_rate_limit=True,
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
        if items_backlog < max(0, int(effective_backlog_pause_catalog())):
            for raw in batch:
                numero = str(raw.get("numeroControlePNCP") or "").strip()
                if numero and contract_needs_items_refresh(numero):
                    enqueue_contract_items(numero_pncp=numero, priority=90)


async def process_contract_items_task(task: Dict[str, Any], *, client: Any) -> int:
    """Busca GET /itens (+ /resultados); ou só /resultados se itens já existem no índice."""
    numero = str(task.get("numero_pncp") or "").strip()
    if not numero:
        return 0

    if contract_has_items_needing_resultados(numero):
        n_res = int(await enrich_contract_resultados_only(numero, client=client) or 0)
        if not contract_needs_items_refresh(numero):
            return n_res
        if n_res > 0 and not contract_has_items_needing_resultados(numero):
            return n_res

    if not contract_needs_items_refresh(numero):
        return 0
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
        mark_contract_items_verified(numero)
        logger.info("ingest items %s: chaves PNCP ausentes — marcado verificado", numero)
        return 0

    rows, resultados = await fetch_contract_items_with_resultados(
        str(cnpj), ano, seq, client=client
    )
    if rows:
        upserted = int(
            upsert_contract_items(raw, rows, resultados_by_item=resultados) or 0
        )
        if upserted <= 0:
            mark_contract_items_verified(numero)
            logger.info(
                "ingest items %s: PNCP retornou %s itens mas 0 upsertados — marcado verificado",
                numero,
                len(rows),
            )
        return upserted
    mark_contract_items_verified(numero)
    logger.info("ingest items %s: PNCP retornou 0 itens — marcado verificado", numero)
    return 0


async def _run_item_task(task: Dict[str, Any], *, client: Any, timeout: float) -> tuple[str, int]:
    tid = int(task["id"])
    numero = str(task.get("numero_pncp") or "").strip()
    if numero and not contract_needs_items_refresh(numero):
        try:
            n_res = await asyncio.wait_for(
                enrich_contract_resultados_only(numero, client=client),
                timeout=min(max(30.0, timeout), 120.0),
            )
        except asyncio.TimeoutError:
            mark_task_failed(tid, "timeout resultados-only")
            logger.warning("ingest resultados-only task %s: timeout", tid)
            return "error", 0
        except Exception as exc:
            mark_task_failed(tid, str(exc))
            logger.warning("ingest resultados-only task %s: %s", tid, exc)
            return "error", 0
        mark_task_done(tid)
        if int(n_res or 0) > 0:
            return "ok", int(n_res)
        return "skip", 0
    try:
        rows_up = await asyncio.wait_for(
            process_contract_items_task(task, client=client),
            timeout=max(30.0, timeout),
        )
        mark_task_done(tid)
        return "ok", int(rows_up or 0)
    except asyncio.TimeoutError:
        mark_task_failed(tid, f"timeout após {timeout:.0f}s")
        logger.warning("ingest items task %s: timeout", tid)
        return "error", 0
    except Exception as exc:
        mark_task_failed(tid, str(exc))
        logger.warning("ingest items task %s: %s", tid, exc)
        return "error", 0


async def _run_catalog_task(task: Dict[str, Any], *, client: Any, timeout: float) -> str:
    tid = int(task["id"])
    catalog_timeout = min(
        max(30.0, timeout),
        max(30.0, float(PNCP_INGEST_CATALOG_TASK_TIMEOUT_SECONDS)),
    )
    try:
        await asyncio.wait_for(
            process_catalog_page_task(task, client=client),
            timeout=catalog_timeout,
        )
        mark_task_done(tid)
        return "ok"
    except asyncio.TimeoutError:
        msg = f"timeout após {catalog_timeout:.0f}s"
        mark_task_failed(tid, msg)
        if _skip_catalog_task_if_slow(task, tid, msg):
            return "skip"
        _mark_ingest_error(
            task.get("uf"),
            int(task["modalidade"]),
            data_inicial=str(task["data_inicial"]),
            data_final=str(task["data_final"]),
            page=int(task["pagina"]),
            message=msg,
        )
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
    global _last_topup_mono, _last_resultados_topup_mono
    ensure_local_index()
    backfill = is_ingest_backfill_mode()
    task_timeout = max(30.0, float(PNCP_INGEST_TASK_TIMEOUT_SECONDS))
    now_mono = time.monotonic()

    gap_sqlite = count_contracts_without_items()
    bp = compute_ingest_backpressure(contracts_without_items=gap_sqlite)
    items_backlog = int(bp["items_backlog"])
    starving = bool(bp["starving"])
    catalog_heavy = bool(bp["catalog_heavy"])
    pause_catalog = bool(bp["pause_catalog"])

    if (now_mono - _last_topup_mono) >= TOPUP_MIN_INTERVAL_SECONDS:
        gap = gap_sqlite
        should_topup = False
        if is_ingest_backfill_mode():
            should_topup = items_backlog < max(
                1, int(PNCP_INGEST_BACKFILL_TARGET_BACKLOG)
            )
        elif starving or pause_catalog:
            should_topup = starving or (gap > 0 and items_backlog < 50)
        if should_topup:
            topped = topup_contract_items_if_starved(items_backlog=items_backlog)
            if topped:
                logger.info(
                    "ingest topup itens enfileirados=%s backlog_antes=%s gap_sqlite=%s backfill=%s",
                    topped,
                    items_backlog,
                    gap,
                    is_ingest_backfill_mode(),
                )
            _last_topup_mono = now_mono
            gap_sqlite = count_contracts_without_items()
            bp = compute_ingest_backpressure(contracts_without_items=gap_sqlite)
            items_backlog = int(bp["items_backlog"])
            starving = bool(bp["starving"])
            catalog_heavy = bool(bp["catalog_heavy"])
            pause_catalog = bool(bp["pause_catalog"])

    if (now_mono - _last_resultados_topup_mono) >= TOPUP_MIN_INTERVAL_SECONDS:
        try:
            res_top = enqueue_contracts_needing_resultados()
            if res_top:
                logger.info("ingest topup resultados enfileirados=%s", res_top)
        except Exception:
            logger.exception("ingest topup resultados falhou")
        _last_resultados_topup_mono = now_mono

    if catalog_heavy and pause_catalog:
        logger.info(
            "ingest catálogo pausado (heavy): catalog_pending=%s items_backlog=%s gap=%s",
            bp.get("catalog_pending"),
            items_backlog,
            gap_sqlite,
        )
    elif not pause_catalog and int(bp.get("catalog_pending") or 0) >= 100 and gap_sqlite < 50:
        logger.info(
            "ingest catálogo reaberto (gap baixo=%s): catalog_pending=%s",
            gap_sqlite,
            bp.get("catalog_pending"),
        )

    catalog_limit = 0 if pause_catalog else PNCP_INGEST_WORKER_CATALOG_BATCH
    item_limit = PNCP_INGEST_WORKER_ITEMS_BATCH
    if pause_catalog or backfill:
        item_limit = min(
            max(item_limit, PNCP_INGEST_WORKER_ITEMS_BATCH_MAX),
            PNCP_INGEST_WORKER_ITEMS_BATCH_MAX,
        )
    elif items_backlog > item_limit:
        item_limit = min(items_backlog, PNCP_INGEST_WORKER_ITEMS_BATCH_MAX)

    if catalog_limit > 0:
        catalog_limit = _cap_catalog_batch_limit(
            catalog_limit,
            has_item_tasks=item_limit > 0,
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
            "items_skipped": 0,
            "item_rows_upserted": 0,
            "errors": 0,
            "catalog_paused": pause_catalog,
            "catalog_heavy": catalog_heavy,
            "items_backlog": items_backlog,
            "items_starved": starving,
            "contracts_without_items": gap_sqlite,
            "backfill_mode": backfill,
            "queue": queue_stats(),
        }

    catalog_ok = items_ok = items_skipped = item_rows_upserted = errors = 0
    items_first = backfill and items_backlog > max(
        0, int(PNCP_INGEST_BACKFILL_ITEMS_FIRST_BACKLOG)
    )
    # Com gap=0, catálogo primeiro — exceto backfill com fila grande (prioriza itens).
    run_catalog_first = (
        not items_first and gap_sqlite == 0 and bool(catalog_tasks)
    )

    async with create_pncp_http_client() as client:

        async def _run_items() -> None:
            nonlocal items_ok, items_skipped, item_rows_upserted, errors
            if not item_tasks:
                return
            conc = max(1, int(PNCP_INGEST_WORKER_ITEMS_CONCURRENCY))
            sem = asyncio.Semaphore(conc)

            async def _item_wrapped(t: Dict[str, Any]) -> tuple[str, int]:
                async with sem:
                    return await _run_item_task(t, client=client, timeout=task_timeout)

            item_results = await asyncio.gather(
                *(_item_wrapped(t) for t in item_tasks),
                return_exceptions=False,
            )
            for st, rows_up in item_results:
                if st == "error":
                    errors += 1
                elif st == "skip":
                    items_skipped += 1
                else:
                    items_ok += 1
                    item_rows_upserted += int(rows_up or 0)

        async def _run_catalog() -> None:
            nonlocal catalog_ok, errors
            for task in catalog_tasks:
                st = await _run_catalog_task(task, client=client, timeout=task_timeout)
                if st == "ok":
                    catalog_ok += 1
                elif st != "skip":
                    errors += 1

        if run_catalog_first:
            await _run_catalog()
            await _run_items()
        else:
            await _run_items()
            await _run_catalog()

    gap_sqlite = count_contracts_without_items()
    return {
        "catalog_ok": catalog_ok,
        "items_ok": items_ok,
        "items_skipped": items_skipped,
        "item_rows_upserted": item_rows_upserted,
        "errors": errors,
        "catalog_paused": pause_catalog,
        "catalog_heavy": catalog_heavy,
        "items_backlog": items_backlog,
        "items_starved": starving,
        "contracts_without_items": gap_sqlite,
        "backfill_mode": backfill,
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
                gap_sqlite = await asyncio.to_thread(count_contracts_without_items)
                bp = compute_ingest_backpressure(contracts_without_items=gap_sqlite)
                result = {
                    "catalog_ok": 0,
                    "items_ok": 0,
                    "items_skipped": 0,
                    "item_rows_upserted": 0,
                    "errors": 1,
                    "batch_timeout": True,
                    "requeued_processing": n,
                    "contracts_without_items": gap_sqlite,
                    "items_backlog": int(bp["items_backlog"]),
                    "catalog_paused": bool(bp["pause_catalog"]),
                    "catalog_heavy": bool(bp["catalog_heavy"]),
                    "queue": queue_stats(),
                }
            record_batch_result(result)
            maybe_log_heartbeat()
            if (result.get("catalog_ok") or result.get("items_ok") or result.get("errors")):
                logger.info(
                    "ingest batch catalog_ok=%s items_ok=%s items_skip=%s item_rows=%s errors=%s pending=%s "
                    "gap=%s items_backlog=%s catalog_paused=%s catalog_heavy=%s backfill_mode=%s",
                    result.get("catalog_ok"),
                    result.get("items_ok"),
                    result.get("items_skipped"),
                    result.get("item_rows_upserted"),
                    result.get("errors"),
                    (result.get("queue") or {}).get("pending"),
                    result.get("contracts_without_items"),
                    result.get("items_backlog"),
                    result.get("catalog_paused"),
                    result.get("catalog_heavy"),
                    result.get("backfill_mode"),
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("ingest worker tick falhou")
        await asyncio.sleep(max(0.5, float(PNCP_INGEST_WORKER_POLL_SECONDS)))
