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
        self.assertTrue(item_matches_faixa_band(it, lo, hi, sentido="ambos"))

    def test_faixa_band_cima_rejeita_homologado_abaixo_com_estimado_na_faixa(self):
        lo, hi = 100.0, 120.0
        it = {
            "valor_unitario_homologado": 85.0,
            "valor_unitario_estimado": 115.0,
            "valor_unitario": 85.0,
        }
        self.assertFalse(item_matches_faixa_band(it, lo, hi, sentido="cima"))

    def test_faixa_band_baixo_rejeita_homologado_acima_com_estimado_na_faixa(self):
        lo, hi = 80.0, 100.0
        it = {
            "valor_unitario_homologado": 105.0,
            "valor_unitario_estimado": 90.0,
            "valor_unitario": 105.0,
        }
        self.assertFalse(item_matches_faixa_band(it, lo, hi, sentido="baixo"))

    def test_faixa_band_none_sentido_nao_usa_recall_estimado(self):
        """Sem sentido explícito: só preço canônico (não recall via estimado)."""
        lo, hi = 100.0, 120.0
        it = {
            "valor_unitario_homologado": 85.0,
            "valor_unitario_estimado": 115.0,
            "valor_unitario": 85.0,
        }
        self.assertFalse(item_matches_faixa_band(it, lo, hi, sentido=None))

    def test_faixa_cima_rejeita_preco_abaixo_do_base_caso_real(self):
        """Base R$ 3.419 +50% cima → mínimo é o base; R$ 3.070 deve ser rejeitado."""
        base = 3419.0
        lo, hi = base, base * 1.5
        it = {"valor_unitario_homologado": 3070.0, "valor_unitario": 3070.0}
        self.assertFalse(item_matches_faixa_band(it, lo, hi, sentido="cima"))
        it_ok = {"valor_unitario_homologado": 3500.0, "valor_unitario": 3500.0}
        self.assertTrue(item_matches_faixa_band(it_ok, lo, hi, sentido="cima"))

    def test_cima_rejeita_apos_enrich_homolog_abaixo_base(self):
        """Homologado abaixo do base com sentido cima — rejeitado."""
        from app.pricing_faixa import compute_faixa_regional

        base = 19.16
        lo, hi = compute_faixa_regional(base, 20.0, sentido="cima")
        pos = {
            "valor_unitario_homologado": 17.59,
            "valor_unitario": 17.59,
            "item_homologado": True,
        }
        self.assertFalse(item_matches_faixa_band(pos, lo, hi, sentido="cima"))

    def test_cima_rejeita_homologado_sem_preco_com_catalogo_na_faixa(self):
        """Homologado sem preço vencedor: não usar catálogo inflado no gate cima."""
        from app.pricing_display import row_unit_price_for_faixa_gate
        from app.pricing_faixa import compute_faixa_regional

        base = 19.0
        lo, hi = compute_faixa_regional(base, 50.0, sentido="cima")
        it = {"valor_unitario": 22.0, "item_homologado": True}
        self.assertEqual(row_unit_price_for_faixa_gate(it, sentido="cima"), 0.0)
        self.assertFalse(item_matches_faixa_band(it, lo, hi, sentido="cima"))
        it_ok = {"valor_unitario_homologado": 21.0, "valor_unitario": 21.0, "item_homologado": True}
        self.assertTrue(item_matches_faixa_band(it_ok, lo, hi, sentido="cima"))


if __name__ == "__main__":
    unittest.main()
