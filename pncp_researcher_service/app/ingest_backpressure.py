"""Regras de backpressure: evita worker preso só em catálogo sem alimentar itens."""
from __future__ import annotations

from typing import Any, Dict

from .config import (
    PNCP_INGEST_CATALOG_HEAVY_PENDING,
    PNCP_INGEST_ITEMS_BACKLOG_PAUSE_CATALOG,
    PNCP_INGEST_ITEMS_STARVE_BACKLOG,
)
from .ingest_queue import TASK_CATALOG_PAGE, TASK_CONTRACT_ITEMS, backlog_by_task_type, pending_by_task_type


def compute_ingest_backpressure() -> Dict[str, Any]:
    """
    Decide se catálogo deve pausar para priorizar contract_items.

    Cenário inaceitável que isto previne: milhares de catalog_page pending,
    zero contract_items, items_ok=0 por horas — índice não cresce.
    """
    items_backlog = backlog_by_task_type(TASK_CONTRACT_ITEMS)
    catalog_pending = pending_by_task_type(TASK_CATALOG_PAGE)
    items_pending = pending_by_task_type(TASK_CONTRACT_ITEMS)

    starve_thresh = max(0, int(PNCP_INGEST_ITEMS_STARVE_BACKLOG))
    heavy_thresh = max(1, int(PNCP_INGEST_CATALOG_HEAVY_PENDING))
    pause_high = max(0, int(PNCP_INGEST_ITEMS_BACKLOG_PAUSE_CATALOG))

    starving = items_backlog < starve_thresh
    catalog_heavy = catalog_pending >= heavy_thresh and items_backlog < max(starve_thresh, 500)
    pause_high_items = items_backlog >= pause_high
    pause_catalog = starving or catalog_heavy or pause_high_items

    return {
        "items_backlog": items_backlog,
        "catalog_pending": catalog_pending,
        "items_pending": items_pending,
        "starving": starving,
        "catalog_heavy": catalog_heavy,
        "pause_high_items": pause_high_items,
        "pause_catalog": pause_catalog,
    }
