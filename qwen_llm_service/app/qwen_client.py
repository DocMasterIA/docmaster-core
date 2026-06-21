"""
Cliente HTTP para API chat compatível com OpenAI (Qwen via DashScope ou outro host).
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import load_settings

logger = logging.getLogger(__name__)


def _split_system_user_prompt(prompt: str) -> tuple[str | None, str]:
    """Extrai <<SYSTEM>> / <<USER>> usado pelo rag_service."""
    raw = (prompt or "").strip()
    if "<<SYSTEM>>" not in raw or "<<USER>>" not in raw:
        return None, raw
    _, rest = raw.split("<<SYSTEM>>", 1)
    system_part, user_part = rest.split("<<USER>>", 1)
    system = system_part.strip() or None
    user = user_part.strip() or raw
    return system, user


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
    cfg = load_settings()
    api_key = cfg.qwen_api_key.strip().strip('"').strip("'")
    if not api_key:
        raise QwenGatewayError("QWEN_API_KEY não configurada.", status_code=503)

    m = (model or cfg.qwen_model_default).strip()
    max_out = max(1, min(int(max_output_tokens or cfg.qwen_max_output_tokens), 32000))

    url = f"{cfg.qwen_api_base_url}/chat/completions"
    system_text, user_text = _split_system_user_prompt(prompt)
    messages: list[dict[str, str]] = []
    if system_text:
        messages.append({"role": "system", "content": system_text})
    messages.append({"role": "user", "content": user_text})

    payload: dict[str, Any] = {
        "model": m,
        "messages": messages,
        "max_tokens": max_out,
        # Modelos híbridos Qwen3.x exigem flag explícita em chamadas não-streaming.
        "enable_thinking": False,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=cfg.qwen_timeout_seconds, trust_env=False) as client:
            resp = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as e:
        raise QwenGatewayError(f"Timeout na API Qwen: {e}", status_code=504) from e
    except httpx.RequestError as e:
        raise QwenGatewayError(f"Erro de rede na API Qwen: {e}", status_code=502) from e

    if resp.status_code == 401:
        detail = "Não autorizado: verifique QWEN_API_KEY (mesmo workspace/região do endpoint)."
        try:
            body401 = resp.json()
            err = body401.get("error", {}) if isinstance(body401, dict) else {}
            if isinstance(err, dict) and err.get("message"):
                detail = f"Não autorizado: {err.get('message')}"
            elif isinstance(body401, dict) and body401.get("message"):
                detail = f"Não autorizado: {body401.get('message')}"
        except Exception:
            if resp.text.strip():
                detail = f"Não autorizado: {resp.text.strip()[:300]}"
        logger.warning(
            "Qwen API 401 model=%s url=%s body=%s",
            m,
            cfg.qwen_api_base_url,
            resp.text[:500],
        )
        raise QwenGatewayError(detail, status_code=401)
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
