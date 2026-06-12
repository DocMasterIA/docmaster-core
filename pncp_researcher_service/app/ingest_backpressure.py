"""Regras de backpressure: evita worker preso só em catálogo sem alimentar itens."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .config import (
    PNCP_INGEST_CATALOG_HEAVY_PENDING,
    PNCP_INGEST_CATALOG_PAUSE_MIN_GAP,
    effective_backlog_pause_catalog,
    effective_items_starve_backlog,
    is_ingest_backfill_mode,
)
from .ingest_queue import TASK_CATALOG_PAGE, TASK_CONTRACT_ITEMS, backlog_by_task_type, pending_by_task_type


def compute_ingest_backpressure(
    *,
    contracts_without_items: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Decide se catálogo deve pausar para priorizar contract_items.

    Cenário inaceitável que isto previne: milhares de catalog_page pending,
    zero contract_items, items_ok=0 por horas — índice não cresce.

    Com gap SQLite baixo (poucos contratos sem itens), NÃO pausa catálogo —
    senão o índice estagna para sempre com milhares de páginas de catálogo congeladas.
    """
    items_backlog = backlog_by_task_type(TASK_CONTRACT_ITEMS)
    catalog_pending = pending_by_task_type(TASK_CATALOG_PAGE)
    items_pending = pending_by_task_type(TASK_CONTRACT_ITEMS)

    backfill = is_ingest_backfill_mode()
    starve_thresh = max(0, int(effective_items_starve_backlog()))
    heavy_thresh = max(1, int(PNCP_INGEST_CATALOG_HEAVY_PENDING))
    pause_high = max(0, int(effective_backlog_pause_catalog()))
    min_gap = max(0, int(PNCP_INGEST_CATALOG_PAUSE_MIN_GAP))
    gap = int(contracts_without_items) if contracts_without_items is not None else None
    gap_low = gap is not None and gap < min_gap

    starving = items_backlog < starve_thresh
    items_work_queued = items_backlog > 0
    gap_needs_drain = gap is None or gap >= min_gap

    catalog_heavy_raw = (
        catalog_pending >= heavy_thresh and items_backlog < max(starve_thresh, 500)
    )
    if backfill:
        catalog_heavy = False
        pause_starve = False
    elif gap_low:
        catalog_heavy = False
        pause_starve = False
    else:
        catalog_heavy = catalog_heavy_raw and (items_work_queued or gap_needs_drain)
        pause_starve = starving and (items_work_queued or gap_needs_drain)
    pause_high_items = items_backlog >= pause_high
    pause_catalog = pause_high_items if backfill else (
        pause_starve or catalog_heavy or pause_high_items
    )

    return {
        "items_backlog": items_backlog,
        "catalog_pending": catalog_pending,
        "items_pending": items_pending,
        "contracts_without_items": gap,
        "gap_low": gap_low,
        "starving": starving,
        "catalog_heavy": catalog_heavy,
        "catalog_heavy_raw": catalog_heavy_raw,
        "gap_needs_drain": gap_needs_drain,
        "pause_high_items": pause_high_items,
        "pause_catalog": pause_catalog,
        "backfill_mode": backfill,
    }
