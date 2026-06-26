"""Lote (busca_lote): sem PNCP ao vivo por padrão, poucos fallbacks, teto de tempo."""
from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.config import PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX
from app.schemas import MarketSearchRequest
from app.service import _bulk_search_timeout_response, market_search_intelligent


class BulkSearchPerformanceTests(unittest.IsolatedAsyncioTestCase):
    async def test_bulk_skips_hybrid_when_local_has_priced(self):
        payload = MarketSearchRequest(
            termo_busca="ITEM TESTE BULK HIBRIDO",
            busca_lote=True,
            max_paginas=3,
            tamanho_pagina=80,
            somente_homologados=False,
        )
        fake_local = {
            "ok": True,
            "itens": [
                {
                    "descricao_item": "ITEM TESTE",
                    "valor_unitario": 10.0,
                    "numero_pncp": "1",
                    "literal_match": 80,
                    "score_aprovacao": 85,
                }
            ],
            "stats": {"sql_rows_fetched": 5},
        }
        with patch("app.service.local_item_search", return_value=fake_local), patch(
            "app.service.market_search", new_callable=AsyncMock
        ) as live_mock:
            await market_search_intelligent(payload)
            live_mock.assert_not_called()

    async def test_bulk_tries_second_term_when_first_empty(self):
        payload = MarketSearchRequest(
            termo_busca="FIO NYLON N° 4.0 COR PRETA COM AGULHA 2,5 CM",
            busca_lote=True,
            somente_homologados=False,
        )
        calls: list[str] = []

        def _track(term, **kwargs):
            calls.append(term)
            if len(calls) >= 2:
                return {
                    "ok": True,
                    "itens": [
                        {
                            "descricao_item": "FIO NYLON AGULHA TESTE",
                            "valor_unitario": 2.5,
                            "fornecedor": "FORNECEDORA LTDA",
                            "cnpj_fornecedor": "12.345.678/0001-95",
                            "numero_pncp": "9",
                            "origem": "base_local_itens",
                            "search_tier": "strict",
                        }
                    ],
                    "stats": {},
                }
            return {"ok": True, "itens": [], "stats": {}}

        with patch("app.service.local_item_search", side_effect=_track), patch(
            "app.service.market_search",
            new_callable=AsyncMock,
            return_value={"ok": True, "itens": [], "stats": {}},
        ), patch(
            "app.service.enrich_homolog_items_from_pncp", new_callable=AsyncMock, return_value=0
        ):
            out = await market_search_intelligent(payload)
        self.assertEqual(len(calls), 2)
        self.assertGreaterEqual(len(out.get("itens") or []), 1)

    async def test_bulk_local_search_defers_supplier_filter(self):
        payload = MarketSearchRequest(
            termo_busca="ITEM TESTE BULK FILTRO",
            busca_lote=True,
            somente_homologados=False,
        )
        fake = {
            "ok": True,
            "itens": [
                {
                    "descricao_item": "ITEM TESTE",
                    "valor_unitario": 10.0,
                    "fornecedor": "Não se aplica",
                    "numero_pncp": "1",
                }
            ],
            "stats": {},
        }
        with patch("app.service.local_item_search", return_value=fake) as local_mock, patch(
            "app.service.market_search", new_callable=AsyncMock
        ):
            await market_search_intelligent(payload)
        self.assertGreaterEqual(local_mock.call_count, 1)
        kw = local_mock.call_args.kwargs
        self.assertFalse(kw.get("filtrar_fornecedor_para_exibicao", True))
        self.assertEqual(kw.get("enrich_homolog_max"), max(0, int(PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX)))

    async def test_bulk_enrich_top3_default_enabled(self):
        from app.config import PNCP_BULK_ENRICH_HOMOLOG_MAX

        self.assertGreaterEqual(int(PNCP_BULK_ENRICH_HOMOLOG_MAX), 1)

    def test_bulk_timeout_response_shape(self):
        payload = MarketSearchRequest(termo_busca="X", busca_lote=True)
        out = _bulk_search_timeout_response(payload)
        self.assertTrue(out.get("ok"))
        self.assertEqual(out.get("itens"), [])
        self.assertTrue((out.get("stats") or {}).get("busca_lote_timeout"))


if __name__ == "__main__":
    unittest.main()
