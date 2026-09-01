"""
Proxy para o serviço FastAPI pncp_researcher_service.

Cotações (CRUD) ficam no Django em `/api/pncp/cotacoes/research/sessions...`.
Este proxy repassa apenas operações do microserviço: índice local, market-search
e streams NDJSON.
"""
from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from backend.app.api import api_login_required
from backend.app.metrics import (
    normalize_pncp_research_action,
    record_platform_event,
    prefeitura_label_from_request,
)

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
    action = normalize_pncp_research_action(path)
    prefeitura = prefeitura_label_from_request(request)
    result = "error"

    try:
        if request.method == "GET":
            # local-index/stats agrega COUNT em vários SQLite (até dezenas de GB).
            stats_timeout = 120 if path.strip("/").startswith("local-index/stats") else 60
            resp = requests.get(url, timeout=stats_timeout)
            out = _json_or_raw_response(resp)
            result = "success" if resp.status_code < 400 else "error"
            return out

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
            # Erro antes do stream NDJSON: devolve JSON normal (422 validação, 502 PNCP, etc.)
            if up.status_code >= 400:
                try:
                    payload = up.json()
                except Exception:
                    payload = {"detail": (up.text or up.reason or "")[:800]}
                up.close()
                result = "error"
                return JsonResponse(payload, status=up.status_code, safe=False)

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
            result = "success" if up.status_code < 400 else "error"
            return out

        resp = requests.post(url, data=request.body, headers=hdr, timeout=600)
        out = _json_or_raw_response(resp)
        result = "success" if resp.status_code < 400 else "error"
        return out

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
    finally:
        record_platform_event(
            module="pncp_research",
            action=action,
            result=result,
            prefeitura=prefeitura,
        )


def _json_or_raw_response(resp: requests.Response) -> JsonResponse | HttpResponse:
    text = resp.text
    try:
        data: Any = resp.json()
        return JsonResponse(data, status=resp.status_code, safe=False)
    except Exception:
        return HttpResponse(text, status=resp.status_code, content_type=resp.headers.get("Content-Type", "text/plain"))
