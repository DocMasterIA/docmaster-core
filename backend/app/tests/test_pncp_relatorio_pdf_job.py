from __future__ import annotations

from datetime import timedelta
from unittest import mock

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from backend.app.pncp_relatorio_api import (
    _relatorio_pdf_job_stale,
    _spawn_relatorio_pdf_worker,
)


class RelatorioPdfJobStaleTests(SimpleTestCase):
    @override_settings(PNCP_RELATORIO_PDF_JOB_STALE_SEC=60)
    def test_stale_when_processing_too_long(self):
        old = (timezone.now() - timedelta(seconds=120)).isoformat()
        self.assertTrue(
            _relatorio_pdf_job_stale({"status": "processing", "started": old}),
        )

    @override_settings(PNCP_RELATORIO_PDF_JOB_STALE_SEC=60)
    def test_not_stale_when_recent(self):
        recent = (timezone.now() - timedelta(seconds=5)).isoformat()
        self.assertFalse(
            _relatorio_pdf_job_stale({"status": "processing", "started": recent}),
        )


class RelatorioPdfSpawnTests(SimpleTestCase):
    def test_spawn_uses_threadpool_executor_when_no_gevent_hub(self):
        ran = []

        def _fn():
            ran.append(True)

        with mock.patch("backend.app.pncp_relatorio_api._get_pdf_job_executor") as get_exec:
            pool = mock.Mock()
            get_exec.return_value = pool
            with mock.patch("gevent.get_hub", side_effect=ImportError):
                _spawn_relatorio_pdf_worker(_fn)
            pool.submit.assert_called_once()
