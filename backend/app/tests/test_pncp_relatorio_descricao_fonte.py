"""Descrição PNCP por fonte no relatório (≠ nome do item manual da cotação)."""
from __future__ import annotations

from types import SimpleNamespace

from django.test import SimpleTestCase

from backend.app.services.pncp_relatorio_itens import fonte_dict_de_item


class RelatorioDescricaoFonteTests(SimpleTestCase):
    def test_fonte_dict_usa_descricao_pncp_do_source_nao_item_manual(self):
        it = SimpleNamespace(
            descricao_item="ACETATO DE MEDROXIPROGESTERONA SUSPENSÃO INJETÁVEL 50MG/ML",
            modalidade="Pregão Eletrônico",
            orgao="FUNDO MUNICIPAL DE SAUDE",
            municipio="Silvânia",
            uf="GO",
            quantidade=100.0,
            numero_pncp="12345678000100-1-000001/2024",
            created_at=None,
            source={
                "descricao": "ACETATO DE MEDROXIPROGESTERONA 150MG/ML AMPOLA 1ML",
                "fornecedor": "LAB XYZ LTDA",
                "cnpj_fornecedor": "27105456000172",
            },
        )
        row = fonte_dict_de_item(it, tz=None)
        self.assertEqual(
            row["descricao_fonte"],
            "ACETATO DE MEDROXIPROGESTERONA 150MG/ML AMPOLA 1ML",
        )
        self.assertNotEqual(row["descricao_fonte"], it.descricao_item)
        self.assertEqual(row["tipo"], "PNCP")

    def test_fonte_dict_tce_rs_label_curto(self):
        it = SimpleNamespace(
            descricao_item="PAPEL A4",
            modalidade="TCE-RS · LicitaCon · proc. tce_rs:85300:2025:14:PCE,Pregão - Eletrônico",
            orgao="PREFEITURA",
            municipio="Porto Alegre",
            uf="RS",
            quantidade=10.0,
            numero_pncp="",
            created_at=None,
            source={
                "plataforma": "tce_rs",
                "descricao": "PAPEL A4 75G",
                "fornecedor": "FORN LTDA",
                "cnpj_fornecedor": "12345678000190",
            },
        )
        row = fonte_dict_de_item(it, tz=None)
        self.assertEqual(row["tipo"], "TCE-RS")
        self.assertEqual(row["modalidade"], "Pregão Eletrônico")

    def test_fonte_dict_compras_gov_label_curto(self):
        it = SimpleNamespace(
            descricao_item="PAPEL A4",
            modalidade="Pregão Eletrônico",
            orgao="MINISTERIO",
            municipio="Brasília",
            uf="DF",
            quantidade=10.0,
            numero_pncp="",
            created_at=None,
            source={
                "plataforma": "compras_gov",
                "descricao": "PAPEL A4 75G",
                "fornecedor": "FORN LTDA",
                "cnpj_fornecedor": "12345678000190",
                "modalidade": "Pregão Eletrônico",
            },
        )
        row = fonte_dict_de_item(it, tz=None)
        self.assertEqual(row["tipo"], "Compras.gov")

    def test_fonte_dict_tce_rs_modalidade_via_processo_id(self):
        it = SimpleNamespace(
            descricao_item="PAPEL A4",
            modalidade="",
            orgao="PREFEITURA",
            municipio="Porto Alegre",
            uf="RS",
            quantidade=10.0,
            numero_pncp="",
            created_at=None,
            source={
                "plataforma": "tce_rs",
                "processo_id": "tce_rs:85300:2025:14:PCP",
                "descricao": "PAPEL A4 75G",
                "fornecedor": "FORN LTDA",
                "cnpj_fornecedor": "12345678000190",
            },
        )
        row = fonte_dict_de_item(it, tz=None)
        self.assertEqual(row["tipo"], "TCE-RS")
        self.assertEqual(row["modalidade"], "Pregão Presencial")

    def test_fonte_dict_tce_rs_link_licitacon(self):
        url = (
            "https://portal.tce.rs.gov.br/aplicprod/f?p=50500:10:::NO:10:"
            "P10_ID_LICITACAO,P10_PAG_RETORNO,F50500_CD_ORGAO:1517985,14,64801&cs=abc"
        )
        it = SimpleNamespace(
            descricao_item="PAPEL A4",
            modalidade="",
            orgao="PREFEITURA",
            municipio="Porto Alegre",
            uf="RS",
            quantidade=10.0,
            numero_pncp="",
            ano_compra=None,
            sequencial_compra=None,
            created_at=None,
            source={
                "plataforma": "tce_rs",
                "processo_id": "tce_rs:64801:2026:5:PRD",
                "descricao": "PAPEL A4 75G",
                "fornecedor": "FORN LTDA",
                "cnpj_fornecedor": "12345678000190",
                "source": {"url_origem": url},
            },
        )
        row = fonte_dict_de_item(it, tz=None)
        self.assertEqual(row["tipo"], "TCE-RS")
        self.assertEqual(row["link_pncp"], url)

    def test_fonte_dict_fallback_objeto_resumido(self):
        it = SimpleNamespace(
            descricao_item="Item manual usuário",
            modalidade="",
            orgao="",
            municipio="",
            uf="",
            quantidade=None,
            numero_pncp="",
            created_at=None,
            source={"objeto_resumido": "Título PNCP via objeto resumido"},
        )
        row = fonte_dict_de_item(it, tz=None)
        self.assertEqual(row["descricao_fonte"], "Título PNCP via objeto resumido")
