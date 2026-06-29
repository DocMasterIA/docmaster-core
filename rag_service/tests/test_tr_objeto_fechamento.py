"""Fechamento normativo do objeto no TR."""
import unittest

from app.tr_deixis import adapt_text_for_dfd_or_oficio, adapt_text_for_tr
from app.tr_objeto_fechamento import (
    TR_FECHAMENTO_AQUISICAO,
    ensure_tr_objeto_fechamento,
)


class TrObjetoFechamentoTests(unittest.TestCase):
    def test_append_aquisicao_fechamento(self):
        raw = (
            "Aquisição de material de expediente, visando atender à Secretaria de Administração."
        )
        out = ensure_tr_objeto_fechamento(raw)
        self.assertTrue(out.endswith(TR_FECHAMENTO_AQUISICAO + "."))
        self.assertIn("neste Termo de Referência", out)

    def test_normalize_existing_fechamento(self):
        raw = (
            "Aquisição de toners, conforme quantidades e demais condições estabelecidas "
            "no Termo de Referência."
        )
        out = ensure_tr_objeto_fechamento(raw)
        self.assertIn("neste Termo de Referência", out)
        self.assertNotIn("no Termo de Referência", out)

    def test_contratacao_usa_fechamento_quantidades(self):
        raw = (
            "Contratação de serviço especializado de limpeza predial, destinado à "
            "conservação dos prédios públicos municipais."
        )
        out = ensure_tr_objeto_fechamento(raw)
        self.assertIn("conforme quantidades", out.lower())
        self.assertNotIn("requisitos técnicos", out.lower())
        self.assertIn("neste Termo de Referência", out)

    def test_dfd_converts_neste_to_no(self):
        tr = ensure_tr_objeto_fechamento(
            "Aquisição de uniformes escolares para a rede municipal."
        )
        dfd = adapt_text_for_dfd_or_oficio(tr)
        self.assertIn("no Termo de Referência", dfd)
        self.assertNotIn("neste Termo de Referência", dfd)

    def test_tr_keeps_neste_after_roundtrip(self):
        tr = ensure_tr_objeto_fechamento("Aquisição de gêneros alimentícios.")
        back = adapt_text_for_tr(adapt_text_for_dfd_or_oficio(tr))
        self.assertIn("neste Termo de Referência", back)


if __name__ == "__main__":
    unittest.main()
