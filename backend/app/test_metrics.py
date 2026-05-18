from unittest.mock import Mock

from django.test import SimpleTestCase

from app.metrics import prefeitura_label, prefeitura_label_from_instance, tenant_label


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
