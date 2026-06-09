from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.local_index import (  # noqa: E402
    _build_fts_match_query,
    _build_search_tokens,
    _row_matches_search_tokens,
    derive_anchor_search_term,
)
from app.service import (  # noqa: E402
    _compute_match_score,
    _ensure_top3_from_pool,
    _infer_search_bottleneck,
)


class TestSearchRecallHelpers(unittest.TestCase):
    def test_short_term_not_truncated(self):
        termo, meta = derive_anchor_search_term("seringa 10ml")
        self.assertEqual(termo, "seringa 10ml")
        self.assertFalse(meta["termo_truncado"])

    def test_long_term_truncated_to_anchors(self):
        long_desc = (
            "SERINGA DESCARTAVEL 10ML LUER LOCK ESTERIL CAIXA 100 UN "
            "MATERIAL MEDICO HOSPITALAR USO UNICO EMBALAGEM INDIVIDUAL"
        )
        termo, meta = derive_anchor_search_term(long_desc, max_groups=10)
        self.assertTrue(meta["termo_truncado"])
        self.assertLessEqual(meta["termo_efetivo_tokens"], 10)
        self.assertLess(len(termo.split()), len(long_desc.split()))

    def test_infer_bottleneck_faixa(self):
        funil = {
            "sql_rows_fetched": 120,
            "local_homologados": 15,
            "scored_final_pool": 0,
            "eliminados_faixa_preco": 12,
        }
        self.assertEqual(_infer_search_bottleneck(funil, 0), "faixa_preco")

    def test_infer_bottleneck_indice_vazio(self):
        funil = {"sql_rows_fetched": 0, "local_homologados": 0}
        self.assertEqual(_infer_search_bottleneck(funil, 0), "indice_sem_match_fts")

    def test_compute_match_score_variant_groups_pharmaceutical(self):
        """Bug: singular/plural no mesmo grupo exigia 2 hits e zerava sem_raw na IA."""
        term = "ACEBROFILINA 50 MG/5 ML XAROPE C/120ML"
        _, meta = derive_anchor_search_term(term)
        groups = _build_search_tokens(meta.get("termo_efetivo") or term)
        desc = "ACEBROFILINA 50 MG/5 ML XAROPE FRASCO 120 ML"
        self.assertEqual(_compute_match_score(desc, groups, variant_groups=False), 0.0)
        self.assertGreater(_compute_match_score(desc, groups, variant_groups=True), 0.0)

    def test_fts_match_query_anchor_only(self):
        term = "ACEBROFILINA 50 MG/5 ML XAROPE C/120ML"
        q = _build_fts_match_query(term, anchor_only=True)
        self.assertIn("acebrofilina", q or "")
        self.assertNotIn("120ml", (q or "").lower())

    def test_row_matches_120ml_spaced(self):
        term = "ACEBROFILINA 50 MG/5 ML XAROPE C/120ML"
        groups = _build_search_tokens(term)
        desc = "ACEBROFILINA 50 MG/5 ML XAROPE FR 120 ML"
        self.assertTrue(_row_matches_search_tokens(desc, groups))

    def test_ensure_top3_from_pool_fills_to_three(self):
        pool = [
            {
                "numero_pncp": "1",
                "numero_item": "1",
                "descricao_item": "ABAIXADOR DE LINGUA",
                "orgao": "Org A",
                "valor_unitario": 10.0,
                "literal_match": 40.0,
                "score_aprovacao": 85,
            },
            {
                "numero_pncp": "2",
                "numero_item": "1",
                "descricao_item": "ABAIXADOR DE LINGUA",
                "orgao": "Org B",
                "valor_unitario": 11.0,
                "literal_match": 38.0,
                "score_aprovacao": 82,
            },
            {
                "numero_pncp": "3",
                "numero_item": "1",
                "descricao_item": "ABAIXADOR DE LINGUA",
                "orgao": "Org C",
                "valor_unitario": 12.0,
                "literal_match": 36.0,
                "score_aprovacao": 80,
            },
        ]
        got = _ensure_top3_from_pool([pool[0]], pool, target=3, termo_busca="ABAIXADOR DE LINGUA")
        self.assertEqual(len(got), 3)

    def test_derive_anchor_caps_long_cotacao_description(self):
        term = "ACEBROFILINA 50 MG 5 ML XAROPE FRASCO 120 ML ESTERIAL"
        eff, meta = derive_anchor_search_term(term)
        self.assertTrue(meta.get("termo_truncado"))
        self.assertLessEqual(meta.get("termo_efetivo_tokens", 99), 8)
        self.assertIn("acebrofilina", eff.lower())


if __name__ == "__main__":
    unittest.main()
