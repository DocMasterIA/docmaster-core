"""Paridade FTS/título das plataformas com o PNCP local."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.federated_candidate_filter import (  # noqa: E402
    evaluate_platform_candidate,
    match_search_title_tier,
)
from app.platform_index.search import resolve_platform_fts_anchor  # noqa: E402


class PlatformPncpParityTests(unittest.TestCase):
    def test_fts_anchor_usa_preprocess_e_tier_nao_primeiro_token_cru(self):
        """Pedido com ruído à frente não ancora no token inútil (paridade PNCP)."""
        termo = "N° MANILHA DE CONCRETO SIMPLES 200MM"
        anchor = resolve_platform_fts_anchor(termo)
        self.assertTrue(len(anchor) >= 2, anchor)
        self.assertNotIn("°", anchor)
        self.assertTrue(
            "manilha" in anchor or "concreto" in anchor or anchor.isalpha(),
            msg=anchor,
        )

    def test_fts_anchor_caneta_simples(self):
        self.assertEqual(resolve_platform_fts_anchor("caneta azul"), "caneta")

    def test_titulo_casa_material_servico_como_pncp(self):
        """Match em desc+mat — núcleo do produto pode estar só no material_servico."""
        termo = "MANILHA DE CONCRETO SIMPLES 200MM, COMPRIMENTO 1,00M."
        ok, tier = evaluate_platform_candidate(
            termo,
            "PECA CATALOGO GENERICA",
            material_servico="MANILHA DE CONCRETO SIMPLES 200MM COMPRIMENTO 1,00M",
            quality_first=False,
        )
        self.assertTrue(ok, tier)
        self.assertIsNotNone(tier)

    def test_titulo_sem_material_rejeita_se_so_desc_fraca(self):
        termo = "FIO NYLON N° 4.0 COR PRETA COM AGULHA 4 CM"
        ok, _ = evaluate_platform_candidate(
            termo,
            "LUVA de seguranca tricota em fios de nylon",
            material_servico="",
        )
        self.assertFalse(ok)

    def test_match_search_title_tier_aceita_blob_combinado(self):
        termo = "ciprofloxacino colirio 0,3%"
        tier = match_search_title_tier(
            termo,
            "CIPROFLOXACINO",
            material_servico="COLIRIO OFTALMICO 0,3% FRASCO 5 ML",
            quality_first=True,
        )
        self.assertIn(tier, {"strict", "core"})


if __name__ == "__main__":
    unittest.main()
