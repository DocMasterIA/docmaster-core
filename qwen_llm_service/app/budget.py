"""
Controle simples de orçamento diário de tokens (UTC).

Reinicia à meia-noite UTC. Para múltiplas réplicas use Redis/DB no futuro.
"""
from __future__ import annotations

import threading
from datetime import date, datetime, timezone
from typing import Tuple

from .config import settings

_lock = threading.Lock()
_day: date | None = None
_used_input: int = 0
_used_output: int = 0


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _reset_if_new_day() -> None:
    global _day, _used_input, _used_output
    t = _today_utc()
    if _day != t:
        _day = t
        _used_input = 0
        _used_output = 0


def get_usage_today() -> Tuple[int, int, int]:
    """(input_tokens, output_tokens, total) consumidos hoje."""
    with _lock:
        _reset_if_new_day()
        total = _used_input + _used_output
        return _used_input, _used_output, total


def check_pre_request(estimated_prompt_tokens: int, max_output_tokens: int) -> tuple[bool, str]:
    """
    Verifica se a requisição estimada cabe no orçamento diário (antes da chamada HTTP).
    Retorna (ok, mensagem_erro_vazia_se_ok).
    """
    budget = settings.qwen_daily_token_budget
    if budget <= 0:
        return True, ""

    need = estimated_prompt_tokens + max_output_tokens
    with _lock:
        _reset_if_new_day()
        total = _used_input + _used_output
        if total + need > budget:
            return (
                False,
                f"Orçamento diário de tokens excedido (uso {total}/{budget}; estimativa desta chamada ~{need}).",
            )
    return True, ""


def record_usage(input_tokens: int, output_tokens: int) -> None:
    """Registra uso após resposta (tokens reportados pela API ou estimados). Sempre contabiliza para /usage-today."""
    inp = max(0, int(input_tokens))
    out = max(0, int(output_tokens))
    global _used_input, _used_output
    with _lock:
        _reset_if_new_day()
        _used_input += inp
        _used_output += out
