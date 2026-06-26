"""Testes de preço canônico para resposta PNCP."""

import unittest

from app.pricing_display import (
    filter_items_for_bulk_salvar_response,
    filter_items_for_search_display,
    filter_items_with_display_price,
    item_matches_faixa_band,
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

    def test_filter_bulk_requires_cnpj(self):
        rows = [
            {"valor_unitario_estimado": 5.0, "fornecedor": "FORNECEDORA OK LTDA"},
            {"valor_unitario_estimado": 3.0, "cnpj_fornecedor": "12.345.678/0001-95"},
            {
                "valor_unitario_estimado": 4.0,
                "cnpj_fornecedor": "12.345.678/0001-95",
                "fornecedor": "Não se aplica",
            },
        ]
        out = filter_items_for_bulk_salvar_response(rows)
        self.assertEqual(len(out), 2)
        for row in out:
            self.assertTrue(str(row.get("cnpj_fornecedor") or "").strip())

    def test_filter_manual_vs_price_only_equivalence_on_valid_rows(self):
        valid = [
            {"valor_unitario_estimado": 5.0, "fornecedor": "ACME LTDA"},
            {"valor_unitario_estimado": 3.0, "cnpj_fornecedor": "12.345.678/0001-95"},
        ]
        self.assertEqual(
            filter_items_for_search_display(valid),
            filter_items_with_display_price(valid),
        )

    def test_merge_homologated_pricing_from_snap(self):
        it = {
            "valor_unitario": 8.0,
            "valor_unitario_estimado": 8.0,
            "item_homologado": True,
        }
        snap = {"valor_unitario_homologado": 12.5, "valor_total_homologado": 125.0, "quantidade_homologada": 10}
        from app.pricing_display import merge_homologated_pricing_from_snap

        self.assertTrue(merge_homologated_pricing_from_snap(it, snap))
        self.assertAlmostEqual(it["valor_unitario_homologado"], 12.5)
        self.assertAlmostEqual(it["valor_unitario"], 12.5)
        self.assertAlmostEqual(row_display_unit_price(it), 12.5)

    def test_item_needs_homolog_pricing_lookup_with_estimado_only(self):
        from app.pricing_display import item_needs_homolog_pricing_lookup

        it = {
            "item_homologado": True,
            "valor_unitario": 8.0,
            "valor_unitario_estimado": 8.0,
            "numero_pncp": "12345678000195-1-000001",
            "ano_compra": 2024,
            "sequencial_compra": 1,
            "numero_item": "3",
        }
        self.assertTrue(item_needs_homolog_pricing_lookup(it))

    def test_faixa_band_aceita_estimado_quando_homologado_fora(self):
        lo, hi = 3.735, 11.205
        it = {
            "valor_unitario_homologado": 12.5,
            "valor_unitario_estimado": 9.0,
            "valor_unitario": 12.5,
        }
        self.assertTrue(item_matches_faixa_band(it, lo, hi))


if __name__ == "__main__":
    unittest.main()
