"""Testes unitários do enriquecimento de fornecedor (sem HTTP)."""
from __future__ import annotations

import unittest

from backend.app.services.pncp_relatorio_itens import (
    _pick_supplier_email_from_source,
    _pick_supplier_name_from_source,
    _pick_supplier_telefone_from_source,
    nome_fornecedor_e_util_para_exibicao,
)
from backend.app.services.pncp_supplier_enrichment import (
    _ano_seq_for_enrichment,
    _enrich_payload_sort_key,
    _needs_brasilapi_enrichment,
    _parse_ano_seq_from_numero_pncp,
    _pncp_compra_keys_present,
    _should_attempt_pncp_supplier_lookup,
    flatten_supplier_fields_in_payload,
)


class ParseNumeroPncpTests(unittest.TestCase):
    def test_parse_ano_seq_controle_padrao(self):
        ano, seq = _parse_ano_seq_from_numero_pncp("00000000000191-1-2024-42")
        self.assertEqual(ano, 2024)
        self.assertEqual(seq, 42)

    def test_parse_ano_seq_formato_barra(self):
        ano, seq = _parse_ano_seq_from_numero_pncp("87613279000167-1-000085/2025")
        self.assertEqual(ano, 2025)
        self.assertEqual(seq, 85)

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


class SupplierNameDisplayTests(unittest.TestCase):
    def test_rejeita_metadado_pncp_como_nome(self):
        self.assertFalse(nome_fornecedor_e_util_para_exibicao("pncp_resultado_item_item"))
        self.assertTrue(nome_fornecedor_e_util_para_exibicao("FORNECEDORA EXEMPLO LTDA"))

    def test_pick_name_ignora_fornecedor_fonte(self):
        src = {
            "cnpj_fornecedor": "57.836.642/0001-42",
            "fornecedor": "",
            "fornecedor_fonte": "pncp_resultado_item_item",
            "fornecedor_fonte_nome": "pncp_resultado_item_item",
        }
        self.assertEqual(_pick_supplier_name_from_source(src), "")

    def test_pick_name_from_fornecedor_cadastro(self):
        src = {
            "cnpj_fornecedor": "27.105.456/0001-72",
            "fornecedor": "",
            "fornecedor_cadastro": {"razao_social": "EMPRESA TESTE LTDA"},
        }
        self.assertEqual(_pick_supplier_name_from_source(src), "EMPRESA TESTE LTDA")

    def test_pick_contact_from_fornecedor_cadastro(self):
        src = {
            "cnpj_fornecedor": "27.105.456/0001-72",
            "fornecedor": "EMPRESA TESTE LTDA",
            "fornecedor_cadastro": {
                "telefone": "(11) 3333-4444",
                "email": "contato@empresa.com.br",
            },
        }
        self.assertEqual(_pick_supplier_telefone_from_source(src), "(11) 3333-4444")
        self.assertEqual(_pick_supplier_email_from_source(src), "contato@empresa.com.br")

    def test_needs_brasilapi_when_cnpj_nome_sem_contato(self):
        it = {
            "cnpj_fornecedor": "27.105.456/0001-72",
            "fornecedor": "EMPRESA TESTE LTDA",
        }
        self.assertTrue(_needs_brasilapi_enrichment(it))

    def test_needs_brasilapi_false_apos_consulta_rf(self):
        it = {
            "cnpj_fornecedor": "27.105.456/0001-72",
            "fornecedor": "EMPRESA TESTE LTDA",
            "fornecedor_contato_fonte": "brasilapi_cnpj",
            "fornecedor_cadastro": {"telefone": "", "email": ""},
        }
        self.assertFalse(_needs_brasilapi_enrichment(it))

    def test_flatten_supplier_from_nested_source(self):
        it = {
            "numero_pncp": "12345678000195-1-2023-7",
            "source": {
                "cnpj_fornecedor": "27.105.456/0001-72",
                "fornecedor": "EMPRESA ANINHADA LTDA",
            },
        }
        flatten_supplier_fields_in_payload(it)
        self.assertEqual(it["cnpj_fornecedor"], "27.105.456/0001-72")
        self.assertEqual(it["fornecedor"], "EMPRESA ANINHADA LTDA")

    def test_flatten_ignora_metadado_pncp_no_topo(self):
        it = {
            "numero_pncp": "12345678000195-1-2023-7",
            "fornecedor": "pncp_resultado_item_item",
            "source": {
                "cnpj_fornecedor": "27.105.456/0001-72",
                "fornecedor": "EMPRESA REAL LTDA",
            },
        }
        flatten_supplier_fields_in_payload(it)
        self.assertEqual(it["fornecedor"], "EMPRESA REAL LTDA")

    def test_should_lookup_nao_homologado_com_chaves_pncp(self):
        it = {
            "numero_pncp": "12345678000195-1-2023-7",
            "ano_compra": 2023,
            "sequencial_compra": 7,
            "situacao": "Em andamento",
        }
        self.assertTrue(_pncp_compra_keys_present(it))
        self.assertTrue(_should_attempt_pncp_supplier_lookup(it, only_homolog=True))

    def test_should_skip_nao_homologado_sem_chaves_pncp(self):
        it = {"situacao": "Em andamento", "descricao_item": "Caneta"}
        self.assertFalse(_should_attempt_pncp_supplier_lookup(it, only_homolog=True))


if __name__ == "__main__":
    unittest.main()
