"""Testes de faixa regional (valor base + variação + sentido)."""

import asyncio
import unittest

from app.pricing_faixa import compute_faixa_regional, normalize_variacao_sentido
from app.schemas import MarketSearchRequest
from app.service import _build_manual_parity_top3, _preco_dentro_faixa, _row_price_for_faixa, market_search_intelligent


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
            self.assertTrue(_preco_dentro_faixa(it, lo, hi), f"R$ {p} fora de [{lo}, {hi}]")

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
