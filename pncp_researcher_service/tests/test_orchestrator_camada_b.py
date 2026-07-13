"""Camada B — pipeline unificado pós-merge multi-fonte."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.adapters.contracts import FederatedSearchQuery, MarketPriceHit
from app.adapters.federated import federated_search
from app.adapters.orchestrator import prepare_federated_candidate_rows


def _hit(
    *,
    plataforma: str = "pncp",
    desc: str = "PAPEL A4 REGRESSAO",
    price: float = 25.0,
    item_id: str = "abc:1",
) -> MarketPriceHit:
    return MarketPriceHit(
        plataforma=plataforma,
        plataforma_item_id=item_id,
        descricao_item=desc,
        valor_unitario=price,
        valor_unitario_homologado=price,
        orgao="Prefeitura Teste",
        uf="SC",
        fornecedor_cnpj="12345678000199",
        raw={
            "descricao_item": desc,
            "valor_unitario": price,
            "valor_unitario_homologado": price,
            "item_homologado": True,
            "orgao": "Prefeitura Teste",
            "uf": "SC",
            "cnpj_fornecedor": "12345678000199",
        },
    )


class OrchestratorPrepareTests(unittest.TestCase):
    def test_prepare_sets_federated_origem(self):
        rows = prepare_federated_candidate_rows([_hit(plataforma="pncp"), _hit(plataforma="tce_rs", item_id="x:2")])
        self.assertEqual(rows[0]["origem"], "federated_pncp")
        self.assertEqual(rows[1]["origem"], "federated_tce_rs")
        self.assertEqual(rows[0]["plataforma"], "pncp")
        self.assertEqual(rows[1]["plataforma"], "tce_rs")


class FederatedUnifiedPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_multi_source_uses_unified_orchestrator_not_price_sort(self):
        """Multi-fonte deve chamar orchestrate_federated_hits (Camada B), não top3 por preço."""
        query = FederatedSearchQuery(
            termo_busca="PAPEL A4 REGRESSAO",
            fontes_habilitadas=["pncp", "tce_rs"],
        )
        pncp_hits = [_hit(plataforma="pncp", price=30.0, item_id="p1:1")]
        tce_hits = [_hit(plataforma="tce_rs", price=20.0, item_id="t1:1", desc="PAPEL A4 REGRESSAO TCE")]

        async def _fake_pncp_search(_q):
            return pncp_hits

        async def _fake_tce_search(_q):
            return tce_hits

        mock_orch = AsyncMock(
            return_value={
                "ok": True,
                "filtros": {"termo_busca": "PAPEL A4 REGRESSAO", "fontes_habilitadas": ["pncp", "tce_rs"]},
                "stats": {"regra_selecao": "federated_unified_pipeline"},
                "itens": [{"descricao_item": "PAPEL A4 REGRESSAO", "plataforma": "pncp", "score_aprovacao": 88}],
            }
        )

        with patch("app.adapters.federated.get_adapters") as mock_get, patch(
            "app.adapters.federated._search_adapter_with_timeout"
        ) as mock_search, patch(
            "app.adapters.federated.assign_canonical_keys",
            side_effect=lambda hits, persist=True: hits,
        ), patch(
            "app.adapters.federated.orchestrate_federated_hits", mock_orch
        ):
            mock_get.return_value = []
            mock_search.side_effect = [
                ("pncp", pncp_hits, None),
                ("tce_rs", tce_hits, None),
            ]
            out = await federated_search(query)

        mock_orch.assert_awaited_once()
        self.assertTrue(out.get("ok"))
        self.assertEqual(out["stats"]["regra_selecao"], "federated_unified_pipeline")

    async def test_multi_source_end_to_end_scoring_fields(self):
        """Smoke: hits de duas fontes passam pelo pipeline real e retornam score_aprovacao."""
        query = FederatedSearchQuery(
            termo_busca="PAPEL A4 REGRESSAO",
            fontes_habilitadas=["pncp", "tce_rs"],
            somente_homologados=False,
        )
        hits_pncp = [_hit(plataforma="pncp", price=25.0)]
        hits_tce = [_hit(plataforma="tce_rs", price=24.0, item_id="tce:9", desc="PAPEL A4 REGRESSAO")]

        with patch(
            "app.adapters.federated._search_adapter_with_timeout",
            side_effect=[
                ("pncp", hits_pncp, None),
                ("tce_rs", hits_tce, None),
            ],
        ), patch(
            "app.adapters.federated.assign_canonical_keys",
            side_effect=lambda hits, persist=True: hits,
        ), patch(
            "app.service.enrich_homolog_items_from_pncp",
            new_callable=AsyncMock,
            return_value=0,
        ), patch(
            "app.service._rerank_top3_with_ia",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "app.service._enriquecer_interpretacao_ia_itens",
            new_callable=AsyncMock,
            return_value=None,
        ):
            out = await federated_search(query)

        self.assertTrue(out.get("ok"))
        itens = out.get("itens") or []
        self.assertGreaterEqual(len(itens), 1)
        self.assertIn("score_aprovacao", itens[0])
        self.assertIn("fontes_habilitadas", out.get("filtros", {}))
        stats = out.get("stats") or {}
        self.assertEqual(stats.get("regra_selecao"), "federated_unified_pipeline")


if __name__ == "__main__":
    unittest.main()
