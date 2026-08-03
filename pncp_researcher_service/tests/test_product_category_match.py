"""Testes de categoria de produto e calibre N° na busca."""

import unittest

from app.local_index import build_search_query_tiers, local_item_search, _match_row_search_tiers
from app.product_category_match import product_category_strict_reject
from app.schemas import MarketSearchRequest
from app.search_text_clean import normalize_for_search
from app.service import market_search_intelligent


class ProductCategoryMatchTests(unittest.TestCase):
    def test_reject_luva_on_fio_query(self):
        glove = (
            "LUVA, de seguranca, antiestatico, cor cinza, tamanho M, "
            "tricotada em fios de nylon ou poliamida"
        )
        term = "FIO NYLON N° 4.0 COR PRETA COM AGULHA 4 CM"
        self.assertTrue(product_category_strict_reject(term, {"descricao_item": glove}))

    def test_allow_fio_sutura(self):
        desc = "FIO DE SUTURA AGULHADO MATERIAL FIO NYLON/POLIAMIDA PRETO"
        term = "FIO NYLON N° 4.0 COR PRETA COM AGULHA 4 CM"
        self.assertFalse(product_category_strict_reject(term, {"descricao_item": desc}))

    def test_calibre_token_preserved(self):
        norm = normalize_for_search("FIO NYLON N° 4.0 COR PRETA")
        self.assertIn("n4p0", norm)


class FioNylonSearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_intelligent_top_not_luva(self):
        term = "FIO NYLON N° 4.0 COR PRETA COM AGULHA 4 CM"
        glove = (
            "LUVA, de seguranca, antiestatico, cor cinza, tamanho M, "
            "tricotada em fios de nylon ou poliamida"
        )
        tiers = build_search_query_tiers(term)
        self.assertIsNone(_match_row_search_tiers(glove, tiers))

        payload = MarketSearchRequest(
            termo_busca=term,
            max_paginas=15,
            tamanho_pagina=100,
            somente_homologados=False,
            busca_lote=False,
        )
        r = await market_search_intelligent(payload)
        for it in r.get("itens") or []:
            d = (it.get("descricao_item") or "").upper()
            self.assertNotIn("LUVA", d[:20], msg=it.get("descricao_item"))

    def test_local_search_finds_fio_nylon(self):
        term = "FIO NYLON N° 4.0 COR PRETA COM AGULHA 4 CM"
        r = local_item_search(term, limit=50, somente_homologados=False)
        self.assertGreater(len(r.get("itens") or []), 0)
        for it in r.get("itens") or []:
            d = (it.get("descricao_item") or "").upper()
            self.assertTrue("FIO" in d or "NYLON" in d)


if __name__ == "__main__":
    unittest.main()
