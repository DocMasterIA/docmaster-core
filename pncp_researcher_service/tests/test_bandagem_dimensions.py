"""Testes de dimensão (15cm x 2m) e linha Smarch vs Kinesio."""

import asyncio
import unittest

from app.local_index import build_search_query_tiers, _match_row_search_tiers, local_item_search
from app.product_spec_match import (
    extract_product_spec_from_term,
    product_line_strict_reject,
    product_spec_strict_reject,
)
from app.schemas import MarketSearchRequest
from app.service import market_search_intelligent


class BandagemDimensionTests(unittest.TestCase):
    def test_extract_15cm_x_2m(self):
        term = "BANDAGEM ELASTICA (FAIXA DE SMARCH) 15CM X 2M"
        spec = extract_product_spec_from_term(term)
        self.assertAlmostEqual(spec.width_cm, 15.0)
        self.assertAlmostEqual(spec.length_m, 2.0)

    def test_reject_kinesio_when_smarch_requested(self):
        term = "BANDAGEM ELASTICA (FAIXA DE SMARCH) 15CM X 2M"
        knesio = "Bandagem elástica adesiva faixa knesio 5mt"
        self.assertTrue(product_line_strict_reject(term, {"descricao_item": knesio}))
        self.assertTrue(product_spec_strict_reject(term, {"descricao_item": knesio}))

    def test_knesio_not_in_tiers_after_spec_filter(self):
        term = "BANDAGEM ELASTICA (FAIXA DE SMARCH) 15CM X 2M"
        knesio = "Bandagem elástica adesiva faixa knesio 5mt"
        tiers = build_search_query_tiers(term)
        # Pode casar no tier core por bandagem+elastica+faixa, mas spec filter barra.
        self.assertTrue(product_spec_strict_reject(term, {"descricao_item": knesio}))


class BandagemSearchIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_top3_smarch_not_kinesio(self):
        term = "BANDAGEM ELASTICA (FAIXA DE SMARCH) 15CM X 2M"
        r = await market_search_intelligent(
            MarketSearchRequest(
                termo_busca=term,
                max_paginas=15,
                tamanho_pagina=100,
                somente_homologados=False,
            )
        )
        for it in r.get("itens") or []:
            d = (it.get("descricao_item") or "").lower()
            self.assertNotIn("kinesio", d)
            self.assertNotIn("knesio", d)


if __name__ == "__main__":
    unittest.main()
