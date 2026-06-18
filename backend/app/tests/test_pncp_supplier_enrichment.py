"""Testes unitários do enriquecimento de fornecedor (sem HTTP)."""
from __future__ import annotations

import unittest

from backend.app.services.pncp_relatorio_itens import (
    _fonte_pncp_em_andamento_sem_fornecedor,
    _fornecedor_exibicao_relatorio,
    _pick_supplier_email_from_source,
    _pick_supplier_name_from_source,
    _pick_supplier_telefone_from_source,
    nome_fornecedor_e_util_para_exibicao,
    preco_unitario_cotacao_fonte,
)
from backend.app.services.pncp_supplier_enrichment import (
    _ano_seq_for_enrichment,
    _enrich_payload_sort_key,
    _homolog_pricing_from_resultados,
    _merge_homologated_pricing_into_payload,
    _needs_brasilapi_enrichment,
    _parse_ano_seq_from_numero_pncp,
    _pncp_compra_keys_present,
    _should_attempt_pncp_supplier_lookup,
    flatten_supplier_fields_in_payload,
    fornecedor_tem_cnpj_para_cotacao,
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

    def test_needs_brasilapi_false_quando_contato_completo(self):
        it = {
            "cnpj_fornecedor": "27.105.456/0001-72",
            "fornecedor": "EMPRESA TESTE LTDA",
            "telefone": "(11) 3333-4444",
            "email": "contato@empresa.com.br",
            "fornecedor_contato_fonte": "brasilapi_cnpj",
        }
        self.assertFalse(_needs_brasilapi_enrichment(it))

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

    def test_flatten_promove_contato_de_source_aninhado(self):
        it = {
            "numero_pncp": "12345678000195-1-2023-7",
            "cnpj_fornecedor": "27.105.456/0001-72",
            "fornecedor": "EMPRESA TESTE LTDA",
            "source": {
                "fornecedor_cadastro": {
                    "telefone": "(11) 3333-4444",
                    "email": "contato@empresa.com.br",
                },
            },
        }
        flatten_supplier_fields_in_payload(it)
        self.assertEqual(it.get("telefone"), "(11) 3333-4444")
        self.assertEqual(it.get("email"), "contato@empresa.com.br")
        self.assertEqual(it["fornecedor_cadastro"]["email"], "contato@empresa.com.br")

    def test_pick_email_from_nested_source(self):
        src = {
            "cnpj_fornecedor": "27.105.456/0001-72",
            "source": {
                "email": "aninhado@empresa.com.br",
            },
        }
        self.assertEqual(_pick_supplier_email_from_source(src), "aninhado@empresa.com.br")
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


class FonteEmAndamentoRelatorioTests(unittest.TestCase):
    def test_detecta_compra_em_andamento_sem_fornecedor(self):
        src = {
            "numero_pncp": "02267698000131-1-000026/2025",
            "temResultado": False,
            "situacaoCompraItemNome": "Em andamento",
            "valor_unitario": 9.97,
        }
        self.assertTrue(_fonte_pncp_em_andamento_sem_fornecedor(src))
        self.assertEqual(
            _fornecedor_exibicao_relatorio(src, fornecedor="", cnpj_fornecedor=""),
            "Sem fornecedor homologado (compra em andamento)",
        )

    def test_nao_marca_em_andamento_quando_tem_fornecedor(self):
        src = {
            "cnpj_fornecedor": "27.105.456/0001-72",
            "fornecedor": "EMPRESA TESTE LTDA",
            "temResultado": True,
        }
        self.assertFalse(_fonte_pncp_em_andamento_sem_fornecedor(src))

    def test_homologado_sem_snapshot_nao_e_em_andamento(self):
        src = {
            "numero_pncp": "12345678000195-1-2023-7",
            "temResultado": True,
            "valor_unitario_homologado": 12.5,
            "situacao_compra": "Em andamento",
        }
        self.assertFalse(_fonte_pncp_em_andamento_sem_fornecedor(src))
        self.assertEqual(
            _fornecedor_exibicao_relatorio(src, fornecedor="", cnpj_fornecedor=""),
            "Não informado",
        )

    def test_exige_cnpj_para_gravar_cotacao(self):
        self.assertFalse(fornecedor_tem_cnpj_para_cotacao({"fornecedor": "Só nome LTDA"}))
        self.assertTrue(
            fornecedor_tem_cnpj_para_cotacao(
                {"cnpj_fornecedor": "27.105.456/0001-72", "fornecedor": "EMPRESA TESTE LTDA"}
            )
        )


class HomologPricingTests(unittest.TestCase):
    def test_homolog_pricing_from_resultados_item(self):
        data = {
            "numeroItem": 3,
            "valorUnitarioHomologado": 8.79,
            "valorTotalHomologado": 879.0,
            "quantidadeHomologada": 100,
        }
        out = _homolog_pricing_from_resultados(data, numero_item="3")
        self.assertAlmostEqual(out["valor_unitario_homologado"], 8.79)
        self.assertAlmostEqual(out["valor_total_homologado"], 879.0)
        self.assertAlmostEqual(out["quantidade_homologada"], 100)

    def test_merge_homologated_pricing_overwrites_estimado(self):
        it = {
            "valor_unitario": 17.27,
            "valor_total": 1727.0,
            "quantidade": 100,
            "source": {"valor_unitario_estimado": 17.27},
        }
        snap = {"valor_unitario_homologado": 8.79, "valor_total_homologado": 879.0}
        self.assertTrue(_merge_homologated_pricing_into_payload(it, snap))
        self.assertAlmostEqual(it["valor_unitario"], 8.79)
        self.assertAlmostEqual(it["valor_total"], 879.0)
        self.assertAlmostEqual(it["source"]["valor_unitario_homologado"], 8.79)

    def test_preco_unitario_cotacao_fonte_prioriza_homologado(self):
        row = {
            "valor_unitario": 17.27,
            "source": {"valor_unitario_homologado": 8.79},
        }
        self.assertAlmostEqual(preco_unitario_cotacao_fonte(row, quantidade_item=100), 8.79)


if __name__ == "__main__":
    unittest.main()
