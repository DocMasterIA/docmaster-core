"""
Proxy para o serviço FastAPI de orquestração LLM.

O frontend chama /api/llm/... no Django (com sessão/cookie). O Django valida
a sessão e repassa a requisição ao FastAPI (localhost). Assim o FastAPI+IA
só é acessível por usuários autenticados via sessão Django.
"""
import logging

import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from backend.app.api import api_login_required

logger = logging.getLogger(__name__)


def _llm_base_url():
    return getattr(settings, "LLM_API_BASE_URL", "http://127.0.0.1:8002").rstrip("/")


@api_login_required
@csrf_exempt
def llm_proxy(request, path):
    """
    Repassa GET/POST para o serviço FastAPI em LLM_API_BASE_URL.
    path: trecho após /api/llm/ (ex: health, planner, section, generate).
    """
    if request.method not in ("GET", "POST"):
        return JsonResponse({"error": "Método não permitido"}, status=405)

    base = _llm_base_url()
    url = f"{base}/api/llm/{path}"
    headers = {"Content-Type": "application/json"}

    try:
        if request.method == "GET":
            resp = requests.get(url, timeout=30)
        else:
            body = request.body
            resp = requests.post(url, data=body, headers=headers, timeout=120)

        # Repassa status e corpo JSON (dict ou list)
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        return JsonResponse(data, status=resp.status_code, safe=isinstance(data, dict))
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
