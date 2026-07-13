"""FEED_PLATFORM isola feeds — plataformas não dependem do processo PNCP."""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_ORIG_SERVICE_MODE = os.environ.get("SERVICE_MODE")
_ORIG_FEED_PLATFORM = os.environ.get("FEED_PLATFORM")


@pytest.fixture(autouse=True)
def _restore_service_mode_modules():
    """reload() altera módulos globais — sempre volta ao estado default do processo."""
    yield
    if _ORIG_SERVICE_MODE is None:
        os.environ.pop("SERVICE_MODE", None)
    else:
        os.environ["SERVICE_MODE"] = _ORIG_SERVICE_MODE
    if _ORIG_FEED_PLATFORM is None:
        os.environ.pop("FEED_PLATFORM", None)
    else:
        os.environ["FEED_PLATFORM"] = _ORIG_FEED_PLATFORM
    import app.service_mode as sm
    import app.api_feed as api_feed

    importlib.reload(sm)
    importlib.reload(api_feed)


def test_pncp_feed_allows_worker_tce_does_not(monkeypatch):
    monkeypatch.setenv("SERVICE_MODE", "feed")
    monkeypatch.setenv("FEED_PLATFORM", "pncp")
    import app.service_mode as sm

    importlib.reload(sm)
    assert sm.is_pncp_feed() is True
    assert sm.pncp_ingest_worker_allowed() is True
    assert sm.is_platform_feed("tce_rs") is False
    assert sm.service_name() == "price_index_feed_pncp"

    monkeypatch.setenv("FEED_PLATFORM", "tce_rs")
    importlib.reload(sm)
    assert sm.is_pncp_feed() is False
    assert sm.pncp_ingest_worker_allowed() is False
    assert sm.is_platform_feed("tce_rs") is True
    assert sm.is_platform_feed("pncp") is False
    assert sm.service_name() == "price_index_feed_tce_rs"


def test_researcher_mode_no_feed(monkeypatch):
    monkeypatch.setenv("SERVICE_MODE", "researcher")
    monkeypatch.setenv("FEED_PLATFORM", "")
    import app.service_mode as sm

    importlib.reload(sm)
    assert sm.is_researcher_mode() is True
    assert sm.is_feed_mode() is False
    assert sm.pncp_ingest_worker_allowed() is False
    assert sm.service_name() == "price_researcher_service"


def test_tce_routes_404_on_pncp_feed(monkeypatch):
    monkeypatch.setenv("SERVICE_MODE", "feed")
    monkeypatch.setenv("FEED_PLATFORM", "pncp")
    import app.service_mode as sm
    import app.api_feed as api_feed

    importlib.reload(sm)
    importlib.reload(api_feed)

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        api_feed._require_platform_feed("tce_rs")
    assert exc.value.status_code == 404

    api_feed._require_pncp_feed()  # must not raise


def test_pncp_routes_404_on_tce_feed(monkeypatch):
    monkeypatch.setenv("SERVICE_MODE", "feed")
    monkeypatch.setenv("FEED_PLATFORM", "tce_rs")
    import app.service_mode as sm
    import app.api_feed as api_feed

    importlib.reload(sm)
    importlib.reload(api_feed)

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        api_feed._require_pncp_feed()
    assert exc.value.status_code == 404

    api_feed._require_platform_feed("tce_rs")
