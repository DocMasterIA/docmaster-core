"""fill-tr-slots preserva slot_package_key para roteamento Qwen com skip_context."""
from __future__ import annotations

import unittest

from app.tr_slots_llm import _package_key_from_override_or_context


class FillTrSlotsRoutingContextTests(unittest.TestCase):
    def test_package_key_from_context_when_skip_context(self):
        override = {"dispensa_fluxo_ui": "normal"}
        ctx = {"slot_package_key": "dispensa_75_ii_compras", "prefeitura": "Teste"}
        pk = _package_key_from_override_or_context(override, {"slot_package_key": ctx["slot_package_key"]})
        self.assertEqual(pk, "dispensa_75_ii_compras")

    def test_package_key_from_override_first(self):
        override = {"slot_package_key": "inexigibilidade_74_i_manutencao_veiculos"}
        ctx = {"slot_package_key": "dispensa_75_ii_compras"}
        pk = _package_key_from_override_or_context(override, ctx)
        self.assertEqual(pk, "inexigibilidade_74_i_manutencao_veiculos")


if __name__ == "__main__":
    unittest.main()
