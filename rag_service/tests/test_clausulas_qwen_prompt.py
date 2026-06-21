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

    def test_system_asks_json_only(self):
        self.assertIn('{"objeto"', CLAUSULAS_QWEN_SYSTEM_PROMPT)

    def test_system_requires_depth(self):
        self.assertIn("8 a 12 frases", CLAUSULAS_QWEN_SYSTEM_PROMPT)
        self.assertIn("proibido texto genérico", CLAUSULAS_QWEN_SYSTEM_PROMPT.lower())


if __name__ == "__main__":
    unittest.main()
