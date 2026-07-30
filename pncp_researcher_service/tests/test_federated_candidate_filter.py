"""Filtro de qualidade em hits federados de plataformas indexadas."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.federated_candidate_filter import (  # noqa: E402
    evaluate_platform_candidate,
    filter_platform_search_rows,
)
from app.product_spec_match import product_form_strict_reject  # noqa: E402


class FederatedCandidateFilterTests(unittest.TestCase):
    def test_colirio_rejeita_comprimido(self):
        termo = "ciprofloxacino colirio 0,3%"
        bad = "CIPROFLOXACINO, CLORIDRATO 500MG CAIXA C/ 14 COMPRIMIDOS"
        good = "CIPROFLOXACINO COLIRIO OFTALMICO 0,3% FRASCO 5 ML"
        self.assertTrue(product_form_strict_reject(termo, {"descricao_item": bad}))
        ok_bad, _ = evaluate_platform_candidate(termo, bad)
        ok_good, tier = evaluate_platform_candidate(termo, good)
        self.assertFalse(ok_bad)
        self.assertTrue(ok_good)
        self.assertIn(tier, {"strict", "core", "flex"})

    def test_filter_rows_drops_mismatch(self):
        termo = "ciprofloxacino colirio 0,3%"
        rows = [
            {"descricao": "CIPROFLOXACINO, CLORIDRATO 500MG COMPRIMIDOS", "id": 1},
            {"descricao": "CIPROFLOXACINO COLIRIO 0,3% 5ML", "id": 2},
        ]
        out = filter_platform_search_rows(termo, rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["id"], 2)
        self.assertIn(out[0].get("search_tier"), {"strict", "core", "flex"})

    def test_single_token_term_keeps_recall(self):
        termo = "caneta"
        ok, tier = evaluate_platform_candidate(termo, "CANETA ESFEROGRAFICA AZUL")
        self.assertTrue(ok)
        self.assertEqual(tier, "flex")


if __name__ == "__main__":
    unittest.main()
