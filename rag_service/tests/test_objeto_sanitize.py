"""Sanitização do campo objeto (sem fechamento TR / justificativa)."""
import unittest

from app.objeto_clause_sanitize import sanitize_objeto_clause_pura


class ObjetoSanitizeTests(unittest.TestCase):
    def test_remove_execucao_obedecera_fechamento_tr(self):
        raw = (
            "Contratação de empresa especializada para execução de serviços de reforma predial "
            "nas instalações do edifício sede da Prefeitura Municipal de Itajaí, visando a recuperação "
            "estrutural, funcional e estética do imóvel. A execução obedecerá rigorosamente às "
            "especificações técnicas, quantitativos e condições estabelecidas no presente Termo de Referência."
        )
        out = sanitize_objeto_clause_pura(raw)
        self.assertIn("reforma predial", out.lower())
        self.assertNotIn("obedecerá rigorosamente", out.lower())
        self.assertNotIn("especificações técnicas", out.lower())

    def test_remove_conforme_quantidades_trailing(self):
        raw = (
            "Aquisição de material de expediente, visando atender à Secretaria de Administração, "
            "conforme quantidades e demais condições estabelecidas neste Termo de Referência."
        )
        out = sanitize_objeto_clause_pura(raw)
        self.assertIn("material de expediente", out.lower())
        self.assertNotIn("conforme quantidades", out.lower())


if __name__ == "__main__":
    unittest.main()
