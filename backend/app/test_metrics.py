from unittest.mock import Mock

from django.test import SimpleTestCase

from app.metrics import (
    docmaster_llm_tokens_total,
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


class LlmTokenMetricsTests(SimpleTestCase):
    def test_record_llm_token_usage_increments(self):
        labels_in = dict(prefeitura="Joinville (SC)", direction="entrada", fluxo="fill_tr_slots")
        labels_out = dict(prefeitura="Joinville (SC)", direction="saida", fluxo="fill_tr_slots")
        before_in = docmaster_llm_tokens_total.labels(**labels_in)._value.get()
        before_out = docmaster_llm_tokens_total.labels(**labels_out)._value.get()
        record_llm_token_usage(
            fluxo="fill_tr_slots",
            prefeitura="Joinville (SC)",
            prompt_tokens=120,
            completion_tokens=45,
        )
        after_in = docmaster_llm_tokens_total.labels(**labels_in)._value.get()
        after_out = docmaster_llm_tokens_total.labels(**labels_out)._value.get()
        self.assertEqual(after_in - before_in, 120.0)
        self.assertEqual(after_out - before_out, 45.0)
