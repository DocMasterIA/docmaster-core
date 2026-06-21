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

# Base URL da orquestração LLM para geração (POST /api/llm/generate) — padrão: llm_api + Ollama.
LLM_ORCHESTRATION_BASE_URL: str = os.getenv(
    "LLM_ORCHESTRATION_BASE_URL",
    "http://localhost:8002",
).rstrip("/")

# Só Estudo Técnico Preliminar (ETP): se definido, cláusulas/listas/tabelas desse tipo usam este
# serviço (ex.: qwen_llm_service em 8015). Demais documentos continuam em LLM_ORCHESTRATION_BASE_URL.
LLM_ETP_GENERATION_BASE_URL: str = os.getenv("LLM_ETP_GENERATION_BASE_URL", "").strip().rstrip("/")

# Objeto + justificativa (dispensa / inexigibilidade via fill-tr-slots): gateway externo opcional.
LLM_CLAUSULAS_GENERATION_BASE_URL: str = os.getenv(
    "LLM_CLAUSULAS_GENERATION_BASE_URL", ""
).strip().rstrip("/")

_CLAUSULAS_PACKAGE_PREFIXES = ("dispensa_", "inexigibilidade_")

# Base URL do llm_agent (para gerar estrutura de documentos)
LLM_AGENT_BASE_URL: str = os.getenv(
    "LLM_AGENT_BASE_URL",
    "http://localhost:8003",
).rstrip("/")

LLM_ORCHESTRATION_GENERATE_PATH: str = os.getenv(
    "LLM_ORCHESTRATION_GENERATE_PATH",
    "/api/llm/generate",
)


def _is_etp_document_type(document_type: str | None) -> bool:
    d = (document_type or "").strip().lower()
    return "etp" in d or "estudo" in d or d == "estudo_tecnico_preliminar"


def is_clausulas_objeto_justificativa_package(slot_package_key: str | None) -> bool:
    """Pacotes de dispensa/inexigibilidade cujo objeto/justificativa podem ir ao gateway externo."""
    key = str(slot_package_key or "").strip().lower()
    return any(key.startswith(prefix) for prefix in _CLAUSULAS_PACKAGE_PREFIXES)


def llm_generation_base_url_for_clausulas(slot_package_key: str | None) -> str:
    """URL do POST /api/llm/generate para objeto/justificativa (Qwen quando configurado)."""
    if is_clausulas_objeto_justificativa_package(slot_package_key) and LLM_CLAUSULAS_GENERATION_BASE_URL:
        return LLM_CLAUSULAS_GENERATION_BASE_URL
    return LLM_ORCHESTRATION_BASE_URL


# Perfil de prompt para cláusulas: auto = rich no gateway cloud, lite no Ollama local.
LLM_CLAUSULAS_PROMPT_PROFILE: str = os.getenv("LLM_CLAUSULAS_PROMPT_PROFILE", "auto").strip().lower()
LLM_CLAUSULAS_CLOUD_MAX_TOKENS: int = _env_int("LLM_CLAUSULAS_CLOUD_MAX_TOKENS", 2048)


def clausulas_gateway_is_cloud(base_url: str | None = None) -> bool:
    """True quando objeto/justificativa não usa o llm_api/Ollama local."""
    url = (base_url or LLM_CLAUSULAS_GENERATION_BASE_URL or "").strip().rstrip("/")
    if not url:
        return False
    return url != LLM_ORCHESTRATION_BASE_URL.rstrip("/")


def clausulas_use_rich_prompt(base_url: str | None = None) -> bool:
    """Rich = redação mais completa (Qwen); lite = genérico/curto (Ollama local)."""
    profile = LLM_CLAUSULAS_PROMPT_PROFILE or "auto"
    if profile == "lite":
        return False
    if profile == "rich":
        return True
    return clausulas_gateway_is_cloud(base_url)


def llm_generation_base_url_for_document_type(document_type: str | None) -> str:
    """URL do POST /api/llm/generate conforme o tipo de documento (ETP opcionalmente via Qwen/outro gateway)."""
    if _is_etp_document_type(document_type) and LLM_ETP_GENERATION_BASE_URL:
        return LLM_ETP_GENERATION_BASE_URL
    return LLM_ORCHESTRATION_BASE_URL


# Ollama (para embeddings, quando usar localmente)
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Timeouts:
# - RAG_TIMEOUT controla o timeout padrão (em segundos) para chamadas HTTP usadas no RAG,
#   incluindo consultas ao PNCP. Valor maior é útil para ingestões em massa.
# - Por padrão, usamos 120s para evitar ReadTimeout frequentes em chamadas pesadas.
RAG_TIMEOUT: float = float(os.getenv("RAG_TIMEOUT", "300"))
RAG_HTTP_TIMEOUT: float | None = None if RAG_TIMEOUT <= 0 else RAG_TIMEOUT
EMBEDDING_TIMEOUT: float = float(os.getenv("EMBEDDING_TIMEOUT", "30.0"))

# Retrieval
RAG_TOP_K: int = _env_int("RAG_TOP_K", 5)

# Pós-processamento de cláusulas (1 = ativo, 0 = desativado para debug/comparação)
RAG_POSTPROCESS: bool = os.getenv("RAG_POSTPROCESS", "1").strip() not in ("0", "false", "False", "no")

# Sanitização via LLM: remove meta-comentários usando a IA (1 = ativo). Alternativa à lista manual de regex.
RAG_LLM_SANITIZE: bool = os.getenv("RAG_LLM_SANITIZE", "1").strip() not in ("0", "false", "False", "no")

# Text corrector microservice (pós-correção antes de montar DOCX)
TEXT_CORRECTOR_ENABLED: bool = os.getenv("TEXT_CORRECTOR_ENABLED", "1").strip() not in ("0", "false", "False", "no")
TEXT_CORRECTOR_BASE_URL: str = os.getenv("TEXT_CORRECTOR_BASE_URL", "http://text_corrector_service:8011").rstrip("/")
