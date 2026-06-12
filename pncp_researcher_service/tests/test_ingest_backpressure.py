import os
import sqlite3
import tempfile

import pytest

from pncp_researcher_service.app import ingest_queue
from pncp_researcher_service.app import local_index
from pncp_researcher_service.app.ingest_backpressure import compute_ingest_backpressure


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


def test_catalog_heavy_pauses_catalog_when_gap_grande(queue_db, monkeypatch):
    monkeypatch.setattr(
        "pncp_researcher_service.app.ingest_backpressure.is_ingest_backfill_mode",
        lambda: False,
    )
    monkeypatch.setattr(
        "pncp_researcher_service.app.ingest_backpressure.PNCP_INGEST_CATALOG_HEAVY_PENDING",
        100,
    )
    monkeypatch.setattr(
        "pncp_researcher_service.app.ingest_backpressure.effective_items_starve_backlog",
        lambda: 150,
    )
    monkeypatch.setattr(
        "pncp_researcher_service.app.ingest_backpressure.PNCP_INGEST_CATALOG_PAUSE_MIN_GAP",
        50,
    )
    now = "2026-06-11T12:00:00Z"
    with ingest_queue._queue_conn() as c:
        for i in range(120):
            c.execute(
                """
                INSERT INTO pncp_ingest_queue (
                    task_type, priority, uf, modalidade, pagina, data_inicial, data_final,
                    numero_pncp, payload_json, status, attempts, max_attempts,
                    last_error, available_at, created_at, updated_at
                ) VALUES ('catalog_page', 100, 'SP', 8, ?, '20250601', '20260601',
                    NULL, '{}', 'pending', 0, 5, NULL, ?, ?, ?)
                """,
                (i + 1, now, now, now),
            )
        c.commit()
    bp = compute_ingest_backpressure(contracts_without_items=200)
    assert bp["catalog_pending"] >= 100
    assert bp["catalog_heavy"] is True
    assert bp["pause_catalog"] is True


def test_gap_baixo_nunca_pausa_catalogo_mesmo_com_items_na_fila(queue_db, monkeypatch):
    """Topup enfileira 15 itens — catálogo não deve voltar a pausar se gap < min_gap."""
    monkeypatch.setattr(
        "pncp_researcher_service.app.ingest_backpressure.PNCP_INGEST_CATALOG_HEAVY_PENDING",
        100,
    )
    monkeypatch.setattr(
        "pncp_researcher_service.app.ingest_backpressure.PNCP_INGEST_CATALOG_PAUSE_MIN_GAP",
        50,
    )
    now = "2026-06-11T12:00:00Z"
    with ingest_queue._queue_conn() as c:
        for i in range(120):
            c.execute(
                """
                INSERT INTO pncp_ingest_queue (
                    task_type, priority, uf, modalidade, pagina, data_inicial, data_final,
                    numero_pncp, payload_json, status, attempts, max_attempts,
                    last_error, available_at, created_at, updated_at
                ) VALUES ('catalog_page', 100, 'SP', 8, ?, '20250601', '20260601',
                    NULL, '{}', 'pending', 0, 5, NULL, ?, ?, ?)
                """,
                (i + 1, now, now, now),
            )
        for i in range(15):
            c.execute(
                """
                INSERT INTO pncp_ingest_queue (
                    task_type, priority, uf, modalidade, pagina, data_inicial, data_final,
                    numero_pncp, payload_json, status, attempts, max_attempts,
                    last_error, available_at, created_at, updated_at
                ) VALUES ('contract_items', 80, NULL, NULL, NULL, NULL, NULL,
                    ?, '{}', 'pending', 0, 5, NULL, ?, ?, ?)
                """,
                (f"PNCP-GAP-{i}", now, now, now),
            )
        c.commit()
    bp = compute_ingest_backpressure(contracts_without_items=15)
    assert bp["gap_low"] is True
    assert bp["pause_catalog"] is False
    assert bp["catalog_heavy"] is False


def test_gap_baixo_reabre_catalogo(queue_db, monkeypatch):
    monkeypatch.setattr(
        "pncp_researcher_service.app.ingest_backpressure.PNCP_INGEST_CATALOG_HEAVY_PENDING",
        100,
    )
    monkeypatch.setattr(
        "pncp_researcher_service.app.ingest_backpressure.PNCP_INGEST_CATALOG_PAUSE_MIN_GAP",
        50,
    )
    now = "2026-06-11T12:00:00Z"
    with ingest_queue._queue_conn() as c:
        for i in range(120):
            c.execute(
                """
                INSERT INTO pncp_ingest_queue (
                    task_type, priority, uf, modalidade, pagina, data_inicial, data_final,
                    numero_pncp, payload_json, status, attempts, max_attempts,
                    last_error, available_at, created_at, updated_at
                ) VALUES ('catalog_page', 100, 'SP', 8, ?, '20250601', '20260601',
                    NULL, '{}', 'pending', 0, 5, NULL, ?, ?, ?)
                """,
                (i + 1, now, now, now),
            )
        c.commit()
    bp = compute_ingest_backpressure(contracts_without_items=15)
    assert bp["catalog_pending"] >= 100
    assert bp["catalog_heavy"] is False
    assert bp["pause_catalog"] is False


def test_backfill_mode_no_pause_catalog_with_large_backlog(queue_db, monkeypatch):
    monkeypatch.setattr(
        "pncp_researcher_service.app.ingest_backpressure.is_ingest_backfill_mode",
        lambda: True,
    )
    monkeypatch.setattr(
        "pncp_researcher_service.app.ingest_backpressure.effective_backlog_pause_catalog",
        lambda: 15000,
    )
    monkeypatch.setattr(
        "pncp_researcher_service.app.ingest_backpressure.effective_items_starve_backlog",
        lambda: 10000,
    )
    now = "2026-06-11T12:00:00Z"
    with ingest_queue._queue_conn() as c:
        for i in range(120):
            c.execute(
                """
                INSERT INTO pncp_ingest_queue (
                    task_type, priority, uf, modalidade, pagina, data_inicial, data_final,
                    numero_pncp, payload_json, status, attempts, max_attempts,
                    last_error, available_at, created_at, updated_at
                ) VALUES ('catalog_page', 100, 'SP', 8, ?, '20250601', '20260601',
                    NULL, '{}', 'pending', 0, 5, NULL, ?, ?, ?)
                """,
                (i + 1, now, now, now),
            )
        for i in range(5000):
            c.execute(
                """
                INSERT INTO pncp_ingest_queue (
                    task_type, priority, uf, modalidade, pagina, data_inicial, data_final,
                    numero_pncp, payload_json, status, attempts, max_attempts,
                    last_error, available_at, created_at, updated_at
                ) VALUES ('contract_items', 80, NULL, NULL, NULL, NULL, NULL,
                    ?, '{}', 'pending', 0, 5, NULL, ?, ?, ?)
                """,
                (f"PNCP-BF-{i}", now, now, now),
            )
        c.commit()
    bp = compute_ingest_backpressure(contracts_without_items=0)
    assert bp["backfill_mode"] is True
    assert bp["pause_catalog"] is False
    assert bp["catalog_heavy"] is False
