import os
import sqlite3
import tempfile
from datetime import datetime, timedelta

import pytest

from pncp_researcher_service.app import local_index


@pytest.fixture()
def refresh_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(local_index, "PNCP_LOCAL_DB_PATH", path)
    local_index.ensure_local_index()
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


def _insert_item(numero_pncp: str, updated_at: str) -> None:
    with sqlite3.connect(local_index.PNCP_LOCAL_DB_PATH) as c:
        c.execute(
            """
            INSERT INTO pncp_itens (
                numero_pncp, descricao, item_fingerprint, updated_at
            ) VALUES (?, ?, ?, ?)
            """,
            (numero_pncp, "item teste", "1|item teste|||", updated_at),
        )
        c.commit()


def test_refresh_days_zero_always_fetches(refresh_db, monkeypatch):
    monkeypatch.setattr(local_index, "effective_items_refresh_days", lambda: 0)
    recent = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    _insert_item("PNCP-1", recent)
    assert local_index.contract_needs_items_refresh("PNCP-1") is True


def test_skip_when_items_are_fresh(refresh_db, monkeypatch):
    monkeypatch.setattr(local_index, "effective_items_refresh_days", lambda: 7)
    recent = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    _insert_item("PNCP-2", recent)
    assert local_index.contract_needs_items_refresh("PNCP-2") is False


def test_fetch_when_items_are_stale(refresh_db, monkeypatch):
    monkeypatch.setattr(local_index, "effective_items_refresh_days", lambda: 7)
    old = (datetime.utcnow() - timedelta(days=10)).isoformat(timespec="seconds") + "Z"
    _insert_item("PNCP-3", old)
    assert local_index.contract_needs_items_refresh("PNCP-3") is True


def test_fetch_when_contract_has_no_items(refresh_db, monkeypatch):
    monkeypatch.setattr(local_index, "effective_items_refresh_days", lambda: 7)
    assert local_index.contract_needs_items_refresh("PNCP-4") is True


def test_skip_when_verified_empty_recently(refresh_db, monkeypatch):
    monkeypatch.setattr(local_index, "effective_items_refresh_days", lambda: 7)
    with sqlite3.connect(local_index.PNCP_LOCAL_DB_PATH) as c:
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        c.execute(
            """
            INSERT INTO pncp_contratos (
                numero_pncp, updated_at, raw_json, itens_verificados_at
            ) VALUES (?, ?, '{}', ?)
            """,
            ("PNCP-EMPTY", now, now),
        )
        c.commit()
    assert local_index.contract_needs_items_refresh("PNCP-EMPTY") is False


def test_count_contracts_without_items_excludes_verified(refresh_db, monkeypatch):
    from pncp_researcher_service.app import ingest_queue

    monkeypatch.setattr(ingest_queue, "PNCP_LOCAL_DB_PATH", local_index.PNCP_LOCAL_DB_PATH)
    with sqlite3.connect(local_index.PNCP_LOCAL_DB_PATH) as c:
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        c.execute(
            """
            INSERT INTO pncp_contratos (numero_pncp, updated_at, raw_json)
            VALUES ('PNCP-GAP', ?, '{}')
            """,
            (now,),
        )
        c.execute(
            """
            INSERT INTO pncp_contratos (
                numero_pncp, updated_at, raw_json, itens_verificados_at
            ) VALUES ('PNCP-VER', ?, '{}', ?)
            """,
            (now, now),
        )
        c.commit()
    assert ingest_queue.count_contracts_without_items() == 1
    local_index.mark_contract_items_verified("PNCP-GAP")
    assert ingest_queue.count_contracts_without_items() == 0
