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
    _match_row_search_tiers,
    _row_matches_search_tokens,
    build_search_query_tiers,
    derive_anchor_search_term,
)
from app.search_text_clean import preprocess_cotacao_search_term  # noqa: E402
from app.service import (  # noqa: E402
    _build_manual_parity_top3,
    _compute_match_score,
    _ensure_top3_from_pool,
    _infer_search_bottleneck,
    _iter_search_term_fallbacks,
    _row_price_for_faixa,
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
        groups = _build_search_tokens(term)
        desc = "ACEBROFILINA 50 MG/5 ML XAROPE FRASCO C/120ML"
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

    def test_preprocess_agulha_compacta_dimensao(self):
        raw = "AGULHA HIPODÊRMICA TAMANHO: 13 X 4,5 (26 G½) CX C/100 UNIDADES."
        pre = preprocess_cotacao_search_term(raw)
        self.assertIn("13x45", pre.lower())
        self.assertIn("26g", pre.lower())
        self.assertNotIn("unidades", pre.lower())
        self.assertFalse(pre.endswith("."))

    def test_agulha_longa_casa_catalogo_curto(self):
        term = "AGULHA HIPODÊRMICA TAMANHO: 13 X 4,5 (26 G½) CX C/100 UNIDADES"
        tiers = build_search_query_tiers(term)
        self.assertTrue(tiers)
        desc = "AGULHA HIPODERMICA 13X45 MM CX 100 UN"
        matched = _match_row_search_tiers(desc, tiers)
        self.assertIsNotNone(matched)
        self.assertIn(matched.label, ("strict", "core", "flex", "anchor"))
        self.assertNotEqual(matched.label, "anchor")

    def test_agulha_nao_casa_seringa(self):
        term = "AGULHA HIPODÊRMICA TAMANHO: 13 X 4,5 (26 G½) CX C/100 UNIDADES"
        tiers = build_search_query_tiers(term)
        self.assertIsNone(_match_row_search_tiers("SERINGA DESCARTAVEL 10ML", tiers))

    def test_search_term_fallbacks_incluem_nucleo_curto(self):
        term = "AGULHA HIPODÊRMICA TAMANHO: 13 X 4,5 (26 G½) CX C/100 UNIDADES."
        alts = _iter_search_term_fallbacks(term)
        self.assertTrue(alts)
        joined = " ".join(alts).lower()
        self.assertIn("13x45", joined)
        self.assertIn(term.lower().strip("."), joined.lower())

    def test_search_term_fallbacks_long_description_prioriza_ancora(self):
        term = (
            "ÁLCOOL GEL 70% EMBALAGEM DE 500ML - ÁLCOOL EM GEL 70% EMBALAGEM COM 500ML, "
            "COM DOSADOR PUMP. CONFORME EDITAL."
        )
        alts = _iter_search_term_fallbacks(term, prefer_anchor_first=True)
        self.assertTrue(alts)
        eff, meta = derive_anchor_search_term(term)
        self.assertTrue(meta.get("termo_truncado"))
        self.assertEqual(alts[0], eff)

    def test_manual_parity_top3_usa_preco_estimado(self):
        itens = [
            {
                "numero_pncp": "1",
                "numero_item": "1",
                "descricao_item": "AGULHA HIPODERMICA 13X45",
                "orgao": "Org A",
                "valor_unitario_estimado": 12.5,
                "search_tier": "core",
                "origem": "base_local_itens",
            },
            {
                "numero_pncp": "2",
                "numero_item": "1",
                "descricao_item": "AGULHA HIPODERMICA 13X45",
                "orgao": "Org B",
                "valor_unitario_estimado": 11.0,
                "search_tier": "flex",
                "origem": "base_local_itens",
            },
        ]
        self.assertGreater(_row_price_for_faixa(itens[0]), 0.0)
        top = _build_manual_parity_top3(itens, "AGULHA HIPODERMICA 13 X 4,5")
        self.assertGreaterEqual(len(top), 1)
        self.assertTrue(top[0].get("match_manual_parity"))


if __name__ == "__main__":
    unittest.main()
