"""Testes de detecção de parada e heartbeat da ingestão."""
from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from unittest import mock

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app import config  # noqa: E402
from app import ingest_runtime as rt  # noqa: E402


class IngestRuntimeTests(unittest.TestCase):
    def setUp(self):
        rt._last_pending = None
        rt._last_progress_at = 0.0
        rt._last_items_progress_at = 0.0
        rt._last_batch_at = 0.0
        rt._stall_recoveries = 0
        rt._last_stall_recovery_at = 0.0
        rt._items_ok_window.clear()
        rt._item_rows_window.clear()
        rt._last_heartbeat_mono = 0.0
        rt.mark_worker_started()
        self._patches = [
            mock.patch.object(config, "PNCP_INGEST_WORKER_ENABLED", True),
            mock.patch.object(config, "PNCP_INGEST_QUEUE_ENABLED", True),
            mock.patch.object(config, "PNCP_INGEST_STALL_SECONDS", 900),
            mock.patch.object(config, "PNCP_INGEST_STALL_MIN_PENDING", 100),
            mock.patch.object(config, "PNCP_INGEST_ITEMS_STALL_SECONDS", 600),
            mock.patch.object(config, "PNCP_INGEST_STALL_RECOVERY_ENABLED", True),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()

    def test_stall_quando_fila_grande_sem_progresso(self):
        rt._last_pending = 500
        rt._last_progress_at = 1.0
        self.assertGreater(rt.seconds_since_progress(), 900)
        self.assertTrue(rt.is_ingest_stalled())

    def test_nao_stall_fila_pequena(self):
        rt._last_pending = 10
        rt._last_progress_at = 1.0
        self.assertFalse(rt.is_ingest_stalled())

    def test_progresso_por_items_ok_reseta_stall(self):
        rt._last_pending = 500
        rt._last_progress_at = 1.0
        rt._last_items_progress_at = 1.0
        rt.record_batch_result({"items_ok": 3, "catalog_ok": 0, "errors": 0, "queue": {"pending": 497}})
        self.assertFalse(rt.is_ingest_stalled())

    def test_items_feed_stall_com_trabalho_sem_items_ok(self):
        rt._last_items_progress_at = 1.0
        rt._last_batch_summary = {
            "items_backlog": 0,
            "contracts_without_items": 500,
            "queue": {"by_task_type": {"contract_items": {"pending": 0, "processing": 0}}},
        }
        self.assertGreater(rt.seconds_since_items_progress(), 600)
        self.assertTrue(rt.is_items_feed_stalled())
        self.assertTrue(rt.is_ingest_stalled())


if __name__ == "__main__":
    unittest.main()
