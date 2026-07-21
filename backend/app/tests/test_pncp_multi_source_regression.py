"""Regressão Django: plataforma multi-fonte não quebra buckets Art. 5º, source compact nem geo."""
from __future__ import annotations

from django.test import SimpleTestCase

from backend.app.pncp_cotacao_api import (
    _compact_item_source,
    _ensure_plataforma_in_payload,
    _fonte_bucket_from_source,
    _resolve_fonte_bucket,
)
from backend.app.services.pncp_source_normalize import normalize_pncp_geo_in_payload


class PlataformaPayloadRegressionTests(SimpleTestCase):
    def test_ensure_plataforma_default_pncp(self):
        row = {"numero_pncp": "123-1/2024", "descricao_item": "Item"}
        _ensure_plataforma_in_payload(row)
        self.assertEqual(row["plataforma"], "pncp")

    def test_ensure_plataforma_respects_custom_value(self):
        row = {"plataforma": "compras_gov", "descricao_item": "Item"}
        _ensure_plataforma_in_payload(row)
        self.assertEqual(row["plataforma"], "compras_gov")

    def test_compact_source_adds_plataforma_without_dropping_pncp_fields(self):
        payload = {
            "numero_pncp": "12345678000195-1-000001/2024",
            "descricao_item": "Papel A4",
            "valor_unitario_homologado": 25.5,
            "cnpj_fornecedor": "12345678000199",
            "score_aprovacao": 91.0,
            "inciso_classificacao": "inciso_i",
            "esfera_id": "f",
            "similaridade_encontrada": True,
        }
        out = _compact_item_source(payload)
        self.assertEqual(out.get("plataforma"), "pncp")
        self.assertEqual(out.get("numero_pncp"), payload["numero_pncp"])
        self.assertEqual(out.get("score_aprovacao"), 91.0)
        self.assertEqual(out.get("similaridade_encontrada"), True)

    def test_fonte_bucket_unchanged_with_plataforma_field(self):
        src = {
            "plataforma": "pncp",
            "inciso_classificacao": "inciso_i",
            "esfera_id": "f",
        }
        self.assertEqual(_fonte_bucket_from_source(src), "governamentais")
        self.assertEqual(_resolve_fonte_bucket(src, "123-1/2024"), "governamentais")

    def test_fonte_bucket_estadual_with_plataforma(self):
        src = {
            "plataforma": "pncp",
            "esfera_administrativa": "estadual",
        }
        self.assertEqual(_fonte_bucket_from_source(src), "entesPublicos")

    def test_fonte_bucket_tce_rs_is_entes_publicos(self):
        src = {"plataforma": "tce_rs"}
        self.assertEqual(_fonte_bucket_from_source(src), "entesPublicos")
        self.assertEqual(_resolve_fonte_bucket(src, None), "entesPublicos")

    def test_fonte_bucket_compras_gov_is_governamentais(self):
        src = {"plataforma": "compras_gov"}
        self.assertEqual(_fonte_bucket_from_source(src), "governamentais")
        self.assertEqual(_resolve_fonte_bucket(src, None), "governamentais")

    def test_geo_normalize_still_works_after_plataforma(self):
        payload = {
            "plataforma": "pncp",
            "orgao": "Secretaria",
            "unidadeOrgao": {"municipioNome": "Curitiba", "ufSigla": "PR"},
        }
        self.assertTrue(normalize_pncp_geo_in_payload(payload))
        self.assertEqual(payload["municipio"], "Curitiba")
        self.assertEqual(payload["uf"], "PR")
        self.assertEqual(payload["plataforma"], "pncp")
