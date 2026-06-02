from __future__ import annotations

import os


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_timeout(key: str, default: float) -> float | None:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        v = float(raw)
    except ValueError:
        return default
    # Convenção: 0 ou negativo = sem timeout
    if v <= 0:
        return None
    return v


def _env_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _env_str_list(key: str, default: list[str]) -> list[str]:
    raw = (os.getenv(key) or "").strip()
    if not raw:
        return default
    out: list[str] = []
    for chunk in raw.split(","):
        c = chunk.strip()
        if c:
            out.append(c)
    return out or default


PNCP_BASE_URL: str = os.getenv("PNCP_BASE_URL", "https://pncp.gov.br/api/consulta").rstrip("/")
# API de compras/itens/arquivos (diferente da API de consulta por publicação).
PNCP_PNCP_API_BASE_URL: str = os.getenv("PNCP_PNCP_API_BASE_URL", "https://pncp.gov.br/pncp-api").rstrip("/")
PNCP_TIMEOUT: float | None = _env_timeout("PNCP_TIMEOUT", 120.0)
PNCP_DEFAULT_LOOKBACK_DAYS: int = _env_int("PNCP_DEFAULT_LOOKBACK_DAYS", 180)
# Teto por requisição para max_paginas (varredura PNCP); aumentar eleva carga e risco de 429.
PNCP_MAX_PAGINAS_PER_REQUEST: int = _env_int("PNCP_MAX_PAGINAS_PER_REQUEST", 120)
PNCP_MAX_RETRIES: int = _env_int("PNCP_MAX_RETRIES", 4)
PNCP_RETRY_BACKOFF_SECONDS: float = float(os.getenv("PNCP_RETRY_BACKOFF_SECONDS", "1.5"))
# Limite de taxa: bucket (rajadas paralelas) | interval (1 GET por intervalo) | off (sem pace; mais 429).
PNCP_THROTTLE_MODE: str = (os.getenv("PNCP_THROTTLE_MODE", "bucket") or "bucket").strip().lower()
# Modo bucket: burst inicial + recarga contínua (melhor que interval fixo com async paralelo).
PNCP_BUCKET_CAPACITY: float = float(os.getenv("PNCP_BUCKET_CAPACITY", "16"))
PNCP_BUCKET_REFILL_PER_SEC: float = float(os.getenv("PNCP_BUCKET_REFILL_PER_SEC", "24"))
# Modo interval: espaço mínimo entre cada GET (legado; serializa demais com muitas tasks).
PNCP_MIN_REQUEST_INTERVAL_SECONDS: float = float(os.getenv("PNCP_MIN_REQUEST_INTERVAL_SECONDS", "0.12"))
# Tentativas extras além de PNCP_MAX_RETRIES quando resposta for 429/502/503/504.
PNCP_RATE_LIMIT_EXTRA_ATTEMPTS: int = _env_int("PNCP_RATE_LIMIT_EXTRA_ATTEMPTS", 6)
# Teto de espera por tentativa em caso de rate limit (segundos).
PNCP_RATE_LIMIT_BACKOFF_CAP_SECONDS: float = float(os.getenv("PNCP_RATE_LIMIT_BACKOFF_CAP_SECONDS", "90"))


def _env_int_list(key: str, default: list[int]) -> list[int]:
    raw = (os.getenv(key) or "").strip()
    if not raw:
        return default
    out: list[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            out.append(int(chunk))
        except ValueError:
            continue
    return out or default


# Quando codigo_modalidade não vier no payload, varre estas modalidades.
PNCP_MODALIDADES_DEFAULT: list[int] = _env_int_list(
    "PNCP_MODALIDADES_DEFAULT",
    [8, 6, 7, 9, 10],
)

# Busca em tabela de itens (detalhamento) para aumentar precisão de termo.
PNCP_ENABLE_ITEM_TABLE_LOOKUP: bool = os.getenv("PNCP_ENABLE_ITEM_TABLE_LOOKUP", "true").strip().lower() in {"1", "true", "yes", "on"}
PNCP_ITEM_LOOKUP_PER_PAGE: int = _env_int("PNCP_ITEM_LOOKUP_PER_PAGE", 50)
PNCP_ITEM_LOOKUP_CONCURRENCY: int = _env_int("PNCP_ITEM_LOOKUP_CONCURRENCY", 12)
# Timeout específico do lookup de itens (evita travar o stream quando PNCP está lento).
PNCP_ITEM_LOOKUP_TIMEOUT_SECONDS: float = float(os.getenv("PNCP_ITEM_LOOKUP_TIMEOUT_SECONDS", "8"))
# Orçamento máximo de tempo por página para lookup de itens.
PNCP_ITEM_LOOKUP_MAX_SECONDS_PER_PAGE: float = float(os.getenv("PNCP_ITEM_LOOKUP_MAX_SECONDS_PER_PAGE", "12"))
# Sempre chama GET itens (objeto + tabela); false = só quando objeto não casa (menos 429).
PNCP_FETCH_ITEMS_ALWAYS: bool = os.getenv("PNCP_FETCH_ITEMS_ALWAYS", "true").strip().lower() in {"1", "true", "yes", "on"}
# Máx. linhas devolvidas em itens_pncp_destaque (match por linha).
PNCP_ITEM_ROWS_MAX_DESTAQUE: int = _env_int("PNCP_ITEM_ROWS_MAX_DESTAQUE", 25)
# Quando só o objeto casa, quantas linhas da tabela enviar como amostra (valores/descrições).
PNCP_ITEM_AMOSTRA_LINHAS: int = _env_int("PNCP_ITEM_AMOSTRA_LINHAS", 12)
# Se a API de itens devolver linhas, exige que o termo apareça na tabela (não só no objeto).
# Evita falso positivo (ex.: bicos "para encher pneus" quando se busca compra de pneus).
PNCP_REQUIRE_TABLE_MATCH_WHEN_ITENS_EXIST: bool = os.getenv(
    "PNCP_REQUIRE_TABLE_MATCH_WHEN_ITENS_EXIST", "true"
).strip().lower() in {"1", "true", "yes", "on"}

# Índice local PNCP (SQLite) para reduzir dependência de chamadas externas.
# Padrão = volume Docker em docker-compose.pncp.yml (/data/pncp). Evita 2º .db em /tmp no container.
PNCP_LOCAL_DB_PATH: str = os.getenv(
    "PNCP_LOCAL_DB_PATH",
    "/data/pncp/pncp_researcher_local.db",
).strip()
PNCP_LOCAL_AUTO_INGEST: bool = os.getenv(
    "PNCP_LOCAL_AUTO_INGEST", "true"
).strip().lower() in {"1", "true", "yes", "on"}
PNCP_LOCAL_BACKFILL_MONTHS: int = _env_int("PNCP_LOCAL_BACKFILL_MONTHS", 12)
# Timeout por contratação no backfill (evita travar a ingestão num único GET de itens).
PNCP_BACKFILL_ITEM_TIMEOUT_SECONDS: float = float(
    os.getenv("PNCP_BACKFILL_ITEM_TIMEOUT_SECONDS", "45")
)
PNCP_LOCAL_INCLUDE_ITEMS: bool = os.getenv(
    "PNCP_LOCAL_INCLUDE_ITEMS", "true"
).strip().lower() in {"1", "true", "yes", "on"}

# Ingestão resiliente PNCP (auto-pause ao detectar bloqueio/rate limit/timeout).
PNCP_INGEST_AUTOPAUSE_ENABLED: bool = _env_bool("PNCP_INGEST_AUTOPAUSE_ENABLED", True)
PNCP_INGEST_AUTOPAUSE_BASE_SECONDS: int = _env_int("PNCP_INGEST_AUTOPAUSE_BASE_SECONDS", 180)
PNCP_INGEST_AUTOPAUSE_MAX_SECONDS: int = _env_int("PNCP_INGEST_AUTOPAUSE_MAX_SECONDS", 1800)
PNCP_INGEST_AUTOPAUSE_JSON_INVALID_SECONDS: int = _env_int(
    "PNCP_INGEST_AUTOPAUSE_JSON_INVALID_SECONDS", 120
)

# Busca local FTS5 (pncp_itens_fts) — fallback LIKE se desativado ou índice vazio.
PNCP_FTS5_ENABLED: bool = _env_bool("PNCP_FTS5_ENABLED", True)

# Busca híbrida: complemento via PNCP ao vivo quando o índice local retorna poucos itens.
PNCP_HYBRID_FALLBACK_ENABLED: bool = _env_bool("PNCP_HYBRID_FALLBACK_ENABLED", True)
PNCP_HYBRID_MIN_LOCAL_RESULTS: int = _env_int("PNCP_HYBRID_MIN_LOCAL_RESULTS", 8)
PNCP_HYBRID_MAX_LIVE_PAGES: int = _env_int("PNCP_HYBRID_MAX_LIVE_PAGES", 4)

# Re-ranking leve com LLM para escolher os 3 melhores itens.
PNCP_IA_RERANK_ENABLED: bool = _env_bool("PNCP_IA_RERANK_ENABLED", True)
PNCP_IA_BASE_URL: str = os.getenv("PNCP_IA_BASE_URL", "http://llm_api:8002").rstrip("/")
PNCP_IA_GENERATE_PATH: str = os.getenv("PNCP_IA_GENERATE_PATH", "/api/llm/generate")
PNCP_IA_MODEL: str = os.getenv("PNCP_IA_MODEL", "").strip()
PNCP_IA_TIMEOUT_SECONDS: float = float(os.getenv("PNCP_IA_TIMEOUT_SECONDS", "4.5"))
PNCP_IA_MAX_CANDIDATES: int = _env_int("PNCP_IA_MAX_CANDIDATES", 36)

# Resumo curto (1–2 frases) do núcleo do item PNCP para títulos ambíguos / descrições longas.
PNCP_IA_ITEM_RESUMO_ENABLED: bool = _env_bool("PNCP_IA_ITEM_RESUMO_ENABLED", True)
PNCP_IA_ITEM_RESUMO_TIMEOUT_SECONDS: float = float(os.getenv("PNCP_IA_ITEM_RESUMO_TIMEOUT_SECONDS", "3.5"))

# Bloqueio de itens ligados à prestação de serviço/locação no resultado de busca.
PNCP_BLOCK_SERVICE_ITEMS: bool = _env_bool("PNCP_BLOCK_SERVICE_ITEMS", True)
PNCP_SERVICE_BLOCK_TERMS: list[str] = _env_str_list(
    "PNCP_SERVICE_BLOCK_TERMS",
    [
        "servico",
        "servicos",
        "prestacao de servico",
        "prestacao de servicos",
        "aluguel",
        "locacao",
        "manutencao",
        "instalacao",
        "montagem",
        "desmontagem",
        "terceirizacao",
        "consultoria",
        "assessoria",
    ],
)
