"""
Configurações do agente de estrutura documental (llm_agent).

Carrega apenas o necessário para falar com a camada de orquestração
LLM (módulo llm_api) e ajustar timeouts.
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


# Base URL da API de orquestração LLM (módulo llm_api).
# Ex.: http://llm_api:8002 (Docker) ou http://localhost:8002 (dev local).
LLM_ORCHESTRATION_BASE_URL: str = os.getenv(
    "LLM_ORCHESTRATION_BASE_URL",
    "http://localhost:8002",
).rstrip("/")

# Path do endpoint generate na orquestração (chama Ollama /api/generate).
LLM_ORCHESTRATION_GENERATE_PATH: str = os.getenv(
    "LLM_ORCHESTRATION_GENERATE_PATH",
    "/api/llm/generate",
)

# Timeout em segundos para a chamada ao módulo de orquestração (llm_api pode demorar com Ollama).
AGENT_TIMEOUT: float = _env_float("AGENT_TIMEOUT", 120.0)

# Número máximo de tentativas semânticas (re-prompt) para corrigir saída inválida.
AGENT_MAX_RETRIES: int = _env_int("AGENT_MAX_RETRIES", 2)

# Registro manual de seções (JSON). Se existir, será usado quando a requisição não enviar sections_catalog.
SECTIONS_REGISTRY_PATH: str = os.getenv(
    "SECTIONS_REGISTRY_PATH",
    os.path.join(os.path.dirname(__file__), "..", "data", "sections_registry.json"),
)

# Chave para atualizar o registro via POST /api/agent/registry (header X-Update-Key). Vazio = endpoint recusa atualização.
REGISTRY_UPDATE_KEY: str = os.getenv("REGISTRY_UPDATE_KEY", "").strip()

