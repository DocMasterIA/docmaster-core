from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.local_index import (  # noqa: E402
    _enrich_homolog_items_from_pncp_sync,
    enrich_homolog_items_from_pncp,
    enrich_local_search_result,
)


def _sample_item() -> dict:
    return {
        "item_homologado": True,
        "numero_pncp": "12345678000195-1-000001",
        "ano_compra": 2024,
        "sequencial_compra": 1,
        "numero_item": "3",
        "situacao_compra": "Homologada",
    }


class TestSearchEnrichAsync(unittest.TestCase):
    def test_sync_wrapper_skips_when_event_loop_running(self):
        async def _inside_loop():
            item = _sample_item()
            n = _enrich_homolog_items_from_pncp_sync([item], max_n=1)
            self.assertEqual(n, 0)
            self.assertFalse(str(item.get("cnpj_fornecedor") or "").strip())

        asyncio.run(_inside_loop())

    def test_enrich_runs_inside_async_context(self):
        async def _run():
            item = _sample_item()
            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            snap = {
                "cnpj_fornecedor": "12.345.678/0001-95",
                "fornecedor": "FORNECEDORA EXEMPLO LTDA",
                "fornecedor_fonte": "pncp_resultado_item",
            }
            with patch("app.pncp_client.create_pncp_http_client", return_value=mock_client):
                with patch(
                    "app.pncp_client.get_contract_supplier_snapshot",
                    new=AsyncMock(return_value=snap),
                ):
                    n = await enrich_homolog_items_from_pncp([item], max_n=1)
            self.assertEqual(n, 1)
            self.assertEqual(item["cnpj_fornecedor"], "12.345.678/0001-95")
            self.assertEqual(item["fornecedor"], "FORNECEDORA EXEMPLO LTDA")
            self.assertTrue(item.get("fornecedor_busca_pncp"))

        asyncio.run(_run())

    def test_enrich_local_search_result_updates_stats(self):
        async def _run():
            item = _sample_item()
            result = {"ok": True, "itens": [item], "stats": {"total_registros": 1}}
            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            snap = {
                "cnpj_fornecedor": "12.345.678/0001-95",
                "fornecedor": "FORNECEDORA EXEMPLO LTDA",
            }
            with patch("app.pncp_client.create_pncp_http_client", return_value=mock_client):
                with patch(
                    "app.pncp_client.get_contract_supplier_snapshot",
                    new=AsyncMock(return_value=snap),
                ):
                    out = await enrich_local_search_result(result, max_n=1)
            self.assertEqual(out["stats"]["enriquecidos_pncp_na_busca"], 1)
            self.assertEqual(out["stats"]["itens_com_cnpj_fornecedor"], 1)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
