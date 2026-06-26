"""Sincronização de metadados do catálogo PNCP (raw_json → colunas indexadas)."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app import ingest_maintenance, ingest_queue, local_index


class CatalogMetadataSyncTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self._orig = local_index.PNCP_LOCAL_DB_PATH
        local_index.PNCP_LOCAL_DB_PATH = self.path
        ingest_queue.PNCP_LOCAL_DB_PATH = self.path
        local_index.ensure_local_index()

    def tearDown(self):
        local_index.PNCP_LOCAL_DB_PATH = self._orig
        ingest_queue.PNCP_LOCAL_DB_PATH = self._orig
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def _insert_homolog_raw(self, numero_pncp: str, numero_item: str = "1") -> None:
        catalog = {
            "numeroItem": numero_item,
            "descricao": "PARACETAMOL 500MG",
            "situacaoCompraItemNome": "Homologado",
            "temResultado": True,
            "valorUnitarioEstimado": 12.5,
            "quantidade": 10,
        }
        blob = zlib.compress(json.dumps(catalog, ensure_ascii=False).encode("utf-8"), level=6)
        with sqlite3.connect(self.path) as c:
            local_index._migrate_pncp_itens_homolog_columns(c)
            local_index._migrate_pncp_itens_supplier_columns(c)
            c.execute(
                """
                INSERT INTO pncp_itens (
                    numero_pncp, numero_item, descricao, item_fingerprint, updated_at,
                    valor_unitario, raw_json_zlib
                ) VALUES (?, ?, ?, ?, datetime('now'), ?, ?)
                """,
                (
                    numero_pncp,
                    numero_item,
                    "PARACETAMOL 500MG",
                    f"item:{numero_item}",
                    12.5,
                    blob,
                ),
            )
            c.commit()

    def test_sync_materializes_situacao_and_elegivel(self):
        self._insert_homolog_raw("PNCP-SYNC-1")
        self.assertEqual(local_index.count_items_needing_catalog_metadata_sync(), 1)
        out = local_index.sync_catalog_metadata_from_raw_json(batch_size=100, max_batches=1)
        self.assertEqual(out["updated"], 1)
        with sqlite3.connect(self.path) as c:
            row = c.execute(
                "SELECT situacao_item, fornecedor_elegivel, valor_unitario_estimado FROM pncp_itens"
            ).fetchone()
        self.assertEqual(row[0], "Homologado")
        self.assertEqual(row[1], 1)
        self.assertAlmostEqual(float(row[2]), 12.5)

    def test_list_contracts_needing_resultados_after_sync(self):
        self._insert_homolog_raw("PNCP-RES-1")
        self.assertEqual(local_index.list_contracts_needing_resultados(10), [])
        local_index.sync_catalog_metadata_from_raw_json(batch_size=100, max_batches=1)
        self.assertEqual(local_index.list_contracts_needing_resultados(10), ["PNCP-RES-1"])
        self.assertEqual(local_index.count_contracts_needing_resultados(), 1)

    def test_purge_keeps_pending_when_resultados_needed(self):
        self._insert_homolog_raw("PNCP-PURGE-1")
        local_index.sync_catalog_metadata_from_raw_json(batch_size=100, max_batches=1)
        ingest_queue.enqueue_contract_items(numero_pncp="PNCP-PURGE-1", priority=50)
        with patch("app.local_index.contract_needs_items_refresh", return_value=False), patch(
            "app.local_index.contract_has_items_needing_resultados", return_value=True
        ):
            purged = ingest_maintenance.purge_redundant_pending_item_tasks(limit=100)
        self.assertEqual(purged, 0)
        stats = ingest_queue.queue_stats()
        self.assertGreaterEqual(int(stats.get("pending") or 0), 1)


if __name__ == "__main__":
    unittest.main()
