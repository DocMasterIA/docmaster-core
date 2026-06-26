"""Testes de variáveis de produto (dose, %, volume, volumes) e rerank."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.local_rerank import apply_local_rerank_top3, compute_local_rerank_score  # noqa: E402
from app.product_spec_match import (  # noqa: E402
    extract_product_spec_from_term,
    product_spec_rerank_adjustment,
    product_spec_strict_reject,
    product_spec_strong_core_match,
)


class ProductSpecMatchTests(unittest.TestCase):
    def test_extract_adenosina_6mg(self):
        h = extract_product_spec_from_term("ADENOSINA 6 MG SOLUCAO INJETAVEL")
        self.assertEqual(h.dose_mg, 6.0)

    def test_extract_alcool_70_1litro(self):
        h = extract_product_spec_from_term("ALCOOL 70% FRASCO COM 1 LITRO")
        self.assertEqual(h.percent, 70.0)
        self.assertEqual(h.vol_l, 1.0)

    def test_extract_agua_oxigenada_10_volumes(self):
        h = extract_product_spec_from_term("AGUA OXIGENADA 10 VOLUMES")
        self.assertEqual(h.volumes, 10)

    def test_extract_medroxiprogesterona_50mg_ml(self):
        h = extract_product_spec_from_term("ACETATO DE MEDROXIPROGESTERONA SUSPENSAO INJETAVEL 50MG/ML")
        self.assertEqual(h.conc_mg_per_ml, 50.0)
        self.assertIsNone(h.dose_mg)

    def test_alcool_gel_500ml_strong_core_match(self):
        termo = "ÁLCOOL GEL 70% EMBALAGEM DE 500ML"
        item = {
            "descricao_item": (
                "Lote 55736 - ÁLCOOL ETÍLICO EM GEL, HIDRATADO 70%, EMBALAGEM DE 500 ML"
            ),
        }
        self.assertTrue(product_spec_strong_core_match(termo, item))
        self.assertFalse(product_spec_strict_reject(termo, item))
        self.assertGreaterEqual(product_spec_rerank_adjustment(termo, item), 35.0)

    def test_penalize_adenosina_3_vs_6mg(self):
        termo = "ADENOSINA 6 MG SOLUCAO INJETAVEL"
        bad = {"descricao_item": "ADENOSINA 3 MG SOLUCAO INJETAVEL AMPOLA"}
        good = {"descricao_item": "ADENOSINA 6 MG SOLUCAO INJETAVEL AMPOLA 2 ML"}
        self.assertLess(product_spec_rerank_adjustment(termo, bad), -40)
        self.assertGreater(product_spec_rerank_adjustment(termo, good), 20)
        self.assertTrue(product_spec_strict_reject(termo, bad))

    def test_penalize_alcool_5l_vs_1l(self):
        termo = "ALCOOL 70% FRASCO COM 1 LITRO"
        bad = {"descricao_item": "ALCOOL ETILICO HIDRATADO A 70% INPM EM FRASCO DE 5 LITROS"}
        good = {"descricao_item": "ALCOOL ETILICO HIDRATADO 70% FRASCO 1 LITRO"}
        self.assertLess(product_spec_rerank_adjustment(termo, bad), -40)
        self.assertGreater(product_spec_rerank_adjustment(termo, good), 40)

    def test_rerank_adenosina_prefere_6mg(self):
        termo = "ADENOSINA 6 MG SOLUCAO INJETAVEL"
        qg = [["adenosina"], ["6mg"]]
        pool = [
            {
                "descricao_item": "ADENOSINA 3 MG SOLUCAO INJETAVEL",
                "literal_match": 74,
                "score_aprovacao": 88,
                "valor_unitario": 12.0,
                "numero_pncp": "1",
            },
            {
                "descricao_item": "ADENOSINA 6 MG SOLUCAO INJETAVEL AMPOLA",
                "literal_match": 72,
                "score_aprovacao": 85,
                "valor_unitario": 13.0,
                "numero_pncp": "2",
            },
            {
                "descricao_item": "ADENOSINA 6 MG INJETAVEL",
                "literal_match": 70,
                "score_aprovacao": 84,
                "valor_unitario": 14.0,
                "numero_pncp": "3",
            },
        ]
        top3, used = apply_local_rerank_top3(
            "ADENOSINA 6 MG",
            pool,
            query_groups=qg,
            min_ok=50,
            max_candidates=24,
            termo_raw=termo,
        )
        self.assertTrue(used)
        first = (top3[0].get("descricao_item") or "").upper()
        self.assertIn("6 MG", first)
        self.assertNotIn("3 MG", first)

    def test_score_good_beats_bad_alcool(self):
        termo = "ALCOOL 70% FRASCO COM 1 LITRO"
        qg = [["alcool"], ["70pct"]]
        bad = {
            "descricao_item": "ALCOOL ETILICO 70% FRASCO 5 LITROS",
            "literal_match": 75,
            "score_aprovacao": 88,
        }
        good = {
            "descricao_item": "ALCOOL ETILICO HIDRATADO 70% FRASCO 1 LITRO",
            "literal_match": 72,
            "score_aprovacao": 84,
        }
        sb = compute_local_rerank_score("ALCOOL 70%", bad, qg, termo_raw=termo)
        sg = compute_local_rerank_score("ALCOOL 70%", good, qg, termo_raw=termo)
        self.assertGreater(sg, sb)


if __name__ == "__main__":
    unittest.main()
