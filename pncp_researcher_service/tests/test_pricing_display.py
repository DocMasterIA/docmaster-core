"""Testes de preço canônico para resposta PNCP."""

import unittest

from app.pricing_display import (
    filter_items_for_search_display,
    filter_items_with_display_price,
    normalize_item_pricing_for_response,
    row_display_unit_price,
)


class PricingDisplayTests(unittest.TestCase):
    def test_homologado_unit(self):
        it = {"valor_unitario_homologado": 12.5, "valor_unitario": 0}
        self.assertAlmostEqual(row_display_unit_price(it), 12.5)

    def test_estimado_quando_unit_zero(self):
        it = {
            "valor_unitario": 0,
            "valor_unitario_estimado": 8.0,
            "situacaoCompraItemNome": "Homologado",
        }
        self.assertAlmostEqual(row_display_unit_price(it), 8.0)

    def test_deriva_unit_de_total_estimado(self):
        it = {
            "valor_unitario": 0,
            "valor_total_estimado": 100.0,
            "quantidade_estimada": 10,
            "situacaoCompraItemNome": "Homologado",
        }
        self.assertAlmostEqual(row_display_unit_price(it), 10.0)

    def test_sem_preco_retorna_zero(self):
        it = {"valor_unitario": 0, "situacaoCompraItemNome": "Homologado"}
        self.assertEqual(row_display_unit_price(it), 0.0)

    def test_normalize_preenche_valor_unitario(self):
        it = {
            "valor_unitario": 0,
            "valor_unitario_estimado": 3.5,
            "valor_total_estimado": 35.0,
            "quantidade": 10,
        }
        self.assertTrue(normalize_item_pricing_for_response(it))
        self.assertAlmostEqual(it["valor_unitario"], 3.5)
        self.assertAlmostEqual(it["valor_total"], 35.0)

    def test_filter_remove_sem_preco(self):
        rows = [
            {"valor_unitario_estimado": 5.0, "fornecedor": "ACME LTDA"},
            {"valor_unitario": 0},
        ]
        out = filter_items_with_display_price(rows)
        self.assertEqual(len(out), 1)
        self.assertAlmostEqual(out[0]["valor_unitario"], 5.0)

    def test_filter_search_remove_fornecedor_placeholder(self):
        rows = [
            {"valor_unitario_estimado": 5.0, "fornecedor": "Não se aplica"},
            {"valor_unitario_estimado": 8.0, "fornecedor": "FORNECEDORA OK LTDA"},
            {"valor_unitario_estimado": 3.0, "cnpj_fornecedor": "12.345.678/0001-95"},
        ]
        out = filter_items_for_search_display(rows)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["fornecedor"], "FORNECEDORA OK LTDA")
        self.assertEqual(out[1]["cnpj_fornecedor"], "12.345.678/0001-95")


if __name__ == "__main__":
    unittest.main()
