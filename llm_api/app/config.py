"""
Configurações da camada de orquestração LLM.

Base URL da API local de IA, timeout, retries e demais parâmetros.
Carrega de variáveis de ambiente (com defaults).
"""
from __future__ import annotations

import os
from typing import Optional


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


# Base URL do Ollama (servidor de IA local)
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

# Timeout total da requisição em segundos
LLM_TIMEOUT: float = _env_float("LLM_TIMEOUT", 120.0)

# Número máximo de tentativas (retries) em caso de falha transitória
LLM_MAX_RETRIES: int = _env_int("LLM_MAX_RETRIES", 3)

# Diretório para logs de auditoria (opcional). Se vazio, o audit usa pasta padrão "logs" automaticamente.
LLM_AUDIT_LOG_DIR: Optional[str] = os.environ.get("LLM_AUDIT_LOG_DIR") or None

# Endpoints relativos ao OLLAMA_BASE_URL (podem ser sobrescritos por env se necessário)
LLM_ENDPOINT_PLANNER: str = os.environ.get("LLM_ENDPOINT_PLANNER", "/v1/planner")
LLM_ENDPOINT_SECTION: str = os.environ.get("LLM_ENDPOINT_SECTION", "/v1/section")
# Análise de editais: avaliação de documento (não gera/modifica, apenas analisa)
LLM_ENDPOINT_ANALYSIS: str = os.environ.get("LLM_ENDPOINT_ANALYSIS", "/v1/analysis")

# Ollama: endpoint e modelo padrão para /api/generate
OLLAMA_GENERATE_PATH: str = os.getenv("OLLAMA_GENERATE_PATH", "/api/generate")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
# Modelo menor para cláusulas curtas (objeto/justificativa). Alvo ~2–4s em CPU com 3B.
OLLAMA_MODEL_FAST: str = os.getenv("OLLAMA_MODEL_FAST", "qwen2.5:3b")
