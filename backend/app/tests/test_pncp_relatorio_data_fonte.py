"""Data da fonte no PDF: data_publicacao, não created_at do save."""
from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from types import SimpleNamespace

from django.test import SimpleTestCase
from django.utils import timezone

from backend.app.services.pncp_relatorio_itens import (
    _format_data_fonte_relatorio,
    fonte_dict_de_item,
)


class RelatorioDataFonteTests(SimpleTestCase):
    def test_format_prefer_data_publicacao_iso(self):
        it = SimpleNamespace(
            data_publicacao="2025-02-10",
            created_at=timezone.now(),
        )
        self.assertEqual(
            _format_data_fonte_relatorio(it, {}, tz=timezone.get_current_timezone()),
            "10/02/2025",
        )

    def test_format_fallback_created_at_quando_sem_publicacao(self):
        created = datetime(2026, 8, 6, 15, 30, tzinfo=dt_timezone.utc)
        it = SimpleNamespace(data_publicacao="", created_at=created)
        out = _format_data_fonte_relatorio(
            it, {}, tz=timezone.get_current_timezone()
        )
        self.assertRegex(out, r"^\d{2}/\d{2}/2026$")

    def test_fonte_dict_nao_usa_created_at_se_tem_publicacao(self):
        created = datetime(2026, 8, 6, 15, 30, tzinfo=dt_timezone.utc)
        it = SimpleNamespace(
            descricao_item="ITEM",
            modalidade="Pregão Eletrônico",
            orgao="ORGAO",
            municipio="Cidade",
            uf="RS",
            quantidade=1.0,
            numero_pncp="",
            data_publicacao="2025-02-10",
            created_at=created,
            valor_unitario=10.0,
            source={
                "descricao": "ITEM PNCP",
                "fornecedor": "FORN LTDA",
                "cnpj_fornecedor": "12345678000190",
            },
        )
        row = fonte_dict_de_item(it, tz=timezone.get_current_timezone())
        self.assertEqual(row["data"], "10/02/2025")
