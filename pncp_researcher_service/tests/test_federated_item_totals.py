"""Totais federados PNCP + TCE-RS em local-index/stats."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from app.platform_index.aggregate_stats import attach_federated_item_totals
from app.platform_index.ingest.tce_rs.ingest import ingest_tce_rs_sample
from app.platform_index.registry import PlatformIndexSpec, register_platform_spec
from app.platform_index.schema import ensure_platform_index


class TestFederatedItemTotals(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.db_path = str(Path(self._tmp) / "tce_rs_local.db")
        os.environ["TCE_RS_LOCAL_DB_PATH"] = self.db_path
        ensure_platform_index("tce_rs", db_path=self.db_path)
        register_platform_spec(
            PlatformIndexSpec(
                id="tce_rs",
                label="TCE-RS (LicitaCon)",
                db_path=self.db_path,
                schema_kind="platform_index",
                inciso_default="inciso_ii",
                esfera_default="estadual",
                uf_scope="RS",
                enabled=True,
            )
        )

    def test_soma_pncp_mais_tce_no_total_todas_fontes(self):
        ingest_tce_rs_sample(db_path=self.db_path)
        out = attach_federated_item_totals({"ok": True, "total_itens": 1_590_000})
        self.assertEqual(out["total_itens"], 1_590_000)
        self.assertEqual(out["total_itens_pncp"], 1_590_000)
        self.assertGreater(out["total_itens_outras_plataformas"], 0)
        self.assertEqual(
            out["total_itens_todas_fontes"],
            out["total_itens_pncp"] + out["total_itens_outras_plataformas"],
        )
        ids = {p["id"] for p in out["por_plataforma"]}
        self.assertIn("pncp", ids)
        self.assertIn("tce_rs", ids)
        tce = next(p for p in out["por_plataforma"] if p["id"] == "tce_rs")
        self.assertEqual(tce["total_itens"], out["total_itens_outras_plataformas"])

    def test_sem_db_tce_mantem_so_pncp(self):
        missing = str(Path(self._tmp) / "ausente.db")
        register_platform_spec(
            PlatformIndexSpec(
                id="tce_rs",
                label="TCE-RS (LicitaCon)",
                db_path=missing,
                schema_kind="platform_index",
                inciso_default="inciso_ii",
                esfera_default="estadual",
                uf_scope="RS",
                enabled=True,
            )
        )
        out = attach_federated_item_totals({"total_itens": 100})
        self.assertEqual(out["total_itens_todas_fontes"], 100)
        self.assertEqual(out["total_itens_outras_plataformas"], 0)


if __name__ == "__main__":
    unittest.main()
