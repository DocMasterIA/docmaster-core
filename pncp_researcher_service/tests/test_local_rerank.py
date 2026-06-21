"""Rerank local (sem LLM) — scoring e seleção top3."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.local_rerank import (  # noqa: E402
    apply_local_rerank_top3,
    compute_local_rerank_score,
    rerank_worth_it_ambiguous,
)


class LocalRerankTests(unittest.TestCase):
    def test_rerank_prefers_literal_core_over_medical_noise(self):
        termo = "parafuso aco sextavado"
        qg = [["parafuso"], ["aco"], ["sextavado"]]
        parafuso = {
            "descricao_item": "Parafuso de aço sextavado M8",
            "material_servico": "Material de fixação",
            "score_aprovacao": 62,
            "literal_match": 55.0,
            "cnpj_fornecedor": "12345678000199",
            "valor_unitario": 2.5,
        }
        implante = {
            "descricao_item": "Parafuso osseo titânio implante ortopedico hospitalar",
            "material_servico": "Ortopedia",
            "score_aprovacao": 68,
            "literal_match": 40.0,
        }
        s_ok = compute_local_rerank_score(termo, parafuso, qg)
        s_bad = compute_local_rerank_score(termo, implante, qg)
        self.assertGreater(s_ok, s_bad)

    def test_apply_local_rerank_returns_three(self):
        termo = "caneta esferografica azul"
        qg = [["caneta"], ["esferografica"], ["azul"]]
        pool = [
            {
                "descricao_item": f"Caneta esferográfica azul ponta {i} mm",
                "orgao": f"Orgão {i}",
                "score_aprovacao": 60 + i,
                "literal_match": 50.0 + i,
                "numero_pncp": f"PNCP-{i}",
                "valor_unitario": 1.0 + i,
            }
            for i in range(8)
        ]
        top3, used = apply_local_rerank_top3(
            termo,
            pool,
            query_groups=qg,
            min_ok=50,
            max_candidates=24,
        )
        self.assertTrue(used)
        self.assertEqual(len(top3), 3)
        self.assertTrue(all(x.get("local_rerank_usado") for x in top3))

    def test_worth_it_mixed_pool(self):
        self.assertTrue(rerank_worth_it_ambiguous("mixed_fallback", [{"score_aprovacao": 70}]))


if __name__ == "__main__":
    unittest.main()
