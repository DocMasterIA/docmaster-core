"""Filtro de pedido para cláusulas dispensa — sem órgão/unidade administrativo."""
from __future__ import annotations

import unittest

from app.clausulas_qwen_prompt import dispensa_clausulas_pedido_from_user_prompt


class DispensaClausulasPedidoTests(unittest.TestCase):
    def test_keeps_contratado_and_caracteristicas(self):
        raw = (
            "O que será contratado: Conserto de fogão\n"
            "Características mínimas: Garantia de 90 dias"
        )
        out = dispensa_clausulas_pedido_from_user_prompt(raw)
        self.assertIn("Conserto de fogão", out)
        self.assertIn("Garantia de 90 dias", out)

    def test_drops_orgao_cabecalho_processo_and_setor(self):
        raw = "\n".join(
            [
                "Gerar documento com base nos dados preenchidos para dispensa rapida.",
                "Cabeçalho do documento: Modelo X",
                "Órgão: Prefeitura Municipal de Teste",
                "Processo: 123/2026",
                "Objeto (o que será contratado): Papel A4",
                "O que será contratado: Papel A4",
                "Setor/secretaria atendido: Secretaria de Finanças",
                "2.1 Setor requisitante (Unidade / Setor / Departamento): Secretaria de Saúde",
            ]
        )
        out = dispensa_clausulas_pedido_from_user_prompt(raw)
        self.assertNotIn("Prefeitura", out)
        self.assertNotIn("Modelo X", out)
        self.assertNotIn("123/2026", out)
        self.assertNotIn("Finanças", out)
        self.assertNotIn("Saúde", out)
        self.assertIn("Papel A4", out)

    def test_drops_setor_line_with_hint(self):
        raw = (
            "Setor/secretaria atendido (usar nas cláusulas de objeto e justificativa): "
            "Secretaria de Saúde"
        )
        out = dispensa_clausulas_pedido_from_user_prompt(raw)
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
