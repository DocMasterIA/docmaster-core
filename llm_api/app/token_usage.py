"""Extrai contagem de tokens das respostas Ollama / orquestração."""
from __future__ import annotations

from typing import Any


def extract_token_usage(body: Any) -> tuple[int, int, str]:
    """
    Retorna (prompt_tokens, completion_tokens, model_name).
    Ollama /api/generate: prompt_eval_count, eval_count.
    """
    if not isinstance(body, dict):
        return 0, 0, ""

    data = body.get("data", body)
    if not isinstance(data, dict):
        return 0, 0, ""

    prompt = _as_int(data.get("prompt_eval_count"))
    completion = _as_int(data.get("eval_count"))
    model = str(data.get("model") or body.get("model") or "").strip()[:48]
    return prompt, completion, model


def _as_int(value: Any) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, n)
