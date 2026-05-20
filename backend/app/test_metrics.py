from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase

from app.api import _record_llm_usage_from_response
from app.metrics import (
    docmaster_llm_invocations_total,
    docmaster_llm_tokens_total,
    normalize_auth_login_result,
    normalize_package_key,
    package_to_tipo_geracao,
    prefeitura_label,
    prefeitura_label_from_instance,
    record_llm_token_usage,
    set_request_metrics,
    tenant_label,
)


class PrefeituraLabelTests(SimpleTestCase):
    def test_joinville_com_uf(self):
        pref = Mock(nome_municipio="Joinville", estado="SC", url="joinville")
        self.assertEqual(prefeitura_label_from_instance(pref), "Joinville (SC)")

    def test_tenant_label_nao_usa_somente_uf(self):
        user = Mock(
            is_authenticated=True,
            is_staff=False,
            is_superuser=False,
            prefeitura=Mock(nome_municipio="Joinville", estado="SC", url="joinville"),
        )
        self.assertEqual(tenant_label(user), "Joinville (SC)")

    def test_staff(self):
        user = Mock(is_authenticated=True, is_staff=True, is_superuser=False, prefeitura=None)
        self.assertEqual(prefeitura_label(user), "Equipe DocMaster (staff)")


class PackageTipoGeraçãoTests(SimpleTestCase):
    def test_dispensa_rapida(self):
        self.assertEqual(
            package_to_tipo_geracao("dispensa_rapida_75_ii_compras"),
            "dispensa_rapida",
        )

    def test_dispensa_normal(self):
        self.assertEqual(
            package_to_tipo_geracao("dispensa_75_i_obras_engenharia"),
            "dispensa_normal",
        )

    def test_etp_via_fluxo(self):
        self.assertEqual(package_to_tipo_geracao("unknown", fluxo="gerar_llm"), "etp")

    def test_etp_livre_package(self):
        self.assertEqual(package_to_tipo_geracao("etp_livre"), "etp")

    def test_inexigibilidade_package(self):
        self.assertEqual(
            package_to_tipo_geracao("inexigibilidade_74_i_fornecedor_exclusivo"),
            "inexigibilidade",
        )


class MetricsNormalizationTests(SimpleTestCase):
    def test_unknown_package_becomes_other(self):
        self.assertEqual(normalize_package_key("pacote_inventado_xyz"), "other")

    def test_auth_login_result_clamped(self):
        self.assertEqual(normalize_auth_login_result("SUCCESS"), "success")
        self.assertEqual(normalize_auth_login_result("weird"), "failure")


class LlmTokenMetricsTests(SimpleTestCase):
    def test_clausulas_llm_recorded(self):
        labels = dict(
            prefeitura="Joinville (SC)",
            direction="entrada",
            fluxo="clausulas_llm",
            tipo_geracao="inexigibilidade",
            package="inexigibilidade_74_i_manutencao_veiculos",
        )
        before = docmaster_llm_tokens_total.labels(**labels)._value.get()
        record_llm_token_usage(
            fluxo="clausulas_llm",
            prefeitura="Joinville (SC)",
            package="inexigibilidade_74_i_manutencao_veiculos",
            prompt_tokens=80,
            completion_tokens=40,
        )
        after = docmaster_llm_tokens_total.labels(**labels)._value.get()
        self.assertEqual(after - before, 80.0)

    def test_llm_proxy_fluxo_not_recorded(self):
        labels = dict(
            prefeitura="X",
            direction="entrada",
            fluxo="llm_proxy_generate",
            tipo_geracao="other",
            package="unknown",
        )
        before = docmaster_llm_tokens_total.labels(**labels)._value.get()
        record_llm_token_usage(
            fluxo="llm_proxy_generate",
            prefeitura="X",
            prompt_tokens=100,
            completion_tokens=50,
        )
        after = docmaster_llm_tokens_total.labels(**labels)._value.get()
        self.assertEqual(before, after)

    def test_record_llm_token_usage_increments(self):
        labels_in = dict(
            prefeitura="Joinville (SC)",
            direction="entrada",
            fluxo="fill_tr_slots",
            tipo_geracao="dispensa_normal",
            package="dispensa_75_ii_compras",
        )
        labels_out = {**labels_in, "direction": "saida"}
        before_in = docmaster_llm_tokens_total.labels(**labels_in)._value.get()
        before_out = docmaster_llm_tokens_total.labels(**labels_out)._value.get()
        record_llm_token_usage(
            fluxo="fill_tr_slots",
            prefeitura="Joinville (SC)",
            package="dispensa_75_ii_compras",
            prompt_tokens=120,
            completion_tokens=45,
        )
        after_in = docmaster_llm_tokens_total.labels(**labels_in)._value.get()
        after_out = docmaster_llm_tokens_total.labels(**labels_out)._value.get()
        self.assertEqual(after_in - before_in, 120.0)
        self.assertEqual(after_out - before_out, 45.0)

    def test_clausulas_llm_increments_invocation_without_tokens(self):
        labels = dict(
            prefeitura="P",
            fluxo="clausulas_llm",
            tipo_geracao="inexigibilidade",
            package="inexigibilidade_74_i_manutencao_veiculos",
        )
        before = docmaster_llm_invocations_total.labels(**labels)._value.get()
        record_llm_token_usage(
            fluxo="clausulas_llm",
            prefeitura="P",
            package="inexigibilidade_74_i_manutencao_veiculos",
            prompt_tokens=0,
            completion_tokens=0,
        )
        after = docmaster_llm_invocations_total.labels(**labels)._value.get()
        self.assertEqual(after - before, 1.0)


class SetRequestMetricsTests(SimpleTestCase):
    def test_referer_fills_tr_dfd_generico(self):
        req = RequestFactory().post(
            "/api/documentos/fill-tr-slots",
            HTTP_REFERER="https://app.docmasteria.com.br/geracao/dispensa-art-75-ii/compras",
        )
        set_request_metrics(req, package="tr_dfd_generico")
        self.assertEqual(req.docmaster_metrics["package"], "dispensa_75_ii_compras")


class RecordLlmUsageFromResponseTests(SimpleTestCase):
    @patch("app.api.record_llm_token_usage")
    def test_records_invocation_without_tokens(self, mock_record):
        request = Mock()
        request.docmaster_metrics = {"package": "dispensa_75_ii_compras"}
        with patch("app.api.prefeitura_label_from_request", return_value="Joinville (SC)"):
            _record_llm_usage_from_response(request, "fill_tr_slots", usage=None)
        mock_record.assert_called_once_with(
            fluxo="fill_tr_slots",
            prefeitura="Joinville (SC)",
            package="dispensa_75_ii_compras",
            prompt_tokens=0,
            completion_tokens=0,
        )
