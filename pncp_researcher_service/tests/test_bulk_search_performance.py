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

from app.schemas import MarketSearchRequest
from app.service import _bulk_search_timeout_response, market_search_intelligent


class BulkSearchPerformanceTests(unittest.IsolatedAsyncioTestCase):
    async def test_bulk_skips_hybrid_fallback_by_default(self):
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

    async def test_bulk_limits_term_fallbacks(self):
        payload = MarketSearchRequest(
            termo_busca="MEDICAMENTO LONGO COM VARIAS PALAVRAS EXTRA NO TERMO",
            busca_lote=True,
            max_paginas=3,
            somente_homologados=False,
        )
        calls: list[str] = []

        def _track(term, **kwargs):
            calls.append(term)
            return {"ok": True, "itens": [], "stats": {}}

        with patch("app.service.local_item_search", side_effect=_track), patch(
            "app.service.market_search", new_callable=AsyncMock
        ):
            await market_search_intelligent(payload)
        self.assertLessEqual(len(calls), 2)

    def test_bulk_timeout_response_shape(self):
        payload = MarketSearchRequest(termo_busca="X", busca_lote=True)
        out = _bulk_search_timeout_response(payload)
        self.assertTrue(out.get("ok"))
        self.assertEqual(out.get("itens"), [])
        self.assertTrue((out.get("stats") or {}).get("busca_lote_timeout"))


if __name__ == "__main__":
    unittest.main()
