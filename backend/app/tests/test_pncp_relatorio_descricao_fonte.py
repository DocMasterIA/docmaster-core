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
