"""
Cliente HTTP para API chat compatível com OpenAI (Qwen via DashScope ou outro host).
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import settings

logger = logging.getLogger(__name__)


class QwenGatewayError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def chat_completion(
    prompt: str,
    model: str | None,
    max_output_tokens: int | None = None,
) -> tuple[str, dict[str, Any]]:
    if not settings.qwen_api_key.strip():
        raise QwenGatewayError("QWEN_API_KEY não configurada.", status_code=503)

    m = (model or settings.qwen_model_default).strip()
    max_out = max(1, min(int(max_output_tokens or settings.qwen_max_output_tokens), 32000))

    url = f"{settings.qwen_api_base_url}/chat/completions"
    payload: dict[str, Any] = {
        "model": m,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_out,
    }

    headers = {
        "Authorization": f"Bearer {settings.qwen_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=settings.qwen_timeout_seconds) as client:
            resp = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as e:
        raise QwenGatewayError(f"Timeout na API Qwen: {e}", status_code=504) from e
    except httpx.RequestError as e:
        raise QwenGatewayError(f"Erro de rede na API Qwen: {e}", status_code=502) from e

    if resp.status_code == 401:
        raise QwenGatewayError("Não autorizado: verifique QWEN_API_KEY.", status_code=401)
    if resp.status_code == 429:
        raise QwenGatewayError("Rate limit na API Qwen.", status_code=429)

    try:
        body = resp.json()
    except Exception:
        raise QwenGatewayError(f"Resposta não-JSON (HTTP {resp.status_code}): {resp.text[:500]}", status_code=502)

    if resp.status_code >= 400:
        err = body.get("error", {}) if isinstance(body, dict) else {}
        msg = err.get("message", str(body)) if isinstance(err, dict) else str(body)
        raise QwenGatewayError(f"API Qwen HTTP {resp.status_code}: {msg}", status_code=502)

    choices = body.get("choices") if isinstance(body, dict) else None
    if not choices or not isinstance(choices, list):
        raise QwenGatewayError("Resposta sem choices.", status_code=502)

    msg0 = (choices[0] or {}).get("message") or {}
    content = (msg0.get("content") or "").strip()

    usage: dict[str, Any] = {}
    raw_usage = body.get("usage") if isinstance(body, dict) else None
    if isinstance(raw_usage, dict):
        usage = {
            "prompt_tokens": raw_usage.get("prompt_tokens", raw_usage.get("input_tokens", 0)),
            "completion_tokens": raw_usage.get(
                "completion_tokens", raw_usage.get("output_tokens", 0)
            ),
            "total_tokens": raw_usage.get("total_tokens"),
        }

    return content, usage
