import os
import sqlite3
import tempfile
from datetime import datetime, timedelta

import pytest

from pncp_researcher_service.app import ingest_maintenance, ingest_queue
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


def test_requeue_all_processing_on_startup(queue_db):
    ingest_queue.enqueue_catalog_page(
        uf="SP", modalidade=8, pagina=1,
        data_inicial="20250601", data_final="20260601",
    )
    tasks = ingest_queue.claim_tasks(task_type=ingest_queue.TASK_CATALOG_PAGE, limit=1)
    assert tasks and tasks[0]["status"] == "processing"
    n = ingest_maintenance.requeue_processing_tasks(stale_only=False, stale_seconds=900)
    assert n == 1
    stats = ingest_queue.queue_stats()
    assert stats["processing"] == 0
    assert stats["pending"] == 1


def test_revive_two_dead_same_key(queue_db):
    """Duas dead com mesma chave → purge deixa uma; revive sem IntegrityError."""
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    old = (datetime.utcnow() - timedelta(hours=2)).isoformat(timespec="seconds") + "Z"
    with ingest_queue._queue_conn() as c:
        for _ in range(2):
            c.execute(
                """
                INSERT INTO pncp_ingest_queue (
                    task_type, priority, uf, modalidade, pagina, data_inicial, data_final,
                    numero_pncp, payload_json, status, attempts, max_attempts,
                    last_error, available_at, created_at, updated_at
                ) VALUES ('catalog_page', 100, 'PR', 8, 3, '20250601', '20260601',
                    NULL, '{}', 'dead', 5, 5, 'json', ?, ?, ?)
                """,
                (now, old, old),
            )
        c.commit()
    purged = ingest_maintenance.purge_redundant_dead_tasks()
    assert purged == 1
    n = ingest_maintenance.revive_dead_tasks(limit=10, min_dead_age_seconds=600)
    assert n == 1
    stats = ingest_queue.queue_stats()
    assert stats["pending"] == 1
    assert stats["dead"] == 0


def test_revive_dead_skips_duplicate_pending(queue_db):
    """dead com mesma chave que pending → purge remove dead, não viola UNIQUE."""
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    old = (datetime.utcnow() - timedelta(hours=2)).isoformat(timespec="seconds") + "Z"
    ingest_queue.enqueue_catalog_page(
        uf="MG", modalidade=8, pagina=2,
        data_inicial="20250601", data_final="20260601",
    )
    with ingest_queue._queue_conn() as c:
        c.execute(
            """
            INSERT INTO pncp_ingest_queue (
                task_type, priority, uf, modalidade, pagina, data_inicial, data_final,
                numero_pncp, payload_json, status, attempts, max_attempts,
                last_error, available_at, created_at, updated_at
            ) VALUES ('catalog_page', 100, 'MG', 8, 2, '20250601', '20260601',
                NULL, '{}', 'dead', 5, 5, 'json', ?, ?, ?)
            """,
            (now, old, old),
        )
        c.commit()
    purged = ingest_maintenance.purge_redundant_dead_tasks()
    assert purged == 1
    n = ingest_maintenance.revive_dead_tasks(limit=10, min_dead_age_seconds=600)
    assert n == 0
    stats = ingest_queue.queue_stats()
    assert stats["pending"] == 1
    assert stats["dead"] == 0


def test_revive_dead_tasks_after_cooldown(queue_db):
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    old = (datetime.utcnow() - timedelta(hours=2)).isoformat(timespec="seconds") + "Z"
    with ingest_queue._queue_conn() as c:
        c.execute(
            """
            INSERT INTO pncp_ingest_queue (
                task_type, priority, uf, modalidade, pagina, data_inicial, data_final,
                numero_pncp, payload_json, status, attempts, max_attempts,
                last_error, available_at, created_at, updated_at
            ) VALUES ('catalog_page', 100, 'MG', 8, 2, '20250601', '20260601',
                NULL, '{}', 'dead', 5, 5, 'json', ?, ?, ?)
            """,
            (now, old, old),
        )
        c.commit()
    n = ingest_maintenance.revive_dead_tasks(limit=10, min_dead_age_seconds=600)
    assert n == 1
    stats = ingest_queue.queue_stats()
    assert stats["pending"] == 1
    assert stats["dead"] == 0


def test_resume_expired_scopes(queue_db):
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    past = (datetime.utcnow() - timedelta(minutes=5)).isoformat(timespec="seconds") + "Z"
    with local_index._conn() as c:
        c.execute(
            """
            INSERT INTO pncp_ingest_state (
                uf, modalidade, status, error_streak, last_error_kind,
                paused_until, updated_at
            ) VALUES ('AL', 8, 'paused_blocked', 2, 'json_invalid', ?, ?)
            """,
            (past, now),
        )
        c.commit()
    n = local_index.resume_expired_ingest_scopes()
    assert n == 1
    state = local_index._get_ingest_state("AL", 8)
    assert state["status"] == "active"
    assert state["paused_until"] is None


def test_self_heal_startup_runs_all(queue_db, monkeypatch):
    monkeypatch.setattr(
        "pncp_researcher_service.app.ingest_maintenance.PNCP_INGEST_SELF_HEAL_ENABLED",
        True,
    )
    out = ingest_maintenance.run_ingest_self_healing(mode="startup")
    assert out["ok"] is True
    assert "requeued_processing" in out


def test_reconcile_gap_after_done_item_tasks(queue_db):
    now = "2026-06-11T12:00:00Z"
    with local_index._conn() as c:
        c.execute(
            """
            INSERT INTO pncp_contratos (numero_pncp, updated_at, raw_json)
            VALUES ('PNCP-STUCK', ?, '{}')
            """,
            (now,),
        )
        c.commit()
    with ingest_queue._queue_conn() as c:
        c.execute(
            """
            INSERT INTO pncp_ingest_queue (
                task_type, priority, uf, modalidade, pagina, data_inicial, data_final,
                numero_pncp, payload_json, status, attempts, max_attempts,
                last_error, available_at, created_at, updated_at
            ) VALUES ('contract_items', 80, NULL, NULL, NULL, NULL, NULL,
                'PNCP-STUCK', '{}', 'done', 1, 5, NULL, ?, ?, ?)
            """,
            (now, now, now),
        )
        c.commit()
    assert ingest_queue.count_contracts_without_items() == 1
    n = ingest_maintenance.reconcile_gap_contracts_after_done_items()
    assert n == 1
    assert ingest_queue.count_contracts_without_items() == 0


def test_purge_redundant_pending_item_tasks(queue_db, monkeypatch):
    monkeypatch.setattr(local_index, "PNCP_INGEST_ITEMS_REFRESH_DAYS", 7)
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    recent = now
    with local_index._conn() as c:
        c.execute(
            """
            INSERT INTO pncp_contratos (numero_pncp, updated_at, raw_json)
            VALUES ('PNCP-FRESH', ?, '{}')
            """,
            (now,),
        )
        c.execute(
            """
            INSERT INTO pncp_itens (
                numero_pncp, descricao, item_fingerprint, updated_at
            ) VALUES ('PNCP-FRESH', 'parafuso', '1|parafuso|||', ?)
            """,
            (recent,),
        )
        c.commit()
    with ingest_queue._queue_conn() as c:
        c.execute(
            """
            INSERT INTO pncp_ingest_queue (
                task_type, priority, uf, modalidade, pagina, data_inicial, data_final,
                numero_pncp, payload_json, status, attempts, max_attempts,
                last_error, available_at, created_at, updated_at
            ) VALUES ('contract_items', 80, NULL, NULL, NULL, NULL, NULL,
                'PNCP-FRESH', '{}', 'pending', 0, 5, NULL, ?, ?, ?)
            """,
            (now, now, now),
        )
        c.commit()
    n = ingest_maintenance.purge_redundant_pending_item_tasks()
    assert n == 1
    stats = ingest_queue.queue_stats()
    assert stats["pending"] == 0
