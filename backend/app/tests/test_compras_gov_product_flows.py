"""Fluxos Django: save/fonte/relatório com plataforma compras_gov (sucesso + falhas)."""
from __future__ import annotations

from types import SimpleNamespace

from django.test import SimpleTestCase

from backend.app.pncp_cotacao_api import (
    _compact_item_source,
    _ensure_plataforma_in_payload,
    _fonte_bucket_from_source,
    _resolve_fonte_bucket,
)
from backend.app.services.pncp_relatorio_itens import (
    _label_fonte_plataforma,
    fonte_dict_de_item,
)
from backend.app.services.pncp_relatorio_pdf import _obter_fonte, _obter_modalidade


class ComprasGovProductFlowTests(SimpleTestCase):
    def test_save_payload_keeps_compras_gov_plataforma(self):
        row = {
            "plataforma": "compras_gov",
            "plataforma_item_id": "cg:1:2",
            "descricao_item": "Papel",
            "inciso_classificacao": "inciso_i",
            "esfera_administrativa": "federal",
            "fonte": "governamentais",
            "cnpj_fornecedor": "12345678000199",
            "valor_unitario": 10.0,
        }
        _ensure_plataforma_in_payload(row)
        self.assertEqual(row["plataforma"], "compras_gov")
        compact = _compact_item_source(row)
        self.assertEqual(compact.get("plataforma"), "compras_gov")
        self.assertEqual(_fonte_bucket_from_source(compact), "governamentais")

    def test_fonte_bucket_compras_gov_aliases(self):
        for plat in ("compras_gov", "compras-gov", "comprasgov"):
            self.assertEqual(
                _fonte_bucket_from_source({"plataforma": plat}),
                "governamentais",
                msg=plat,
            )

    def test_fonte_bucket_does_not_confuse_compras_gov_with_tce(self):
        self.assertEqual(_fonte_bucket_from_source({"plataforma": "compras_gov"}), "governamentais")
        self.assertEqual(_fonte_bucket_from_source({"plataforma": "tce_rs"}), "entesPublicos")

    def test_resolve_fonte_without_plataforma_falls_back_pncp_numero(self):
        # Sem plataforma: número PNCP → governamentais (legado).
        self.assertEqual(_resolve_fonte_bucket({}, "123-1/2024"), "governamentais")
        # Sem plataforma e sem número → None (falha de classificação).
        self.assertIsNone(_resolve_fonte_bucket({}, None))

    def test_relatorio_label_and_pdf_fonte(self):
        self.assertEqual(
            _label_fonte_plataforma({"plataforma": "compras_gov"}),
            "Compras.gov",
        )
        self.assertEqual(_obter_fonte("Compras.gov"), "Compras.gov")
        self.assertEqual(_obter_fonte("compras_gov"), "Compras.gov")
        self.assertEqual(_obter_fonte("ComprasGov"), "Compras.gov")
        self.assertEqual(_obter_modalidade("Compras.gov"), "Pregão")

    def test_fonte_dict_flow_end_to_end(self):
        it = SimpleNamespace(
            descricao_item="ITEM MANUAL",
            modalidade="Pregão Eletrônico",
            orgao="MINISTERIO",
            municipio="Brasília",
            uf="DF",
            quantidade=5.0,
            numero_pncp="",
            created_at=None,
            source={
                "plataforma": "compras_gov",
                "descricao": "ITEM COMPRAS.GOV",
                "fornecedor": "FORN CG",
                "cnpj_fornecedor": "12345678000190",
                "url_origem": "https://compras.gov.br/x",
            },
        )
        row = fonte_dict_de_item(it, tz=None)
        self.assertEqual(row["tipo"], "Compras.gov")
        self.assertEqual(row["descricao_fonte"], "ITEM COMPRAS.GOV")

    def test_empty_source_plataforma_does_not_force_compras_gov(self):
        self.assertIsNone(_fonte_bucket_from_source({}))
        self.assertEqual(
            _label_fonte_plataforma({"plataforma": "pncp"}),
            "PNCP",
        )
