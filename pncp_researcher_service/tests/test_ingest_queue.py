import os
import sqlite3
import tempfile

import pytest

from pncp_researcher_service.app import ingest_queue


@pytest.fixture()
def queue_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(ingest_queue, "PNCP_LOCAL_DB_PATH", path)
    monkeypatch.setattr(
        "pncp_researcher_service.app.local_index.PNCP_LOCAL_DB_PATH",
        path,
    )
    with sqlite3.connect(path) as c:
        ingest_queue.ensure_ingest_queue(c)
        c.commit()
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


def test_enqueue_catalog_page_idempotent(queue_db):
    ok1 = ingest_queue.enqueue_catalog_page(
        uf="SP",
        modalidade=8,
        pagina=3,
        data_inicial="20250601",
        data_final="20260601",
    )
    ok2 = ingest_queue.enqueue_catalog_page(
        uf="SP",
        modalidade=8,
        pagina=3,
        data_inicial="20250601",
        data_final="20260601",
    )
    assert ok1 is True
    assert ok2 is False
    stats = ingest_queue.queue_stats()
    assert stats["pending"] == 1


def test_claim_and_complete_contract_items(queue_db):
    ingest_queue.enqueue_contract_items(numero_pncp="12345678000100-1-000001/2025")
    tasks = ingest_queue.claim_tasks(task_type=ingest_queue.TASK_CONTRACT_ITEMS, limit=5)
    assert len(tasks) == 1
    ingest_queue.mark_task_done(int(tasks[0]["id"]))
    stats = ingest_queue.queue_stats()
    assert stats["done"] == 1
    assert stats["pending"] == 0
