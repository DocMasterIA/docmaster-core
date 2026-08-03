"""Filtro de qualidade em hits federados — mesmo matcher PNCP (tiers)."""
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
    match_search_title_tier,
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
        self.assertIn(tier, {"strict", "core"})

    def test_filter_rows_drops_mismatch(self):
        termo = "ciprofloxacino colirio 0,3%"
        rows = [
            {"descricao": "CIPROFLOXACINO, CLORIDRATO 500MG COMPRIMIDOS", "id": 1},
            {"descricao": "CIPROFLOXACINO COLIRIO 0,3% 5ML", "id": 2},
        ]
        out = filter_platform_search_rows(termo, rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["id"], 2)
        self.assertIn(out[0].get("search_tier"), {"strict", "core"})

    def test_single_token_term_keeps_recall(self):
        termo = "caneta"
        ok, tier = evaluate_platform_candidate(termo, "CANETA ESFEROGRAFICA AZUL")
        self.assertTrue(ok)
        # Termo curto: tier PNCP real (strict com 1 grupo), não pseudo-flex ad hoc.
        self.assertEqual(tier, "strict")

    def test_termo_rico_rejeita_hit_so_primeiro_token(self):
        """QUALITY_FIRST: FTS no 1º token não mete título desconectado no top-3."""
        termo = "MANILHA DE CONCRETO SIMPLES 200MM, COMPRIMENTO 1,00M."
        ok_papel, _ = evaluate_platform_candidate(
            termo,
            "Papel Embrulho tipo papel: papel manilha, bobina, largura 150",
        )
        ok_fraco, _ = evaluate_platform_candidate(
            termo,
            "MANILHA SIMPLES PARA USO DIVERSO SEM ESPECIFICACAO",
        )
        ok_bom, tier = evaluate_platform_candidate(
            termo,
            "MANILHA DE CONCRETO SIMPLES 200MM COMPRIMENTO 1,00M",
        )
        self.assertFalse(ok_papel)
        self.assertFalse(ok_fraco)
        self.assertTrue(ok_bom)
        self.assertIn(tier, {"strict", "core"})

    def test_outro_termo_rico_rejeita_so_ancora_fts(self):
        """Genérico: não depende de dicionário manilha — outro pedido rico."""
        termo = "FIO NYLON N° 4.0 COR PRETA COM AGULHA 4 CM"
        ok_luva, _ = evaluate_platform_candidate(
            termo,
            "LUVA de seguranca tricota em fios de nylon tamanho M",
        )
        ok_bom, tier = evaluate_platform_candidate(
            termo,
            "FIO DE SUTURA NYLON N° 4.0 PRETO COM AGULHA 4 CM",
        )
        self.assertFalse(ok_luva)
        self.assertTrue(ok_bom)
        self.assertIn(tier, {"strict", "core"})

    def test_filtra_federado_bitola_e_titulo(self):
        termo = "MANILHA DE CONCRETO SIMPLES 200MM, COMPRIMENTO 1,00M."
        rows = [
            {
                "id": 1,
                "descricao": (
                    "Papel Embrulho tipo papel: papel manilha, largura: 150, comprimento: 100"
                ),
            },
            {"id": 2, "descricao": "MANILHA DE CONCRETO SIMPLES 300MM, COMPRIMENTO 1,00M."},
            {"id": 3, "descricao": "MANILHA DE CONCRETO SIMPLES 200MM COMPRIMENTO 1,00M"},
            {
                "id": 4,
                "descricao": "MANILHA ACO CARBONO GALVANIZADO COMPRIMENTO UTIL 66 ABERTURA 22",
            },
        ]
        out = filter_platform_search_rows(termo, rows)
        ids = [r["id"] for r in out]
        self.assertEqual(ids, [3])

    def test_titulo_usa_material_servico(self):
        termo = "ciprofloxacino colirio 0,3%"
        ok, tier = evaluate_platform_candidate(
            termo,
            "CIPROFLOXACINO",
            material_servico="COLIRIO OFTALMICO 0,3% 5ML",
        )
        self.assertTrue(ok)
        self.assertIn(tier, {"strict", "core"})

    def test_lista_manual_override_quality_first(self):
        ok, _ = evaluate_platform_candidate(
            "ciprofloxacino colirio 0,3%",
            "COMPRIMIDO QUALQUER COISA SEM RELACAO",
            quality_first=False,
        )
        self.assertFalse(ok)
        self.assertEqual(
            match_search_title_tier("caneta", "CANETA ESFEROGRAFICA", quality_first=False),
            "strict",
        )



if __name__ == "__main__":
    unittest.main()
