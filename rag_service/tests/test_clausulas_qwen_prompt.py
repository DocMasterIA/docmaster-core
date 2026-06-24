"""Prompt enxuto Qwen para cláusulas."""
from __future__ import annotations

import unittest

from app.clausulas_qwen_prompt import (
    CLAUSULAS_QWEN_SYSTEM_PROMPT,
    build_clausulas_qwen_full_prompt,
)


class ClausulasQwenPromptTests(unittest.TestCase):
    def test_full_prompt_wraps_system_user(self):
        full = build_clausulas_qwen_full_prompt("O que será contratado: papel A4")
        self.assertIn("<<SYSTEM>>", full)
        self.assertIn("<<USER>>", full)
        self.assertIn(CLAUSULAS_QWEN_SYSTEM_PROMPT[:40], full)
        self.assertIn("papel A4", full)

    def test_rapida_fluxo_adds_user_hint(self):
        full = build_clausulas_qwen_full_prompt(
            "O que será contratado: reforma predial",
            fluxo_ui="rapida",
        )
        self.assertIn("Dispensa rápida", full)
        self.assertIn("pare após o 3º", full.lower())

    def test_normal_fluxo_adds_setor_hint(self):
        full = build_clausulas_qwen_full_prompt(
            "O que será contratado: papel A4\nSetor/secretaria atendido: Administração",
            fluxo_ui="normal",
        )
        self.assertIn("Dispensa normal", full)
        self.assertIn("setor/secretaria", full.lower())

    def test_system_asks_json_only(self):
        self.assertIn('{"objeto"', CLAUSULAS_QWEN_SYSTEM_PROMPT)

    def test_system_requires_three_paragraphs(self):
        self.assertIn("exatamente 3 parágrafos", CLAUSULAS_QWEN_SYSTEM_PROMPT.lower())
        self.assertIn("proibido texto genérico", CLAUSULAS_QWEN_SYSTEM_PROMPT.lower())
        self.assertNotIn("8 a 12 frases", CLAUSULAS_QWEN_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
