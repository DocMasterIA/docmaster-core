"""Planejador: enfileira páginas de catálogo e contratos sem itens na janela de 365 dias."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import (
    PNCP_INGEST_BACKFILL_TARGET_BACKLOG,
    PNCP_INGEST_BACKFILL_TOPUP_CHUNK,
    PNCP_INGEST_PLANNER_CONTRACTS_WITHOUT_ITEMS,
    PNCP_INGEST_PLANNER_CONTRACTS_WITHOUT_ITEMS_MAX,
    PNCP_INGEST_PLANNER_PAGES_PER_SCOPE,
    PNCP_INGEST_QUEUE_ENABLED,
    PNCP_INGEST_QUEUE_MAX_PENDING,
    PNCP_INGEST_RESULTADOS_TOPUP_ENABLED,
    PNCP_INGEST_RESULTADOS_TOPUP_LIMIT,
    PNCP_INGEST_SYNC_CATALOG_BATCH,
    effective_resultados_topup_limit,
    PNCP_MODALIDADES_DEFAULT,
    PNCP_UFS_DEFAULT,
    effective_items_refresh_days,
    effective_items_starve_backlog,
    is_ingest_backfill_mode,
)
from .ingest_backpressure import compute_ingest_backpressure
from .ingest_dates import resolve_backfill_window
from .ingest_queue import (
    TASK_CONTRACT_ITEMS,
    count_contracts_without_items,
    enqueue_catalog_page,
    enqueue_contract_items,
    queue_stats,
)
from .local_index import (
    _get_ingest_state,
    _parse_iso_utc,
    _resolve_backfill_start_page,
    ensure_local_index,
    list_contracts_needing_resultados,
    count_items_needing_catalog_metadata_sync,
    count_contracts_needing_resultados,
    sync_catalog_metadata_from_raw_json,
)

logger = logging.getLogger(__name__)

PRIORITY_GAP = 50
# Acima de backlog (80): topup /resultados compete com fila de contratos sem itens.
PRIORITY_RESULTADOS = 72
PRIORITY_NORMAL = 100
PRIORITY_BACKLOG_ITEMS = 80
# Abaixo de catálogo-on-page (90) e gap (80): não compete com descoberta imediata.
PRIORITY_STALE_REFRESH = 110

_SQL_ITEM_UPDATED_AT = (
    "datetime(replace(replace(i.updated_at,'T',' '),'Z',''))"
)


def enqueue_contracts_without_items(*, limit: int, priority: int = PRIORITY_BACKLOG_ITEMS) -> int:
    """Enfileira contratos locais que ainda não têm linhas em pncp_itens."""
    lim = max(0, int(limit))
    if lim <= 0:
        return 0
    ensure_local_index()
    from .ingest_queue import _queue_conn

    with _queue_conn() as c:
        rows = c.execute(
            """
            SELECT c.numero_pncp
            FROM pncp_contratos c
            WHERE NOT EXISTS (
                SELECT 1 FROM pncp_itens i WHERE i.numero_pncp = c.numero_pncp LIMIT 1
            )
            AND (c.itens_verificados_at IS NULL OR TRIM(c.itens_verificados_at) = '')
            ORDER BY c.updated_at DESC
            LIMIT ?
            """,
            (lim,),
        ).fetchall()
    n = 0
    for r in rows:
        if enqueue_contract_items(
            numero_pncp=str(r["numero_pncp"]),
            priority=int(priority),
        ):
            n += 1
    return n


def enqueue_contracts_needing_items_refresh(
    *,
    limit: int,
    priority: int = PRIORITY_STALE_REFRESH,
) -> int:
    """
    Enfileira contratos que já têm itens locais mas passaram do refresh window.
    Complementa enqueue_contracts_without_items (gap=0) sem esperar o catálogo repassar.
    """
    days = effective_items_refresh_days()
    lim = max(0, int(limit))
    if lim <= 0 or days <= 0:
        return 0
    ensure_local_index()
    from .ingest_queue import _queue_conn

    with _queue_conn() as c:
        rows = c.execute(
            f"""
            SELECT c.numero_pncp
            FROM pncp_contratos c
            WHERE EXISTS (
                SELECT 1 FROM pncp_itens i WHERE i.numero_pncp = c.numero_pncp LIMIT 1
            )
            AND (
                SELECT MAX({_SQL_ITEM_UPDATED_AT})
                FROM pncp_itens i
                WHERE i.numero_pncp = c.numero_pncp
            ) < datetime('now', ?)
            ORDER BY (
                SELECT MAX({_SQL_ITEM_UPDATED_AT})
                FROM pncp_itens i
                WHERE i.numero_pncp = c.numero_pncp
            ) ASC
            LIMIT ?
            """,
            (f"-{days} days", lim),
        ).fetchall()
    n = 0
    for r in rows:
        if enqueue_contract_items(
            numero_pncp=str(r["numero_pncp"]),
            priority=int(priority),
        ):
            n += 1
    return n


def enqueue_contracts_not_in_item_queue(
    *,
    limit: int,
    priority: int = PRIORITY_STALE_REFRESH,
) -> int:
    """Enfileira contratos sem task contract_items pending/processing (backfill contínuo)."""
    lim = max(0, int(limit))
    if lim <= 0:
        return 0
    ensure_local_index()
    from .ingest_queue import _queue_conn

    with _queue_conn() as c:
        rows = c.execute(
            """
            SELECT c.numero_pncp
            FROM pncp_contratos c
            WHERE NOT EXISTS (
                SELECT 1 FROM pncp_ingest_queue q
                WHERE q.task_type = ?
                  AND q.numero_pncp = c.numero_pncp
                  AND q.status IN ('pending', 'processing')
            )
            ORDER BY
                CASE WHEN EXISTS (
                    SELECT 1 FROM pncp_itens i WHERE i.numero_pncp = c.numero_pncp LIMIT 1
                ) THEN 1 ELSE 0 END ASC,
                c.updated_at DESC
            LIMIT ?
            """,
            (TASK_CONTRACT_ITEMS, lim),
        ).fetchall()
    n = 0
    for r in rows:
        if enqueue_contract_items(
            numero_pncp=str(r["numero_pncp"]),
            priority=int(priority),
        ):
            n += 1
    return n


def _topup_chunk_limit(*, items_backlog: int) -> int:
    if is_ingest_backfill_mode():
        target = max(1, int(PNCP_INGEST_BACKFILL_TARGET_BACKLOG))
        if items_backlog >= target:
            return 0
        chunk = max(1, int(PNCP_INGEST_BACKFILL_TOPUP_CHUNK))
        return min(chunk, target - items_backlog)
    starve = max(0, int(effective_items_starve_backlog()))
    if items_backlog >= starve:
        return 0
    base = max(0, int(PNCP_INGEST_PLANNER_CONTRACTS_WITHOUT_ITEMS))
    ceiling = max(base, int(PNCP_INGEST_PLANNER_CONTRACTS_WITHOUT_ITEMS_MAX))
    if items_backlog <= 0:
        return ceiling
    return min(ceiling, base + (starve - items_backlog) * 4)


def topup_contract_items_if_starved(*, items_backlog: int) -> int:
    """Alimenta a fila de itens quando o backlog está baixo (crescimento do índice)."""
    lim = _topup_chunk_limit(items_backlog=items_backlog)
    if lim <= 0:
        return 0
    n_gap = enqueue_contracts_without_items(limit=lim)
    remaining = max(0, lim - n_gap)
    n_stale = 0
    if remaining > 0 and not is_ingest_backfill_mode():
        n_stale = enqueue_contracts_needing_items_refresh(limit=remaining)
        remaining = max(0, remaining - n_stale)
    n_queue = 0
    if remaining > 0 and is_ingest_backfill_mode():
        n_queue = enqueue_contracts_not_in_item_queue(limit=remaining)
    total = n_gap + n_stale + n_queue
    if total:
        logger.info(
            "ingest topup enfileirados=%s gap=%s stale=%s queue=%s backlog_antes=%s backfill=%s",
            total,
            n_gap,
            n_stale,
            n_queue,
            items_backlog,
            is_ingest_backfill_mode(),
        )
    return total


def enqueue_contracts_needing_resultados(limit: Optional[int] = None) -> int:
    """
    Enfileira contratos já no índice sem preço homologado.
    O worker trata com GET /resultados only (sem refetch /itens).
    """
    if not PNCP_INGEST_RESULTADOS_TOPUP_ENABLED:
        return 0
    lim = max(1, int(limit or effective_resultados_topup_limit()))
    ensure_local_index()
    numeros = list_contracts_needing_resultados(lim)
    n = 0
    for numero in numeros:
        if enqueue_contract_items(numero_pncp=numero, priority=PRIORITY_RESULTADOS):
            n += 1
    if n:
        logger.info("ingest topup resultados enfileirados=%s", n)
    return n


def plan_ingest_queue(
    *,
    uf: Optional[str] = None,
    modalidades: Optional[List[int]] = None,
    pages_per_scope: Optional[int] = None,
    contracts_without_items_limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Enfileira trabalho pendente sem executar HTTP.
    Idempotente: INSERT OR IGNORE na fila.
    """
    if not PNCP_INGEST_QUEUE_ENABLED:
        return {"ok": False, "error": "PNCP_INGEST_QUEUE_ENABLED=0"}

    ensure_local_index()
    data_inicial, data_final, dias = resolve_backfill_window()
    ufs = [str(uf).strip().upper()] if uf else list(PNCP_UFS_DEFAULT)
    mods = [int(m) for m in (modalidades or PNCP_MODALIDADES_DEFAULT)]
    page_budget = max(1, int(pages_per_scope or PNCP_INGEST_PLANNER_PAGES_PER_SCOPE))
    backlog_lim = max(
        0, int(contracts_without_items_limit or PNCP_INGEST_PLANNER_CONTRACTS_WITHOUT_ITEMS)
    )

    catalog_enqueued = 0
    catalog_skipped_paused = 0
    catalog_skipped_queue_full = 0
    items_enqueued = 0
    now = datetime.utcnow()
    pending_now = int(queue_stats().get("pending") or 0)
    bp = compute_ingest_backpressure(contracts_without_items=count_contracts_without_items())
    items_backlog = int(bp["items_backlog"])
    pause_catalog_backlog = bool(bp["pause_high_items"])
    pause_catalog_starve = bool(bp["starving"])
    pause_catalog_heavy = bool(bp["catalog_heavy"])
    plan_catalog = pending_now < max(0, int(PNCP_INGEST_QUEUE_MAX_PENDING))
    plan_catalog = plan_catalog and not bool(bp["pause_catalog"])
    if not plan_catalog:
        catalog_skipped_queue_full = len(ufs) * len(mods)

    for scope_uf in ufs:
        if not plan_catalog:
            break
        for modalidade in mods:
            state = _get_ingest_state(scope_uf, modalidade)
            pause_until = _parse_iso_utc(state["paused_until"]) if state else None
            if pause_until and pause_until > now:
                catalog_skipped_paused += 1
                continue

            start_page, _ = _resolve_backfill_start_page(
                scope_uf,
                modalidade,
                data_inicial=data_inicial,
                data_final=data_final,
            )
            priority = (
                PRIORITY_GAP if state and state["last_error_kind"] else PRIORITY_NORMAL
            )

            for offset in range(page_budget):
                pagina = start_page + offset
                if enqueue_catalog_page(
                    uf=scope_uf,
                    modalidade=modalidade,
                    pagina=pagina,
                    data_inicial=data_inicial,
                    data_final=data_final,
                    priority=priority,
                ):
                    catalog_enqueued += 1

    if backlog_lim > 0:
        starve = max(0, int(effective_items_starve_backlog()))
        if items_backlog < starve:
            items_enqueued = topup_contract_items_if_starved(items_backlog=items_backlog)
        else:
            items_enqueued = enqueue_contracts_without_items(limit=backlog_lim)

    catalog_sync: Dict[str, Any] = {"skipped": True}
    if count_items_needing_catalog_metadata_sync() > 0:
        catalog_sync = sync_catalog_metadata_from_raw_json(
            batch_size=max(1000, int(PNCP_INGEST_SYNC_CATALOG_BATCH)),
            max_batches=1,
        )

    resultados_enqueued = enqueue_contracts_needing_resultados()

    return {
        "ok": True,
        "backfill_mode": is_ingest_backfill_mode(),
        "window": {
            "data_inicial": data_inicial,
            "data_final": data_final,
            "dias": dias,
        },
        "ufs": len(ufs),
        "modalidades": mods,
        "catalog_pages_enqueued": catalog_enqueued,
        "catalog_scopes_paused": catalog_skipped_paused,
        "catalog_skipped_queue_full": catalog_skipped_queue_full,
        "queue_pending_before": pending_now,
        "items_backlog_before": items_backlog,
        "catalog_paused_backlog": pause_catalog_backlog,
        "catalog_paused_starve": pause_catalog_starve,
        "catalog_paused_heavy": pause_catalog_heavy,
        "catalog_pending_before": bp.get("catalog_pending"),
        "contract_items_enqueued": items_enqueued,
        "resultados_enqueued": resultados_enqueued,
        "contracts_needing_resultados": count_contracts_needing_resultados(),
        "catalog_metadata_sync": catalog_sync,
    }
