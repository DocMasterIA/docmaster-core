"""E-mail externo por CNPJ (cnpj.ws / ReceitaWS + cache persistente)."""
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.app.services.pncp_relatorio_itens import (
    EMAIL_INDISPONIVEL_RF,
    _completar_email_receitaws_pdf,
    fonte_dict_de_item,
)
from backend.app.services.pncp_supplier_enrichment import fetch_cnpj_email_externo


class CnpjEmailExternoTests(SimpleTestCase):
    def test_fetch_cnpj_ws_ok(self):
        with patch(
            "backend.app.services.pncp_supplier_enrichment._fetch_cnpj_ws_email_http",
            return_value=("viviane.barreto@cristalia.com.br", False),
        ):
            self.assertEqual(
                fetch_cnpj_email_externo("44.734.671/0022-86"),
                "viviane.barreto@cristalia.com.br",
            )

    def test_fetch_receitaws_error_status(self):
        with patch(
            "backend.app.services.pncp_supplier_enrichment._fetch_cnpj_ws_email_http",
            return_value=("", False),
        ), patch(
            "backend.app.services.pncp_supplier_enrichment._fetch_receitaws_email_http",
            return_value=("", True),
        ):
            self.assertEqual(fetch_cnpj_email_externo("51420204000112"), "")

    def test_cnpj_ws_rate_limit_falls_back_to_receitaws(self):
        with patch(
            "backend.app.services.pncp_supplier_enrichment.get_cached_cnpj_email",
            return_value="",
        ), patch(
            "backend.app.services.pncp_supplier_enrichment.is_cnpj_email_negative_cached",
            return_value=False,
        ), patch(
            "backend.app.services.pncp_supplier_enrichment.set_cached_cnpj_email",
        ), patch(
            "backend.app.services.pncp_supplier_enrichment._fetch_cnpj_ws_email_http",
            return_value=("", True),
        ), patch(
            "backend.app.services.pncp_supplier_enrichment._fetch_receitaws_email_http",
            return_value=("contato@empresa.com.br", False),
        ) as mock_rw:
            em = fetch_cnpj_email_externo("51420204000112")
        self.assertEqual(em, "contato@empresa.com.br")
        mock_rw.assert_called_once()

    def test_cnpj_ws_rate_limit_does_not_block_next_cnpj(self):
        state = {"cache": {}, "http_fetches": 0, "max_http_fetches": 8, "rate_limited": False}
        calls = {"ws": 0, "rw": 0}

        def _ws(_cnpj):
            calls["ws"] += 1
            return ("", True)

        def _rw(cnpj):
            calls["rw"] += 1
            return ("b@b.com", False) if cnpj == "51420204000112" else ("c@c.com", False)

        with patch(
            "backend.app.services.pncp_supplier_enrichment._fetch_cnpj_ws_email_http",
            side_effect=_ws,
        ), patch(
            "backend.app.services.pncp_supplier_enrichment._fetch_receitaws_email_http",
            side_effect=_rw,
        ), patch(
            "backend.app.services.pncp_supplier_enrichment.get_cached_cnpj_email",
            return_value="",
        ), patch(
            "backend.app.services.pncp_supplier_enrichment.is_cnpj_email_negative_cached",
            return_value=False,
        ), patch(
            "backend.app.services.pncp_supplier_enrichment.set_cached_cnpj_email",
        ), patch(
            "backend.app.services.pncp_supplier_enrichment.set_cached_cnpj_sem_email",
        ):
            em1 = fetch_cnpj_email_externo("51420204000112", state=state)
            em2 = fetch_cnpj_email_externo("44734671002286", state=state)
        self.assertEqual(em1, "b@b.com")
        self.assertEqual(em2, "c@c.com")
        # Após 429 no cnpj.ws, demais CNPJs usam só ReceitaWS (evita martelar API bloqueada).
        self.assertEqual(calls["ws"], 1)
        self.assertEqual(calls["rw"], 2)

    def test_completar_email_usa_state(self):
        state = {"cache": {}, "http_fetches": 0, "max_http_fetches": 8, "rate_limited": False}
        with patch(
            "backend.app.services.pncp_relatorio_itens.fetch_cnpj_email_externo",
            return_value="a@b.com",
        ) as mock_fetch:
            em = _completar_email_receitaws_pdf(
                cnpj_fornecedor="51.420.204/0001-12",
                email="",
                state=state,
            )
        self.assertEqual(em, "a@b.com")
        mock_fetch.assert_called_once()

    def test_fonte_dict_usa_email_externo(self):
        class _It:
            modalidade = "PNCP"
            municipio = "Itapira"
            uf = "SP"
            orgao = "Teste"
            numero_pncp = "123"
            quantidade = 1
            created_at = None
            source = {
                "cnpj_fornecedor": "44.734.671/0022-86",
                "fornecedor": "CRISTALIA PRODUTOS QUIMICOS FARMACEUTICOS LTDA",
                "fornecedor_cadastro": {"telefone": "1938639777"},
            }

        state = {"cache": {}, "http_fetches": 0, "max_http_fetches": 8, "rate_limited": False}
        with patch(
            "backend.app.services.pncp_relatorio_itens.fetch_cnpj_email_externo",
            return_value="viviane.barreto@cristalia.com.br",
        ):
            row = fonte_dict_de_item(_It(), tz=None, receitaws_pdf_state=state)
        self.assertEqual(row["email"], "viviane.barreto@cristalia.com.br")
        self.assertNotEqual(row["email"], EMAIL_INDISPONIVEL_RF)
