"""
Proxy para o serviço FastAPI pncp_researcher_service.

O frontend chama /api/pncp-research/... no Django (sessão). O Django repassa
ao serviço PNCP (localhost / rede Docker), inclusive NDJSON em market-search/stream.
"""
from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from backend.app.api import api_login_required

logger = logging.getLogger(__name__)


def _pncp_research_base_url() -> str:
    return getattr(settings, "PNCP_RESEARCHER_BASE_URL", "http://127.0.0.1:8012").rstrip("/")


def _upstream_url(path: str) -> str:
    p = (path or "").strip("/")
    return f"{_pncp_research_base_url()}/api/pncp-research/{p}"


def _is_stream_path(path: str) -> bool:
    return path.rstrip("/").endswith("stream")


@api_login_required
@csrf_exempt
def pncp_research_proxy(request, path: str):
    if request.method not in ("GET", "POST", "OPTIONS"):
        return JsonResponse({"error": "Método não permitido"}, status=405)
    if request.method == "OPTIONS":
        return HttpResponse(status=204)

    url = _upstream_url(path)

    try:
        if request.method == "GET":
            resp = requests.get(url, timeout=60)
            return _json_or_raw_response(resp)

        content_type = request.META.get("CONTENT_TYPE", "application/json")
        hdr = {"Content-Type": content_type}

        if _is_stream_path(path):
            up = requests.post(
                url,
                data=request.body,
                headers=hdr,
                stream=True,
                timeout=(30, 900),
            )

            def stream_iter():
                try:
                    for chunk in up.iter_content(chunk_size=8192):
                        if chunk:
                            yield chunk
                finally:
                    up.close()

            out = StreamingHttpResponse(
                stream_iter(),
                content_type=up.headers.get("Content-Type", "application/x-ndjson"),
                status=up.status_code,
            )
            # Evita buffering no Gunicorn/nginx intermediário quando possível
            out["X-Accel-Buffering"] = "no"
            return out

        resp = requests.post(url, data=request.body, headers=hdr, timeout=600)
        return _json_or_raw_response(resp)

    except requests.exceptions.Timeout:
        logger.warning("PNCP research proxy timeout: %s", url)
        return JsonResponse(
            {"error": "Pesquisa PNCP demorou demais. Tente reduzir max_paginas ou o período."},
            status=504,
        )
    except requests.exceptions.ConnectionError as e:
        logger.warning("PNCP research proxy connection error: %s — %s", url, e)
        return JsonResponse(
            {"error": "Serviço de pesquisa PNCP indisponível. Verifique se está em execução."},
            status=503,
        )
    except Exception as e:
        logger.exception("PNCP research proxy error: %s", e)
        return JsonResponse({"error": "Erro ao comunicar com o pesquisador PNCP."}, status=502)


def _json_or_raw_response(resp: requests.Response) -> JsonResponse | HttpResponse:
    text = resp.text
    try:
        data: Any = resp.json()
        return JsonResponse(data, status=resp.status_code, safe=False)
    except Exception:
        return HttpResponse(text, status=resp.status_code, content_type=resp.headers.get("Content-Type", "text/plain"))
