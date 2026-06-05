"""Janela de datas para ingestão PNCP (máx. 365 dias por request na API)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, Tuple

from .config import PNCP_LOCAL_BACKFILL_DAYS, PNCP_LOCAL_BACKFILL_MONTHS

PNCP_API_MAX_LOOKBACK_DAYS = 365


def resolve_backfill_window(
    *,
    months: Optional[int] = None,
    days: Optional[int] = None,
) -> Tuple[str, str, int]:
    """
    Retorna (data_inicial, data_final, dias_efetivos) em AAAAMMDD.
    Prioridade: ``days`` explícito > ``months`` legado > ``PNCP_LOCAL_BACKFILL_DAYS``.
    """
    end = datetime.utcnow().date()
    if days is not None:
        effective = min(PNCP_API_MAX_LOOKBACK_DAYS, max(1, int(days)))
    elif months is not None:
        effective = min(PNCP_API_MAX_LOOKBACK_DAYS, max(1, int(months) * 30))
    else:
        effective = min(PNCP_API_MAX_LOOKBACK_DAYS, max(1, int(PNCP_LOCAL_BACKFILL_DAYS)))
    start = end - timedelta(days=effective)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), effective


def window_dates(data_inicial: str, data_final: str) -> Tuple[date, date]:
    return (
        datetime.strptime(data_inicial, "%Y%m%d").date(),
        datetime.strptime(data_final, "%Y%m%d").date(),
    )
