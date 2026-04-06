"""
Configuração do gateway Qwen (API compatível com OpenAI / DashScope).

Defina QWEN_API_KEY no ambiente. Modelo exato depende do provedor.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    port: int = _env_int("PORT", 8015)
    qwen_api_base_url: str = os.getenv(
        "QWEN_API_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    ).rstrip("/")
    qwen_api_key: str = os.getenv("QWEN_API_KEY", "")
    qwen_model_default: str = os.getenv("QWEN_MODEL", "qwen3.6-plus")
    qwen_timeout_seconds: float = _env_float("QWEN_TIMEOUT", 120.0)
    qwen_max_output_tokens: int = _env_int("QWEN_MAX_OUTPUT_TOKENS", 4096)
    qwen_max_prompt_chars: int = _env_int("QWEN_MAX_PROMPT_CHARS", 120_000)
    qwen_daily_token_budget: int = _env_int("QWEN_DAILY_TOKEN_BUDGET", 0)
    qwen_estimated_chars_per_token: int = _env_int("QWEN_ESTIMATED_CHARS_PER_TOKEN", 4)
    qwen_audit_log_dir: Optional[str] = os.getenv("QWEN_AUDIT_LOG_DIR") or None


settings = Settings()
