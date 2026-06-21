"""Roteamento objeto/justificativa → gateway externo (Qwen)."""
from __future__ import annotations

import unittest

from app import config


class ClausulasLlmRoutingTests(unittest.TestCase):
    def test_is_clausulas_package(self):
        self.assertTrue(config.is_clausulas_objeto_justificativa_package("dispensa_75_ii_compras"))
        self.assertTrue(
            config.is_clausulas_objeto_justificativa_package("inexigibilidade_74_i_fornecedor_exclusivo")
        )
        self.assertFalse(config.is_clausulas_objeto_justificativa_package("etp_livre"))
        self.assertFalse(config.is_clausulas_objeto_justificativa_package(""))

    def test_clausulas_base_url_when_configured(self):
        prev = config.LLM_CLAUSULAS_GENERATION_BASE_URL
        try:
            config.LLM_CLAUSULAS_GENERATION_BASE_URL = "http://qwen:8015"
            url = config.llm_generation_base_url_for_clausulas("dispensa_75_ii_servicos")
            self.assertEqual(url, "http://qwen:8015")
            url_etp = config.llm_generation_base_url_for_clausulas("etp_livre")
            self.assertEqual(url_etp, config.LLM_ORCHESTRATION_BASE_URL)
        finally:
            config.LLM_CLAUSULAS_GENERATION_BASE_URL = prev

    def test_clausulas_falls_back_without_env(self):
        prev = config.LLM_CLAUSULAS_GENERATION_BASE_URL
        try:
            config.LLM_CLAUSULAS_GENERATION_BASE_URL = ""
            url = config.llm_generation_base_url_for_clausulas("dispensa_75_ii_compras")
            self.assertEqual(url, config.LLM_ORCHESTRATION_BASE_URL)
        finally:
            config.LLM_CLAUSULAS_GENERATION_BASE_URL = prev

    def test_rich_prompt_auto_on_cloud(self):
        prev_url = config.LLM_CLAUSULAS_GENERATION_BASE_URL
        prev_profile = config.LLM_CLAUSULAS_PROMPT_PROFILE
        try:
            config.LLM_CLAUSULAS_GENERATION_BASE_URL = "http://qwen:8015"
            config.LLM_CLAUSULAS_PROMPT_PROFILE = "auto"
            self.assertTrue(config.clausulas_use_rich_prompt("http://qwen:8015"))
            config.LLM_CLAUSULAS_PROMPT_PROFILE = "lite"
            self.assertFalse(config.clausulas_use_rich_prompt("http://qwen:8015"))
        finally:
            config.LLM_CLAUSULAS_GENERATION_BASE_URL = prev_url
            config.LLM_CLAUSULAS_PROMPT_PROFILE = prev_profile


if __name__ == "__main__":
    unittest.main()
