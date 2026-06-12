import os
import sqlite3
import tempfile

import pytest

from pncp_researcher_service.app import ingest_planner, ingest_queue
from pncp_researcher_service.app import local_index


@pytest.fixture()
def queue_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(ingest_queue, "PNCP_LOCAL_DB_PATH", path)
    monkeypatch.setattr(local_index, "PNCP_LOCAL_DB_PATH", path)
    with sqlite3.connect(path) as c:
        ingest_queue.ensure_ingest_queue(c)
        local_index.ensure_local_index()
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


def test_topup_enqueues_contracts_without_items(queue_db):
    now = "2026-06-11T12:00:00Z"
    with local_index._conn() as c:
        for n in ("PNCP-1", "PNCP-2", "PNCP-3"):
            c.execute(
                """
                INSERT INTO pncp_contratos (
                    numero_pncp, updated_at, raw_json
                ) VALUES (?, ?, '{}')
                """,
                (n, now),
            )
        c.commit()
    n = ingest_planner.topup_contract_items_if_starved(items_backlog=0)
    assert n == 3
    stats = ingest_queue.queue_stats()
    assert stats["pending"] == 3


def test_topup_enqueues_stale_refresh_when_gap_empty(queue_db, monkeypatch):
    monkeypatch.setattr(ingest_planner, "PNCP_INGEST_ITEMS_REFRESH_DAYS", 7)
    old = "2026-05-01T12:00:00Z"
    now = "2026-06-11T12:00:00Z"
    with local_index._conn() as c:
        c.execute(
            """
            INSERT INTO pncp_contratos (numero_pncp, updated_at, raw_json)
            VALUES ('PNCP-STALE', ?, '{}')
            """,
            (now,),
        )
        c.execute(
            """
            INSERT INTO pncp_itens (
                numero_pncp, descricao, item_fingerprint, updated_at
            ) VALUES ('PNCP-STALE', 'x', 'fp1', ?)
            """,
            (old,),
        )
        c.commit()
    n = ingest_planner.topup_contract_items_if_starved(items_backlog=0)
    assert n == 1
    stats = ingest_queue.queue_stats()
    assert stats["pending"] == 1


def test_topup_skips_stale_when_backlog_not_starved(queue_db, monkeypatch):
    monkeypatch.setattr(ingest_planner, "PNCP_INGEST_ITEMS_REFRESH_DAYS", 7)
    monkeypatch.setattr(ingest_planner, "PNCP_INGEST_ITEMS_STARVE_BACKLOG", 150)
    old = "2026-05-01T12:00:00Z"
    now = "2026-06-11T12:00:00Z"
    with local_index._conn() as c:
        c.execute(
            """
            INSERT INTO pncp_contratos (numero_pncp, updated_at, raw_json)
            VALUES ('PNCP-STALE', ?, '{}')
            """,
            (now,),
        )
        c.execute(
            """
            INSERT INTO pncp_itens (
                numero_pncp, descricao, item_fingerprint, updated_at
            ) VALUES ('PNCP-STALE', 'x', 'fp1', ?)
            """,
            (old,),
        )
        c.commit()
    n = ingest_planner.topup_contract_items_if_starved(items_backlog=200)
    assert n == 0
    assert ingest_queue.queue_stats()["pending"] == 0


def test_topup_no_stale_when_refresh_days_zero(queue_db, monkeypatch):
    monkeypatch.setattr(ingest_planner, "PNCP_INGEST_ITEMS_REFRESH_DAYS", 0)
    old = "2026-05-01T12:00:00Z"
    now = "2026-06-11T12:00:00Z"
    with local_index._conn() as c:
        c.execute(
            """
            INSERT INTO pncp_contratos (numero_pncp, updated_at, raw_json)
            VALUES ('PNCP-STALE', ?, '{}')
            """,
            (now,),
        )
        c.execute(
            """
            INSERT INTO pncp_itens (
                numero_pncp, descricao, item_fingerprint, updated_at
            ) VALUES ('PNCP-STALE', 'x', 'fp1', ?)
            """,
            (old,),
        )
        c.commit()
    n = ingest_planner.topup_contract_items_if_starved(items_backlog=0)
    assert n == 0


def test_plan_pauses_catalog_when_items_starved(queue_db, monkeypatch):
    monkeypatch.setattr(
        "pncp_researcher_service.app.ingest_planner.PNCP_INGEST_ITEMS_STARVE_BACKLOG",
        150,
    )
    monkeypatch.setattr(
        "pncp_researcher_service.app.ingest_backpressure.PNCP_INGEST_CATALOG_PAUSE_MIN_GAP",
        50,
    )
    now = "2026-06-11T12:00:00Z"
    with local_index._conn() as c:
        for i in range(60):
            c.execute(
                """
                INSERT INTO pncp_contratos (numero_pncp, updated_at, raw_json)
                VALUES (?, ?, '{}')
                """,
                (f"PNCP-GAP-{i}", now),
            )
        c.commit()
    out = ingest_planner.plan_ingest_queue()
    assert out["catalog_paused_starve"] is True
    assert out["catalog_pages_enqueued"] == 0
