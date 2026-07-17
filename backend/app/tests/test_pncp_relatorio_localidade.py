from django.test import SimpleTestCase

from backend.app.services.pncp_relatorio_itens import (
    _format_orgao_com_local,
    _resolve_municipio_uf_para_fonte,
)
from backend.app.services.pncp_source_normalize import normalize_pncp_geo_in_payload


class RelatorioLocalidadeTests(SimpleTestCase):
    def test_normalize_unidade_orgao_to_top(self):
        payload = {
            "orgao": "Fundo Municipal",
            "unidadeOrgao": {"municipioNome": "Silvânia", "ufSigla": "GO"},
        }
        self.assertTrue(normalize_pncp_geo_in_payload(payload))
        self.assertEqual(payload["municipio"], "Silvânia")
        self.assertEqual(payload["uf"], "GO")

    def test_resolve_from_source_nested(self):
        src = {
            "unidadeOrgao": {"municipioNome": "Porto Alegre", "ufSigla": "RS"},
        }
        mun, uf = _resolve_municipio_uf_para_fonte("", "", src)
        self.assertEqual(mun, "Porto Alegre")
        self.assertEqual(uf, "RS")

    def test_format_orgao_com_local(self):
        out = _format_orgao_com_local(
            "FUNDO MUNICIPAL DE SAUDE DE SILVANIA",
            "Silvânia",
            "GO",
        )
        self.assertEqual(out, "Silvânia/GO - FUNDO MUNICIPAL DE SAUDE DE SILVANIA")

    def test_tce_ignora_ibge_fornecedor_e_infere_cidade_do_orgao(self):
        mun, uf = _resolve_municipio_uf_para_fonte(
            "4314902",
            "RS",
            {"plataforma": "tce_rs", "orgao": "PM DE TIO HUGO"},
            orgao="PM DE TIO HUGO",
        )
        self.assertEqual(mun, "Tio Hugo")
        self.assertEqual(uf, "RS")
        out = _format_orgao_com_local("PM DE TIO HUGO", mun, uf)
        self.assertEqual(out, "Tio Hugo/RS - PM DE TIO HUGO")
