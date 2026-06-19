"""
Proxy para o serviço FastAPI de orquestração LLM.

O frontend chama /api/llm/... no Django (com sessão/cookie). O Django valida
a sessão e repassa a requisição ao FastAPI (localhost).

Geração de cláusulas (POST /api/llm/generate) grava tokens com fluxo clausulas_llm
e package inferido do Referer — necessário para inexigibilidade (não usa fill-tr-slots).
"""
from __future__ import annotations

import json
import logging

import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from backend.app.api import api_login_required
from backend.app.metrics import (
    normalize_llm_action,
    prefeitura_label_from_request,
    record_llm_token_usage,
    record_platform_event,
)
from backend.app.slot_package_keys import is_clausulas_objeto_justificativa_package, resolve_slot_package_key

logger = logging.getLogger(__name__)


def _llm_base_url():
    return getattr(settings, "LLM_API_BASE_URL", "http://127.0.0.1:8002").rstrip("/")


def _llm_base_url_for_proxy(path: str, payload: dict | None, request) -> str:
    """Roteia generate de dispensa/inexigibilidade para gateway externo quando configurado."""
    action = (path or "").strip("/").lower()
    if action != "generate":
        return _llm_base_url()
    pkg = resolve_slot_package_key(payload, request)
    if not is_clausulas_objeto_justificativa_package(pkg):
        return _llm_base_url()
    clausulas = getattr(settings, "LLM_CLAUSULAS_API_BASE_URL", "").strip().rstrip("/")
    return clausulas or _llm_base_url()


def _llm_proxy_timeout_seconds(path: str, payload: dict | None, request) -> int:
    action = (path or "").strip("/").lower()
    if action != "generate":
        return 30
    base = _llm_base_url_for_proxy(path, payload, request)
    clausulas = getattr(settings, "LLM_CLAUSULAS_API_BASE_URL", "").strip().rstrip("/")
    if clausulas and base.rstrip("/") == clausulas.rstrip("/"):
        return int(getattr(settings, "LLM_CLAUSULAS_PROXY_TIMEOUT", 180))
    return 120


@api_login_required
@csrf_exempt
def llm_proxy(request, path):
    """
    Repassa GET/POST para o serviço FastAPI em LLM_API_BASE_URL.
    path: trecho após /api/llm/ (ex: health, planner, section, generate).
    """
    if request.method not in ("GET", "POST"):
        return JsonResponse({"error": "Método não permitido"}, status=405)

    payload: dict = {}
    raw_body = None
    if request.method == "POST":
        raw_body = request.body
        if raw_body:
            try:
                parsed = json.loads(raw_body)
                if isinstance(parsed, dict):
                    payload = parsed
            except (json.JSONDecodeError, TypeError, ValueError):
                payload = {}

    base = _llm_base_url_for_proxy(path, payload, request)
    url = f"{base}/api/llm/{path}"
    action = normalize_llm_action(path)
    prefeitura = prefeitura_label_from_request(request)
    headers = {
        "Content-Type": "application/json",
        "X-DocMaster-Prefeitura": prefeitura,
    }
    result = "error"
    try:
        if request.method == "GET":
            resp = requests.get(url, timeout=30)
        else:
            timeout = _llm_proxy_timeout_seconds(path, payload, request)
            resp = requests.post(url, data=raw_body, headers=headers, timeout=timeout)

        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        response = JsonResponse(data, status=resp.status_code, safe=isinstance(data, dict))
        result = "success" if resp.status_code < 400 else "error"
        if isinstance(data, dict) and data.get("ok") is False:
            result = "error"
        if result == "success" and action == "generate" and isinstance(data, dict):
            usage = data.get("token_usage")
            if not isinstance(usage, dict):
                usage = {}
            pkg = resolve_slot_package_key(payload, request)
            record_llm_token_usage(
                fluxo="clausulas_llm",
                prefeitura=prefeitura,
                package=pkg or "unknown",
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
            )
        return response
    except requests.exceptions.Timeout:
        logger.warning("LLM proxy timeout: %s", url)
        return JsonResponse(
            {"error": "Serviço de IA demorou para responder. Tente novamente."},
            status=504,
        )
    except requests.exceptions.ConnectionError as e:
        logger.warning("LLM proxy connection error: %s — %s", url, e)
        return JsonResponse(
            {"error": "Serviço de IA indisponível. Verifique se o serviço está em execução."},
            status=503,
        )
    except Exception as e:
        logger.exception("LLM proxy error: %s", e)
        return JsonResponse({"error": "Erro ao comunicar com o serviço de IA."}, status=502)
    finally:
        record_platform_event(
            module="llm",
            action=action,
            result=result,
            prefeitura=prefeitura,
        )
