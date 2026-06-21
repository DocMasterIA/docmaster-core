"""
Configuração do gateway Qwen (API compatível com OpenAI / DashScope).

Defina QWEN_API_KEY no ambiente. Modelo exato depende do provedor.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


def _env_str(key: str, default: str = "") -> str:
    raw = os.getenv(key)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip()


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
    port: int
    qwen_api_base_url: str
    qwen_api_key: str
    qwen_model_default: str
    qwen_timeout_seconds: float
    qwen_max_output_tokens: int
    qwen_max_prompt_chars: int
    qwen_daily_token_budget: int
    qwen_estimated_chars_per_token: int
    qwen_audit_log_dir: Optional[str]


def load_settings() -> Settings:
    audit = _env_str("QWEN_AUDIT_LOG_DIR")
    return Settings(
        port=_env_int("PORT", 8015),
        qwen_api_base_url=_env_str(
            "QWEN_API_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ).rstrip("/"),
        qwen_api_key=_env_str("QWEN_API_KEY"),
        qwen_model_default=_env_str("QWEN_MODEL", "qwen3.6-plus"),
        qwen_timeout_seconds=_env_float("QWEN_TIMEOUT", 120.0),
        qwen_max_output_tokens=_env_int("QWEN_MAX_OUTPUT_TOKENS", 4096),
        qwen_max_prompt_chars=_env_int("QWEN_MAX_PROMPT_CHARS", 120_000),
        qwen_daily_token_budget=_env_int("QWEN_DAILY_TOKEN_BUDGET", 0),
        qwen_estimated_chars_per_token=_env_int("QWEN_ESTIMATED_CHARS_PER_TOKEN", 4),
        qwen_audit_log_dir=audit or None,
    )


settings = load_settings()
