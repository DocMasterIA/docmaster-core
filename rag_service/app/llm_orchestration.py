"""Cliente da orquestração LLM com acumulação de tokens por requisição RAG."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

import httpx

from .config import LLM_ORCHESTRATION_BASE_URL, LLM_ORCHESTRATION_GENERATE_PATH

_TOKEN_ACC: ContextVar["TokenAccumulator | None"] = ContextVar("llm_token_acc", default=None)


@dataclass
class TokenAccumulator:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    llm_calls: int = 0

    def add_from_response(self, body: Any) -> None:
        prompt, completion = _extract_from_body(body)
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        if prompt or completion:
            self.llm_calls += 1

    def to_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.prompt_tokens + self.completion_tokens,
            "llm_calls": self.llm_calls,
        }


def _extract_from_body(body: Any) -> tuple[int, int]:
    if not isinstance(body, dict):
        return 0, 0
    usage = body.get("token_usage")
    if isinstance(usage, dict):
        return _as_int(usage.get("prompt_tokens")), _as_int(usage.get("completion_tokens"))
    data = body.get("data", body)
    if not isinstance(data, dict):
        return 0, 0
    return _as_int(data.get("prompt_eval_count")), _as_int(data.get("eval_count"))


def _as_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def prefeitura_label_from_context(context: dict[str, Any] | None) -> str:
    if not context or not isinstance(context, dict):
        return "Não identificado"
    explicit = (context.get("prefeitura_metric") or "").strip()
    if explicit:
        return explicit[:56]
    usuario = context.get("usuario") or {}
    if not isinstance(usuario, dict):
        return "Não identificado"
    nome = (usuario.get("prefeitura") or "").strip()
    uf = (usuario.get("estado_uf") or "").strip().upper()
    if nome and uf:
        return f"{nome} ({uf})"[:56]
    if nome:
        return nome[:56]
    return "Não identificado"


def _headers(prefeitura: str) -> dict[str, str]:
    h: dict[str, str] = {}
    if prefeitura and prefeitura != "Não identificado":
        h["X-DocMaster-Prefeitura"] = prefeitura[:56]
    return h


@asynccontextmanager
async def llm_token_scope():
    acc = TokenAccumulator()
    token = _TOKEN_ACC.set(acc)
    try:
        yield acc
    finally:
        _TOKEN_ACC.reset(token)


def current_token_usage() -> dict[str, int]:
    acc = _TOKEN_ACC.get()
    return acc.to_dict() if acc else {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "llm_calls": 0,
    }


async def llm_post_generate(
    client: httpx.AsyncClient,
    prompt: str,
    *,
    user_context: dict[str, Any] | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """POST /api/llm/generate com prefeitura e acumulação de tokens."""
    prefeitura = prefeitura_label_from_context(user_context)
    url = f"{LLM_ORCHESTRATION_BASE_URL}{LLM_ORCHESTRATION_GENERATE_PATH}"
    payload: dict[str, Any] = {"prompt": prompt, "stream": False, "prefeitura": prefeitura}
    if model:
        payload["model"] = model
    resp = await client.post(url, json=payload, headers=_headers(prefeitura))
    resp.raise_for_status()
    body = resp.json()
    acc = _TOKEN_ACC.get()
    if acc:
        acc.add_from_response(body)
    return body if isinstance(body, dict) else {}


def token_usage_response_header(acc: TokenAccumulator | None = None) -> dict[str, str]:
    data = (acc or _TOKEN_ACC.get())
    if not data:
        return {}
    return {"X-DocMaster-LLM-Token-Usage": json.dumps(data.to_dict(), ensure_ascii=False)}
