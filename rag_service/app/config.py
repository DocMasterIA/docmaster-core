"""
Configurações do serviço RAG.

Conecta ao ChromaDB (servidor) e à camada de orquestração LLM (llm_api).
"""
from __future__ import annotations

import os


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# ChromaDB (instalado no servidor)
CHROMA_HOST: str = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT: int = _env_int("CHROMA_PORT", 8000)
CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "docmaster_docs")

# Base URL da orquestração LLM (llm_api) para geração de respostas
LLM_ORCHESTRATION_BASE_URL: str = os.getenv(
    "LLM_ORCHESTRATION_BASE_URL",
    "http://localhost:8002",
).rstrip("/")

# Base URL do llm_agent (para gerar estrutura de documentos)
LLM_AGENT_BASE_URL: str = os.getenv(
    "LLM_AGENT_BASE_URL",
    "http://localhost:8003",
).rstrip("/")

LLM_ORCHESTRATION_GENERATE_PATH: str = os.getenv(
    "LLM_ORCHESTRATION_GENERATE_PATH",
    "/api/llm/generate",
)

# Ollama (para embeddings, quando usar localmente)
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Timeouts:
# - RAG_TIMEOUT controla o timeout padrão (em segundos) para chamadas HTTP usadas no RAG,
#   incluindo consultas ao PNCP. Valor maior é útil para ingestões em massa.
# - Por padrão, usamos 120s para evitar ReadTimeout frequentes em chamadas pesadas.
RAG_TIMEOUT: float = float(os.getenv("RAG_TIMEOUT", "120"))
RAG_HTTP_TIMEOUT: float | None = None if RAG_TIMEOUT <= 0 else RAG_TIMEOUT
EMBEDDING_TIMEOUT: float = float(os.getenv("EMBEDDING_TIMEOUT", "30.0"))

# Retrieval
RAG_TOP_K: int = _env_int("RAG_TOP_K", 5)

# Pós-processamento de cláusulas (1 = ativo, 0 = desativado para debug/comparação)
RAG_POSTPROCESS: bool = os.getenv("RAG_POSTPROCESS", "1").strip() not in ("0", "false", "False", "no")

# Sanitização via LLM: remove meta-comentários usando a IA (1 = ativo). Alternativa à lista manual de regex.
RAG_LLM_SANITIZE: bool = os.getenv("RAG_LLM_SANITIZE", "1").strip() not in ("0", "false", "False", "no")
