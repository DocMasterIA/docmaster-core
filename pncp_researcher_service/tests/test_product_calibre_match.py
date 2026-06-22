"""Calibre/tamanho, agulha, U/g e combos medicamentosos no rerank PNCP."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.product_spec_match import (  # noqa: E402
    extract_product_spec_from_term,
    product_combo_strict_reject,
    product_spec_rerank_adjustment,
    product_spec_strict_reject,
)
from app.search_text_clean import normalize_for_search, pre_clean_raw  # noqa: E402


class CalibreExtractTests(unittest.TestCase):
    def test_penrose_n_dot_2(self):
        self.assertIn("n2", normalize_for_search("DRENO DE PEN ROSE ESTÉRIL N. 2"))

    def test_penrose_no_01(self):
        self.assertIn("n01", pre_clean_raw("DRENO DE PENROSE No 01").replace(" ", ""))

    def test_extract_dreno_calibre(self):
        h = extract_product_spec_from_term("DRENO DE PEN ROSE ESTÉRIL N. 2")
        self.assertEqual(h.calibre, 2.0)

    def test_extract_luva_calibre(self):
        h = extract_product_spec_from_term("LUVA CIRÚRGICA ESTÉRIL Nº 6,5")
        self.assertEqual(h.calibre, 6.5)

    def test_extract_fio_calibre(self):
        h = extract_product_spec_from_term("FIO NYLON N° 4.0 COR PRETA COM AGULHA 2,5 CM")
        self.assertEqual(h.calibre, 4.0)
        self.assertEqual(h.needle_cm, 2.5)
        self.assertIsNone(h.width_cm)

    def test_extract_colagenase_u_per_g(self):
        h = extract_product_spec_from_term("COLAGENASE 0,6 U/G POMADA DERMATOLÓGICA 30G")
        self.assertEqual(h.units_per_g, 0.6)


class CalibreRerankTests(unittest.TestCase):
    def test_reject_dreno_numero_errado(self):
        term = "DRENO DE PEN ROSE ESTÉRIL N. 2"
        bad = {"descricao_item": "DRENO DE PENROSE No 01 ESTERILIZADO"}
        good = {"descricao_item": "DRENO DE PENROSE S/ GAZE Nº 02"}
        self.assertTrue(product_spec_strict_reject(term, bad))
        self.assertFalse(product_spec_strict_reject(term, good))
        self.assertLess(product_spec_rerank_adjustment(term, bad), -40)
        self.assertGreater(product_spec_rerank_adjustment(term, good), 20)

    def test_reject_luva_tamanho_errado(self):
        term = "LUVA CIRÚRGICA ESTÉRIL Nº 6,5"
        bad = {"descricao_item": "LUVA CIRÚRGICA ESTÉRIL N. 7.0"}
        good = {"descricao_item": "LUVA CIRURGICA ESTÉRIL N. 6,5 - PAR"}
        self.assertTrue(product_spec_strict_reject(term, bad))
        self.assertFalse(product_spec_strict_reject(term, good))

    def test_reject_fio_calibre_errado(self):
        term = "FIO NYLON N° 4.0 COR PRETA COM AGULHA 2,5 CM"
        bad = {"descricao_item": "FIO NYLON PRETO AGULHADO 0 COM AGULHA 3.0 CM"}
        self.assertTrue(product_spec_strict_reject(term, bad))
        self.assertLess(product_spec_rerank_adjustment(term, bad), -40)

    def test_reject_glicose_combo(self):
        term = "GLICOSE 50 % - 10 ML SOLUÇÃO INJETAVEL"
        combo = {
            "descricao_item": (
                "Dimenidrinato + Piridoxina, Cloridrato + Glicose + Frutose, "
                "3 mg + 5 mg + 100 mg + 100 mg/ml, Solução injetável, Ampola, 10 ml"
            )
        }
        pure = {"descricao_item": "SOLUÇÃO DE GLICOSE INJETAVEL 50% AMP 10ML"}
        self.assertTrue(product_combo_strict_reject(term, combo))
        self.assertTrue(product_spec_strict_reject(term, combo))
        self.assertFalse(product_combo_strict_reject(term, pure))

    def test_reject_colagenase_concentracao(self):
        term = "COLAGENASE 0,6 U/G POMADA DERMATOLÓGICA 30G"
        bad = {"descricao_item": "Colagenase, 1,2 U/g, Pomada Dermatológica, Bisnaga, 30 g"}
        good = {"descricao_item": "COLAGENASE 0,6 U/G PURA Pomada Dermatológica Bisnaga 30 gramas"}
        self.assertTrue(product_spec_strict_reject(term, bad))
        self.assertGreater(product_spec_rerank_adjustment(term, good), 20)


if __name__ == "__main__":
    unittest.main()
