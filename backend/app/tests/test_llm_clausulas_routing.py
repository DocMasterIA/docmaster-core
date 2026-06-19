"""Proxy LLM — roteamento de cláusulas dispensa/inexigibilidade."""
from __future__ import annotations

from django.test import RequestFactory, SimpleTestCase, override_settings

from backend.app.llm_proxy import _llm_base_url_for_proxy, _llm_proxy_timeout_seconds
from backend.app.slot_package_keys import is_clausulas_objeto_justificativa_package


class SlotPackageClausulasTests(SimpleTestCase):
    def test_is_clausulas_package(self):
        self.assertTrue(is_clausulas_objeto_justificativa_package("dispensa_rapida_75_ii_compras"))
        self.assertFalse(is_clausulas_objeto_justificativa_package("tr_dfd_generico"))


class LlmProxyRoutingTests(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()

    @override_settings(
        LLM_API_BASE_URL="http://llm_api:8002",
        LLM_CLAUSULAS_API_BASE_URL="http://qwen_llm_service:8015",
    )
    def test_generate_dispensa_routes_to_qwen(self):
        req = self.rf.post(
            "/api/llm/generate",
            data='{"slot_package_key":"dispensa_75_ii_compras"}',
            content_type="application/json",
            HTTP_REFERER="https://docmasteria.com.br/geracao/dispensa-art-75-ii/compras",
        )
        payload = {"slot_package_key": "dispensa_75_ii_compras"}
        base = _llm_base_url_for_proxy("generate", payload, req)
        self.assertEqual(base, "http://qwen_llm_service:8015")

    @override_settings(
        LLM_API_BASE_URL="http://llm_api:8002",
        LLM_CLAUSULAS_API_BASE_URL="http://qwen_llm_service:8015",
    )
    def test_health_stays_on_llm_api(self):
        req = self.rf.get("/api/llm/health")
        base = _llm_base_url_for_proxy("health", {}, req)
        self.assertEqual(base, "http://llm_api:8002")

    @override_settings(
        LLM_API_BASE_URL="http://llm_api:8002",
        LLM_CLAUSULAS_API_BASE_URL="http://qwen_llm_service:8015",
        LLM_CLAUSULAS_PROXY_TIMEOUT=180,
    )
    def test_clausulas_timeout_longer(self):
        req = self.rf.post("/api/llm/generate")
        payload = {"slot_package_key": "inexigibilidade_74_i_manutencao_veiculos"}
        timeout = _llm_proxy_timeout_seconds("generate", payload, req)
        self.assertEqual(timeout, 180)
