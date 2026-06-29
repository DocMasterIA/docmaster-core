"""Filtro de pedido para cláusulas dispensa — sem órgão/unidade administrativo."""
from __future__ import annotations

import unittest

from app.clausulas_qwen_prompt import dispensa_clausulas_pedido_from_user_prompt


class DispensaClausulasPedidoTests(unittest.TestCase):
    def test_keeps_contratado_and_setor(self):
        raw = (
            "O que será contratado: Conserto de fogão\n"
            "Setor/secretaria atendido: Secretaria de Administração"
        )
        out = dispensa_clausulas_pedido_from_user_prompt(raw)
        self.assertIn("Conserto de fogão", out)
        self.assertIn("Secretaria de Administração", out)

    def test_drops_orgao_cabecalho_processo(self):
        raw = "\n".join(
            [
                "Gerar documento com base nos dados preenchidos para dispensa rapida.",
                "Cabeçalho do documento: Modelo X",
                "Órgão: Prefeitura Municipal de Teste",
                "Processo: 123/2026",
                "Objeto (o que será contratado): Papel A4",
                "O que será contratado: Papel A4",
                "Setor/secretaria atendido: Secretaria de Finanças",
            ]
        )
        out = dispensa_clausulas_pedido_from_user_prompt(raw)
        self.assertNotIn("Prefeitura", out)
        self.assertNotIn("Modelo X", out)
        self.assertNotIn("123/2026", out)
        self.assertIn("Papel A4", out)
        self.assertIn("Secretaria de Finanças", out)

    def test_normal_setor_line_with_hint(self):
        raw = (
            "Setor/secretaria atendido (usar nas cláusulas de objeto e justificativa): "
            "Secretaria de Saúde"
        )
        out = dispensa_clausulas_pedido_from_user_prompt(raw)
        self.assertEqual(out, "Setor/secretaria atendido: Secretaria de Saúde")


if __name__ == "__main__":
    unittest.main()
