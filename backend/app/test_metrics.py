from unittest.mock import Mock

from django.test import SimpleTestCase

from app.metrics import (
    docmaster_llm_tokens_total,
    package_to_tipo_geracao,
    prefeitura_label,
    prefeitura_label_from_instance,
    record_llm_token_usage,
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


class LlmTokenMetricsTests(SimpleTestCase):
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
