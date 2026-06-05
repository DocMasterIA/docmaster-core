"""Planejador: enfileira páginas de catálogo e contratos sem itens na janela de 365 dias."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import (
    PNCP_INGEST_ITEMS_BACKLOG_PAUSE_CATALOG,
    PNCP_INGEST_PLANNER_CONTRACTS_WITHOUT_ITEMS,
    PNCP_INGEST_PLANNER_PAGES_PER_SCOPE,
    PNCP_INGEST_QUEUE_ENABLED,
    PNCP_INGEST_QUEUE_MAX_PENDING,
    PNCP_MODALIDADES_DEFAULT,
    PNCP_UFS_DEFAULT,
)
from .ingest_dates import resolve_backfill_window
from .ingest_queue import (
    TASK_CONTRACT_ITEMS,
    enqueue_catalog_page,
    enqueue_contract_items,
    pending_by_task_type,
    queue_stats,
)
from .local_index import _get_ingest_state, _parse_iso_utc, _resolve_backfill_start_page, ensure_local_index

logger = logging.getLogger(__name__)

PRIORITY_GAP = 50
PRIORITY_NORMAL = 100
PRIORITY_BACKLOG_ITEMS = 80


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
    items_backlog = pending_by_task_type(TASK_CONTRACT_ITEMS)
    pause_catalog_backlog = items_backlog >= max(
        0, int(PNCP_INGEST_ITEMS_BACKLOG_PAUSE_CATALOG)
    )
    plan_catalog = pending_now < max(0, int(PNCP_INGEST_QUEUE_MAX_PENDING))
    plan_catalog = plan_catalog and not pause_catalog_backlog
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
        from .ingest_queue import _queue_conn

        with _queue_conn() as c:
            rows = c.execute(
                """
                SELECT c.numero_pncp
                FROM pncp_contratos c
                WHERE NOT EXISTS (
                    SELECT 1 FROM pncp_itens i WHERE i.numero_pncp = c.numero_pncp LIMIT 1
                )
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (backlog_lim,),
            ).fetchall()
        for r in rows:
            if enqueue_contract_items(
                numero_pncp=str(r["numero_pncp"]),
                priority=PRIORITY_BACKLOG_ITEMS,
            ):
                items_enqueued += 1

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
        "contract_items_enqueued": items_enqueued,
    }
