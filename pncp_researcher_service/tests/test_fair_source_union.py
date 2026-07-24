from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.adapters.contracts import MarketPriceHit  # noqa: E402
from app.adapters.dedup import dedupe_hits  # noqa: E402
from app.adapters.pncp_adapter import PncpAdapter  # noqa: E402
from app.adapters.contracts import FederatedSearchQuery  # noqa: E402
from app.service import _select_top3_prioritize_federal  # noqa: E402


class TestFairSourceUnion(unittest.IsolatedAsyncioTestCase):
    async def test_pncp_multi_fonte_search_uses_local_pool_not_intelligent_top3(self):
        """PNCP no merge deve contribuir pool local, não top-3 do intelligent."""
        called = {"intelligent": False, "local": False}

        async def boom_intelligent(_payload):
            called["intelligent"] = True
            return {"itens": [{"descricao_item": "should-not-use", "valor_unitario": 1}]}

        def fake_local(*_a, **kwargs):
            called["local"] = True
            self.assertEqual(kwargs.get("limit"), 200)
            return {
                "itens": [
                    {
                        "numero_pncp": "1-1/2024",
                        "numero_item": "1",
                        "descricao_item": "Papel A4",
                        "valor_unitario": 20.0,
                        "valor_unitario_homologado": 20.0,
                        "search_tier": "strict",
                    },
                    {
                        "numero_pncp": "2-1/2024",
                        "numero_item": "1",
                        "descricao_item": "Papel A4 sulfite",
                        "valor_unitario": 21.0,
                        "valor_unitario_homologado": 21.0,
                        "search_tier": "core",
                    },
                ]
            }

        with patch("app.service.market_search_intelligent", side_effect=boom_intelligent), patch(
            "app.local_index.local_item_search", side_effect=fake_local
        ), patch(
            "app.adapters.pncp_adapter.PNCP_FEDERATED_PLATFORM_SEARCH_LIMIT",
            200,
        ):
            hits = await PncpAdapter().search(
                FederatedSearchQuery(termo_busca="papel a4", fontes_habilitadas=["pncp", "tce_rs"])
            )

        self.assertTrue(called["local"])
        self.assertFalse(called["intelligent"])
        self.assertEqual(len(hits), 2)
        self.assertTrue(all(h.plataforma == "pncp" for h in hits))

    def test_dedupe_preserves_pncp_and_tce(self):
        out = dedupe_hits(
            [
                MarketPriceHit(
                    plataforma="pncp",
                    plataforma_item_id="p:1",
                    descricao_item="Seringa 10ml",
                    valor_unitario=1.0,
                    canonical_key="soft|x",
                ),
                MarketPriceHit(
                    plataforma="tce_rs",
                    plataforma_item_id="t:1",
                    descricao_item="Seringa 10ml",
                    valor_unitario=1.1,
                    canonical_key="soft|x",
                ),
            ]
        )
        self.assertEqual({h.plataforma for h in out}, {"pncp", "tce_rs"})

    def test_federal_first_reserves_slot_for_estadual(self):
        federais = [
            {
                "plataforma": "pncp",
                "plataforma_item_id": f"f{i}",
                "descricao_item": f"Item fed {i}",
                "orgao": f"Orgao F{i}",
                "esfera": "federal",
                "esfera_administrativa": "federal",
                "score_aprovacao": 90 - i,
                "literal_match": 40,
                "valor_unitario": 10 + i,
            }
            for i in range(3)
        ]
        tce = {
            "plataforma": "tce_rs",
            "plataforma_item_id": "t1",
            "descricao_item": "Item estadual",
            "orgao": "Orgao TCE",
            "esfera": "estadual",
            "esfera_administrativa": "estadual",
            "score_aprovacao": 70,
            "literal_match": 35,
            "valor_unitario": 9.5,
        }
        got = _select_top3_prioritize_federal(federais + [tce])
        plats = {str(x.get("plataforma")) for x in got}
        self.assertIn("tce_rs", plats)
        self.assertEqual(len(got), 3)

    def test_mono_platform_top3_swaps_in_other_source(self):
        pncp_only = [
            {
                "plataforma": "pncp",
                "plataforma_item_id": f"p{i}",
                "descricao_item": f"Desc {i}",
                "orgao": f"O{i}",
                "esfera": "federal",
                "score_aprovacao": 75 - i,
                "literal_match": 30,
                "valor_unitario": 5 + i,
            }
            for i in range(3)
        ]
        cg = {
            "plataforma": "compras_gov",
            "plataforma_item_id": "c1",
            "descricao_item": "Desc compras",
            "orgao": "CGU",
            "esfera": "federal",
            "score_aprovacao": 68,
            "literal_match": 28,
            "valor_unitario": 5.2,
        }
        got = _select_top3_prioritize_federal(pncp_only + [cg])
        plats = {str(x.get("plataforma")) for x in got}
        self.assertIn("compras_gov", plats)


if __name__ == "__main__":
    unittest.main()
