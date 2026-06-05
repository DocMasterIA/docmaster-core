from datetime import datetime, timedelta

from pncp_researcher_service.app.ingest_dates import (
    PNCP_API_MAX_LOOKBACK_DAYS,
    resolve_backfill_window,
)


def test_resolve_backfill_window_default_days(monkeypatch):
    monkeypatch.setattr(
        "pncp_researcher_service.app.ingest_dates.PNCP_LOCAL_BACKFILL_DAYS",
        365,
    )
    di, df, dias = resolve_backfill_window()
    end = datetime.utcnow().date()
    start = end - timedelta(days=365)
    assert di == start.strftime("%Y%m%d")
    assert df == end.strftime("%Y%m%d")
    assert dias == 365


def test_resolve_backfill_window_explicit_days():
    di, df, dias = resolve_backfill_window(days=90)
    end = datetime.utcnow().date()
    start = end - timedelta(days=90)
    assert dias == 90
    assert di == start.strftime("%Y%m%d")


def test_resolve_backfill_window_caps_at_api_max():
    _, _, dias = resolve_backfill_window(days=500)
    assert dias == PNCP_API_MAX_LOOKBACK_DAYS
