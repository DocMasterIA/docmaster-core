"""Testes de faixa regional (valor base + variação + sentido)."""

import asyncio
import unittest

from app.pricing_faixa import compute_faixa_regional, normalize_variacao_sentido
from app.schemas import MarketSearchRequest
from app.service import _build_manual_parity_top3, _filter_rows_in_faixa, _preco_dentro_faixa, _row_price_for_faixa, market_search_intelligent


class PricingFaixaTests(unittest.TestCase):
    def test_ambos(self):
        lo, hi = compute_faixa_regional(100, 20, sentido="ambos")
        self.assertAlmostEqual(lo, 80.0)
        self.assertAlmostEqual(hi, 120.0)

    def test_baixo(self):
        lo, hi = compute_faixa_regional(15, 20, sentido="baixo")
        self.assertAlmostEqual(lo, 12.0)
        self.assertAlmostEqual(hi, 15.0)

    def test_cima(self):
        lo, hi = compute_faixa_regional(15, 20, sentido="cima")
        self.assertAlmostEqual(lo, 15.0)
        self.assertAlmostEqual(hi, 18.0)

    def test_sentido_invalido_cai_em_ambos(self):
        self.assertEqual(normalize_variacao_sentido("invalid"), "ambos")

    def test_sentido_aliases_pt(self):
        self.assertEqual(normalize_variacao_sentido("Para cima"), "cima")
        self.assertEqual(normalize_variacao_sentido("pra baixo"), "baixo")


class ManualParityFaixaTests(unittest.TestCase):
    def test_nao_relaxa_faixa_estreita(self):
        itens = [
            {"valor_unitario": 10.0, "descricao_item": "fora", "search_tier": "strict"},
            {"valor_unitario": 14.9, "descricao_item": "dentro", "search_tier": "strict"},
        ]
        out = _build_manual_parity_top3(
            itens,
            "teste",
            faixa_min=14.85,
            faixa_max=15.15,
            target=3,
        )
        self.assertEqual(len(out), 1)
        self.assertAlmostEqual(_row_price_for_faixa(out[0]), 14.9)


class MarketSearchFaixaIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_sentido_baixo_exclui_acima_do_base(self):
        payload = MarketSearchRequest(
            termo_busca="ALCOOL ETILICO 70",
            max_paginas=10,
            tamanho_pagina=80,
            valor_base_referencia=15.0,
            variacao_percentual_referencia=20.0,
            variacao_sentido_referencia="baixo",
            somente_homologados=False,
        )
        r = await market_search_intelligent(payload)
        lo, hi = r["filtros"]["faixa_regional_min"], r["filtros"]["faixa_regional_max"]
        self.assertAlmostEqual(lo, 12.0)
        self.assertAlmostEqual(hi, 15.0)
        self.assertEqual(r["filtros"]["variacao_sentido_referencia"], "baixo")
        for it in r.get("itens") or []:
            p = _row_price_for_faixa(it)
            self.assertTrue(
                _preco_dentro_faixa(it, lo, hi, sentido="baixo"),
                f"R$ {p} fora de [{lo}, {hi}] com sentido baixo",
            )

    def test_bulk_recall_pool_respeita_sentido_cima(self):
        from app.service import _build_bulk_manual_recall_pool

        base = 100.0
        lo, hi = compute_faixa_regional(base, 20.0, sentido="cima")
        itens = [
            {
                "valor_unitario": 90.0,
                "valor_unitario_estimado": 115.0,
                "descricao_item": "abaixo base mas estimado na faixa",
                "search_tier": "strict",
            },
            {
                "valor_unitario": 110.0,
                "descricao_item": "dentro faixa cima",
                "search_tier": "strict",
            },
        ]
        pool, funil = _build_bulk_manual_recall_pool(
            itens,
            termo_busca="teste",
            termo_busca_raw="teste",
            faixa_min=lo,
            faixa_max=hi,
            faixa_sentido="cima",
            min_ok=70,
        )
        self.assertEqual(funil["eliminados_faixa_preco_recall"], 1)
        self.assertEqual(len(pool), 1)
        self.assertAlmostEqual(_row_price_for_faixa(pool[0]), 110.0)

    def test_filter_rows_in_faixa_pos_enrich_cima(self):
        base = 19.16
        lo, hi = compute_faixa_regional(base, 20.0, sentido="cima")
        rows = [
            {
                "valor_unitario_homologado": 17.59,
                "valor_unitario": 17.59,
                "descricao_item": "homolog abaixo base",
            },
            {
                "valor_unitario_homologado": 20.50,
                "valor_unitario": 20.50,
                "descricao_item": "dentro faixa",
            },
        ]
        out = _filter_rows_in_faixa(rows, lo, hi, sentido="cima")
        self.assertEqual(len(out), 1)
        self.assertAlmostEqual(_row_price_for_faixa(out[0]), 20.50)

    async def test_faixa_estreita_nao_relaxa(self):
        payload = MarketSearchRequest(
            termo_busca="ALCOOL ETILICO 70",
            max_paginas=10,
            tamanho_pagina=50,
            valor_base_referencia=15.0,
            variacao_percentual_referencia=1.0,
            variacao_sentido_referencia="ambos",
            somente_homologados=False,
        )
        r = await market_search_intelligent(payload)
        lo, hi = r["filtros"]["faixa_regional_min"], r["filtros"]["faixa_regional_max"]
        for it in r.get("itens") or []:
            p = _row_price_for_faixa(it)
            self.assertTrue(lo <= p <= hi, f"R$ {p} fora de [{lo}, {hi}]")


if __name__ == "__main__":
    unittest.main()
