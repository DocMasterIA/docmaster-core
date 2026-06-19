"""Config IA da busca inteligente PNCP."""
from __future__ import annotations

import unittest

from app import config


class PncpIaConfigTests(unittest.TestCase):
    def test_ia_defaults(self):
        self.assertTrue(config.PNCP_IA_RERANK_ENABLED)
        self.assertEqual(config.PNCP_IA_GENERATE_PATH, "/api/llm/generate")

    def test_ia_base_url_stripped(self):
        prev = config.PNCP_IA_BASE_URL
        try:
            config.PNCP_IA_BASE_URL = "http://qwen_llm_service:8015/"
            self.assertEqual(config.PNCP_IA_BASE_URL.rstrip("/"), "http://qwen_llm_service:8015")
        finally:
            config.PNCP_IA_BASE_URL = prev


if __name__ == "__main__":
    unittest.main()
