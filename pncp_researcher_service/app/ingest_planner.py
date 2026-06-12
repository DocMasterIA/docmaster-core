"""Planejador: enfileira páginas de catálogo e contratos sem itens na janela de 365 dias."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import (
    PNCP_INGEST_ITEMS_REFRESH_DAYS,
    PNCP_INGEST_ITEMS_STARVE_BACKLOG,
    PNCP_INGEST_PLANNER_CONTRACTS_WITHOUT_ITEMS,
    PNCP_INGEST_PLANNER_CONTRACTS_WITHOUT_ITEMS_MAX,
    PNCP_INGEST_PLANNER_PAGES_PER_SCOPE,
    PNCP_INGEST_QUEUE_ENABLED,
    PNCP_INGEST_QUEUE_MAX_PENDING,
    PNCP_MODALIDADES_DEFAULT,
    PNCP_UFS_DEFAULT,
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
from .local_index import _get_ingest_state, _parse_iso_utc, _resolve_backfill_start_page, ensure_local_index

logger = logging.getLogger(__name__)

PRIORITY_GAP = 50
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
    days = max(0, int(PNCP_INGEST_ITEMS_REFRESH_DAYS or 0))
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


def topup_contract_items_if_starved(*, items_backlog: int) -> int:
    """Alimenta a fila de itens quando o backlog está baixo (crescimento do índice)."""
    starve = max(0, int(PNCP_INGEST_ITEMS_STARVE_BACKLOG))
    if items_backlog >= starve:
        return 0
    base = max(0, int(PNCP_INGEST_PLANNER_CONTRACTS_WITHOUT_ITEMS))
    ceiling = max(base, int(PNCP_INGEST_PLANNER_CONTRACTS_WITHOUT_ITEMS_MAX))
    # Quanto menor o backlog, mais contratos enfileiramos nesta rodada.
    if items_backlog <= 0:
        lim = ceiling
    else:
        lim = min(ceiling, base + (starve - items_backlog) * 4)
    n_gap = enqueue_contracts_without_items(limit=lim)
    remaining = max(0, lim - n_gap)
    n_stale = enqueue_contracts_needing_items_refresh(limit=remaining)
    if n_stale:
        logger.info(
            "ingest topup stale refresh enfileirados=%s gap=%s backlog_antes=%s",
            n_stale,
            n_gap,
            items_backlog,
        )
    return n_gap + n_stale


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
        starve = max(0, int(PNCP_INGEST_ITEMS_STARVE_BACKLOG))
        if items_backlog < starve:
            items_enqueued = topup_contract_items_if_starved(items_backlog=items_backlog)
        else:
            items_enqueued = enqueue_contracts_without_items(limit=backlog_lim)

    return {
        "ok": True,
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
    }
