"""Testes de extração de embalagem e rerank por pack size."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.local_rerank import apply_local_rerank_top3, compute_local_rerank_score  # noqa: E402
from app.pack_size_match import (  # noqa: E402
    extract_pack_hints_from_item,
    extract_pack_hints_from_term,
    pack_size_rerank_adjustment,
)


class PackSizeMatchTests(unittest.TestCase):
    def test_extract_from_term_c100(self):
        h = extract_pack_hints_from_term("ABAIXADOR DE LINGUA C/100 UNIDADES")
        self.assertEqual(h.pack_units, 100)

    def test_extract_from_term_caixa(self):
        h = extract_pack_hints_from_term("AGULHA 13X45 CX C/100 UNIDADES")
        self.assertEqual(h.pack_units, 100)

    def test_extract_from_unidade_pacote_50(self):
        item = {
            "descricao_item": "ABAIXADOR LÍNGUA",
            "unidade_medida": "PACOTE 50,00 UN",
            "quantidade": 150,
        }
        h = extract_pack_hints_from_item(item)
        self.assertEqual(h.pack_units, 50)

    def test_extract_from_descricao_pct_100(self):
        item = {
            "descricao_item": "ABAIXADOR DE LINGUA DE MADEIRA PCT C/ 100 UN",
            "unidade_medida": "PCT",
            "quantidade": 1000,
        }
        h = extract_pack_hints_from_item(item)
        self.assertIn(100, h.candidates)

    def test_penalize_50_vs_want_100(self):
        termo = "ABAIXADOR DE LINGUA C/100 UNIDADES"
        bad = {
            "descricao_item": "ABAIXADOR LÍNGUA",
            "unidade_medida": "Pacote 50,00 UN",
            "quantidade": 250,
            "literal_match": 70,
            "score_aprovacao": 85,
        }
        good = {
            "descricao_item": "ABAIXADOR DE LINGUA PCT C/ 100 UNIDADES",
            "unidade_medida": "PCT",
            "quantidade": 300,
            "literal_match": 76,
            "score_aprovacao": 85,
        }
        self.assertLess(pack_size_rerank_adjustment(termo, bad), -30)
        self.assertGreater(pack_size_rerank_adjustment(termo, good), 20)

    def test_rerank_demotes_pacote_50(self):
        termo = "ABAIXADOR DE LINGUA C/100 UNIDADES"
        qg = [["abaixador"], ["lingua"]]
        pool = [
            {
                "descricao_item": "ABAIXADOR LÍNGUA",
                "unidade_medida": "PACOTE 50,00 UN",
                "quantidade": 150,
                "orgao": "Org A",
                "literal_match": 72,
                "score_aprovacao": 88,
                "valor_unitario": 7.0,
                "numero_pncp": "1",
            },
            {
                "descricao_item": "ABAIXADOR DE LINGUA DE MADEIRA PCT C/ 100 UN",
                "unidade_medida": "PCT",
                "quantidade": 1000,
                "orgao": "Org B",
                "literal_match": 71,
                "score_aprovacao": 86,
                "valor_unitario": 7.1,
                "numero_pncp": "2",
            },
            {
                "descricao_item": "ABAIXADOR DE LÍNGUA PCT C/100 UNIDADES",
                "unidade_medida": "PACOTE",
                "quantidade": 50,
                "orgao": "Org C",
                "literal_match": 70,
                "score_aprovacao": 84,
                "valor_unitario": 7.2,
                "numero_pncp": "3",
            },
        ]
        top3, used = apply_local_rerank_top3(
            "ABAIXADOR DE LINGUA",
            pool,
            query_groups=qg,
            min_ok=50,
            max_candidates=24,
            termo_raw=termo,
        )
        self.assertTrue(used)
        first = (top3[0].get("descricao_item") or "").upper()
        self.assertNotIn("50,00", str(top3[0].get("unidade_medida") or ""))
        self.assertTrue("100" in first or "100" in str(top3[0].get("unidade_medida") or ""))

    def test_score_good_beats_bad(self):
        termo = "ABAIXADOR DE LINGUA C/100 UNIDADES"
        qg = [["abaixador"], ["lingua"]]
        bad = {
            "descricao_item": "ABAIXADOR LÍNGUA",
            "unidade_medida": "Pacote 50,00 UN",
            "literal_match": 72,
            "score_aprovacao": 88,
        }
        good = {
            "descricao_item": "ABAIXADOR PCT C/100 UN",
            "unidade_medida": "PCT",
            "literal_match": 70,
            "score_aprovacao": 84,
        }
        sb = compute_local_rerank_score("ABAIXADOR DE LINGUA", bad, qg, termo_raw=termo)
        sg = compute_local_rerank_score("ABAIXADOR DE LINGUA", good, qg, termo_raw=termo)
        self.assertGreater(sg, sb)


if __name__ == "__main__":
    unittest.main()
