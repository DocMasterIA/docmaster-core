"""Testes do prompt Qwen para inexigibilidade."""
import unittest

from app.inexigibilidade_qwen_prompt import (
    build_inexigibilidade_qwen_full_prompt,
    inexigibilidade_variant_from_package,
)


class InexigibilidadeQwenPromptTests(unittest.TestCase):
    def test_variant_manutencao(self):
        self.assertEqual(
            inexigibilidade_variant_from_package("inexigibilidade_74_i_manutencao_veiculos"),
            "manutencao_veiculos",
        )

    def test_variant_fornecedor(self):
        self.assertEqual(
            inexigibilidade_variant_from_package("inexigibilidade_74_i_fornecedor_exclusivo"),
            "fornecedor_exclusivo",
        )

    def test_full_prompt_includes_art_74_and_json_keys(self):
        full = build_inexigibilidade_qwen_full_prompt(
            "Marca: Fiat\nModelo: Uno",
            "inexigibilidade_74_i_manutencao_veiculos",
        )
        self.assertIn("art. 74", full.lower())
        self.assertIn("dfd_objeto_referencia", full)
        self.assertIn("<<USER>>", full)
        self.assertIn("Fiat", full)


if __name__ == "__main__":
    unittest.main()
