"""Recall de tokens para specs (10 volumes, 70%, mg/ml)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.local_index import _build_search_tokens, _row_matches_search_tokens  # noqa: E402


class ProductSpecTokenRecallTests(unittest.TestCase):
    def test_10_volumes_matches_10_vol_in_description(self):
        tokens = _build_search_tokens("AGUA OXIGENADA 10 VOLUMES")
        self.assertTrue(tokens)
        desc = "AGUA OXIGENADA DEZ VOLUMES FRASCO 100 ML"
        # após normalize: agua oxigenada dez volumes...
        desc_norm = "agua oxigenada 10 vol frasco 100 ml"
        matched = _row_matches_search_tokens(desc_norm, tokens, min_match_ratio=1.0)
        self.assertTrue(matched)

    def test_70pct_token_group(self):
        tokens = _build_search_tokens("ALCOOL 70% FRASCO 1 LITRO")
        flat = {v for group in tokens for v in group}
        self.assertTrue(any("70" in v or "70pct" in v for v in flat))


if __name__ == "__main__":
    unittest.main()
