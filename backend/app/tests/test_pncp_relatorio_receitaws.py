"""Fallback ReceitaWS de e-mail quando BrasilAPI omite (relatório + PDF)."""
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.app.services.pncp_relatorio_itens import (
    EMAIL_INDISPONIVEL_RF,
    _completar_email_receitaws_pdf,
    fonte_dict_de_item,
)
from backend.app.services.pncp_supplier_enrichment import fetch_receitaws_email_por_cnpj


class ReceitawsPdfEmailTests(SimpleTestCase):
    def test_fetch_receitaws_email_ok(self):
        with patch(
            "backend.app.services.pncp_supplier_enrichment._get_json",
            return_value={"status": "OK", "email": "bl-distribuidora@hotmail.com"},
        ):
            self.assertEqual(
                fetch_receitaws_email_por_cnpj("51.420.204/0001-12"),
                "bl-distribuidora@hotmail.com",
            )

    def test_fetch_receitaws_cristalia_filial(self):
        with patch(
            "backend.app.services.pncp_supplier_enrichment._get_json",
            return_value={"status": "OK", "email": "viviane.barreto@cristalia.com.br"},
        ):
            self.assertEqual(
                fetch_receitaws_email_por_cnpj("44.734.671/0022-86"),
                "viviane.barreto@cristalia.com.br",
            )

    def test_fetch_receitaws_email_error_status(self):
        with patch(
            "backend.app.services.pncp_supplier_enrichment._get_json",
            return_value={"status": "ERROR", "message": "rate limit"},
        ):
            self.assertEqual(fetch_receitaws_email_por_cnpj("51420204000112"), "")

    def test_completar_email_respeita_cache_e_limite(self):
        state = {"cache": {}, "fetches": 0, "max_lookups": 1}
        with patch(
            "backend.app.services.pncp_relatorio_itens.fetch_receitaws_email_por_cnpj",
            return_value="a@b.com",
        ) as mock_fetch:
            em1 = _completar_email_receitaws_pdf(
                cnpj_fornecedor="51.420.204/0001-12",
                email="",
                state=state,
            )
            em2 = _completar_email_receitaws_pdf(
                cnpj_fornecedor="51.420.204/0001-12",
                email="",
                state=state,
            )
            em3 = _completar_email_receitaws_pdf(
                cnpj_fornecedor="11.222.333/0001-81",
                email="",
                state=state,
            )
        self.assertEqual(em1, "a@b.com")
        self.assertEqual(em2, "a@b.com")
        self.assertEqual(em3, "")
        mock_fetch.assert_called_once()

    def test_fonte_dict_usa_receitaws_quando_brasilapi_sem_email(self):
        class _It:
            modalidade = "PNCP"
            municipio = "Penedo"
            uf = "AL"
            orgao = "Teste"
            numero_pncp = "123"
            quantidade = 1
            created_at = None
            source = {
                "cnpj_fornecedor": "51.420.204/0001-12",
                "fornecedor": "BL DISTRIBUIDORA LTDA",
                "fornecedor_cadastro": {"telefone": "8287120102"},
            }

        state = {"cache": {}, "fetches": 0, "max_lookups": 8}
        with patch(
            "backend.app.services.pncp_relatorio_itens.fetch_receitaws_email_por_cnpj",
            return_value="bl-distribuidora@hotmail.com",
        ):
            row = fonte_dict_de_item(_It(), tz=None, receitaws_pdf_state=state)
        self.assertEqual(row["email"], "bl-distribuidora@hotmail.com")
        self.assertNotEqual(row["email"], EMAIL_INDISPONIVEL_RF)

    def test_fonte_dict_sem_state_nao_chama_receitaws(self):
        class _It:
            modalidade = "PNCP"
            municipio = "Penedo"
            uf = "AL"
            orgao = "Teste"
            numero_pncp = "123"
            quantidade = 1
            created_at = None
            source = {"cnpj_fornecedor": "51.420.204/0001-12", "fornecedor": "BL"}

        with patch(
            "backend.app.services.pncp_relatorio_itens.fetch_receitaws_email_por_cnpj",
        ) as mock_fetch:
            row = fonte_dict_de_item(_It(), tz=None)
        self.assertEqual(row["email"], EMAIL_INDISPONIVEL_RF)
        mock_fetch.assert_not_called()
