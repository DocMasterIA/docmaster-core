"""Modo qualidade da busca inteligente (Qwen rerank + tiers rígidos)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app import config  # noqa: E402
from app.service import (  # noqa: E402
    _effective_min_score_aprovacao,
    _filter_ia_rerank_candidates,
    _ia_bulk_rerank_worth_it,
    _ia_rerank_on_for_request,
    _ia_rerank_pool_allowed,
    _ia_resumo_on_for_request,
    _select_top3_mixed_literal_similar,
)


class SearchQualityModeTests(unittest.TestCase):
    def test_ia_rerank_mixed_pool_allowed(self):
        self.assertTrue(_ia_rerank_pool_allowed("literal_only"))
        prev = config.PNCP_IA_RERANK_MIXED_POOL
        try:
            config.PNCP_IA_RERANK_MIXED_POOL = True
            self.assertTrue(_ia_rerank_pool_allowed("mixed_fallback"))
            config.PNCP_IA_RERANK_MIXED_POOL = False
            self.assertFalse(_ia_rerank_pool_allowed("mixed_fallback"))
        finally:
            config.PNCP_IA_RERANK_MIXED_POOL = prev

    def test_effective_min_score_floor(self):
        prev_q = config.PNCP_SEARCH_QUALITY_FIRST
        prev_m = config.PNCP_SEARCH_MIN_SCORE_APROVACAO
        try:
            config.PNCP_SEARCH_QUALITY_FIRST = True
            config.PNCP_SEARCH_MIN_SCORE_APROVACAO = 45
            self.assertEqual(_effective_min_score_aprovacao(), 50)
            config.PNCP_SEARCH_MIN_SCORE_APROVACAO = 60
            self.assertEqual(_effective_min_score_aprovacao(), 60)
        finally:
            config.PNCP_SEARCH_QUALITY_FIRST = prev_q
            config.PNCP_SEARCH_MIN_SCORE_APROVACAO = prev_m

    def test_filter_ia_drops_aggressive(self):
        prev = config.PNCP_SEARCH_QUALITY_FIRST
        try:
            config.PNCP_SEARCH_QUALITY_FIRST = True
            pool = [
                {"literal_match": 10, "score_aprovacao": 70, "match_agressivo": True},
                {"literal_match": 8, "score_aprovacao": 65},
            ]
            out = _filter_ia_rerank_candidates(pool)
            self.assertEqual(len(out), 1)
            self.assertFalse(out[0].get("match_agressivo"))
        finally:
            config.PNCP_SEARCH_QUALITY_FIRST = prev

    def test_mixed_top3_caps_similar(self):
        literal = [{"numero_pncp": "A", "literal_match": 9, "score_aprovacao": 80}]
        similar = [
            {"numero_pncp": "B", "literal_match": 3, "similaridade_encontrada": True, "score_aprovacao": 60},
            {"numero_pncp": "C", "literal_match": 2, "similaridade_encontrada": True, "score_aprovacao": 58},
            {"numero_pncp": "D", "literal_match": 1, "similaridade_encontrada": True, "score_aprovacao": 55},
        ]
        top = _select_top3_mixed_literal_similar(literal, similar, max_similar=1)
        self.assertEqual(len(top), 3)
        sim_count = sum(1 for x in top if x.get("numero_pncp") in {"B", "C", "D"})
        self.assertLessEqual(sim_count, 1)

    def test_quality_first_default_in_config(self):
        self.assertTrue(config.PNCP_SEARCH_QUALITY_FIRST)
        self.assertFalse(config.PNCP_SEARCH_ANCHOR_TIER_ENABLED)

    def test_bulk_ia_flags(self):
        self.assertFalse(_ia_rerank_on_for_request(True))
        self.assertTrue(_ia_rerank_on_for_request(False))
        self.assertFalse(_ia_resumo_on_for_request(True))
        prev = config.PNCP_IA_RERANK_BULK_ENABLED
        try:
            config.PNCP_IA_RERANK_BULK_ENABLED = True
            self.assertTrue(_ia_rerank_on_for_request(True))
        finally:
            config.PNCP_IA_RERANK_BULK_ENABLED = prev

    def test_bulk_rerank_skips_clear_literal_pool(self):
        pool = [
            {"literal_match": 90, "score_aprovacao": 88},
            {"literal_match": 85, "score_aprovacao": 82},
            {"literal_match": 40, "score_aprovacao": 55},
        ]
        self.assertFalse(_ia_bulk_rerank_worth_it("literal_only", pool))

    def test_bulk_rerank_runs_on_mixed_pool(self):
        pool = [{"literal_match": 90, "score_aprovacao": 88}]
        self.assertTrue(_ia_bulk_rerank_worth_it("mixed_fallback", pool))


if __name__ == "__main__":
    unittest.main()
