"""Testes unitários do enriquecimento de fornecedor (sem HTTP)."""
from __future__ import annotations

import unittest

from backend.app.services.pncp_supplier_enrichment import (
    _ano_seq_for_enrichment,
    _enrich_payload_sort_key,
    _parse_ano_seq_from_numero_pncp,
)


class ParseNumeroPncpTests(unittest.TestCase):
    def test_parse_ano_seq_controle_padrao(self):
        ano, seq = _parse_ano_seq_from_numero_pncp("00000000000191-1-2024-42")
        self.assertEqual(ano, 2024)
        self.assertEqual(seq, 42)

    def test_parse_invalido(self):
        self.assertEqual(_parse_ano_seq_from_numero_pncp(""), (None, None))
        self.assertEqual(_parse_ano_seq_from_numero_pncp("apenas-texto"), (None, None))

    def test_ano_seq_fallback_source_e_numero(self):
        ano, seq = _ano_seq_for_enrichment(
            numero_pncp="12345678000195-1-2023-7",
            ano_compra=None,
            sequencial_compra=None,
            source={},
        )
        self.assertEqual((ano, seq), (2023, 7))

    def test_ano_seq_prioriza_colunas(self):
        ano, seq = _ano_seq_for_enrichment(
            numero_pncp="12345678000195-1-2099-99",
            ano_compra=2020,
            sequencial_compra=5,
            source={"ano_compra": 2021},
        )
        self.assertEqual((ano, seq), (2020, 5))


class EnrichSortKeyTests(unittest.TestCase):
    def test_homolog_com_resultado_primeiro(self):
        a = {"temResultado": True, "situacaoCompraItemNome": "Homologado", "numero_item": "2"}
        b = {"temResultado": False, "situacao": "Em andamento", "numero_item": "1"}
        self.assertLess(_enrich_payload_sort_key(a), _enrich_payload_sort_key(b))


if __name__ == "__main__":
    unittest.main()
