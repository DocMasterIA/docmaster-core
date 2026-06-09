from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.local_index import derive_anchor_search_term  # noqa: E402
from app.service import _infer_search_bottleneck  # noqa: E402


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
        termo, meta = derive_anchor_search_term(long_desc, max_groups=8)
        self.assertTrue(meta["termo_truncado"])
        self.assertLessEqual(meta["termo_efetivo_tokens"], 8)
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


if __name__ == "__main__":
    unittest.main()
