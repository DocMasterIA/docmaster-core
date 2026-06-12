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
# Janela de ingestão em dias (default 365 = teto da API PNCP por request).
PNCP_LOCAL_BACKFILL_DAYS: int = _env_int("PNCP_LOCAL_BACKFILL_DAYS", 365)

# Fila de ingestão em 2 fases (catálogo → itens).
PNCP_INGEST_QUEUE_ENABLED: bool = _env_bool("PNCP_INGEST_QUEUE_ENABLED", True)
PNCP_INGEST_WORKER_ENABLED: bool = _env_bool("PNCP_INGEST_WORKER_ENABLED", True)
PNCP_INGEST_WORKER_POLL_SECONDS: float = float(
    os.getenv("PNCP_INGEST_WORKER_POLL_SECONDS", "2")
)
PNCP_INGEST_WORKER_CATALOG_BATCH: int = _env_int("PNCP_INGEST_WORKER_CATALOG_BATCH", 6)
PNCP_INGEST_WORKER_ITEMS_BATCH: int = _env_int("PNCP_INGEST_WORKER_ITEMS_BATCH", 32)
PNCP_INGEST_WORKER_ITEMS_CONCURRENCY: int = _env_int("PNCP_INGEST_WORKER_ITEMS_CONCURRENCY", 10)
# Timeout por tarefa HTTP no worker — evita batch preso 20+ min numa chamada PNCP.
PNCP_INGEST_TASK_TIMEOUT_SECONDS: float = float(
    os.getenv("PNCP_INGEST_TASK_TIMEOUT_SECONDS", "180")
)
# Timeout por página de catálogo (menor que itens — evita batch 480s estourar).
PNCP_INGEST_CATALOG_TASK_TIMEOUT_SECONDS: float = float(
    os.getenv("PNCP_INGEST_CATALOG_TASK_TIMEOUT_SECONDS", "90")
)
# Teto de duração do batch; ao estourar, requeue processing e segue o loop.
PNCP_INGEST_BATCH_MAX_SECONDS: float = float(
    os.getenv("PNCP_INGEST_BATCH_MAX_SECONDS", "480")
)
PNCP_INGEST_QUEUE_MAX_ATTEMPTS: int = _env_int("PNCP_INGEST_QUEUE_MAX_ATTEMPTS", 5)
# Planner não enfileira catálogo se pending >= este valor (drena antes de inchando).
PNCP_INGEST_QUEUE_MAX_PENDING: int = _env_int("PNCP_INGEST_QUEUE_MAX_PENDING", 12000)
# Com fila de itens acima deste valor, worker/planner pausam catálogo (só drena itens).
PNCP_INGEST_ITEMS_BACKLOG_PAUSE_CATALOG: int = _env_int(
    "PNCP_INGEST_ITEMS_BACKLOG_PAUSE_CATALOG", 3000
)
# Boost opcional do batch de itens quando há backlog alto.
PNCP_INGEST_WORKER_ITEMS_BATCH_MAX: int = _env_int(
    "PNCP_INGEST_WORKER_ITEMS_BATCH_MAX", 48
)
PNCP_INGEST_PLANNER_INTERVAL_SECONDS: int = _env_int(
    "PNCP_INGEST_PLANNER_INTERVAL_SECONDS", 300
)
PNCP_INGEST_PLANNER_PAGES_PER_SCOPE: int = _env_int(
    "PNCP_INGEST_PLANNER_PAGES_PER_SCOPE", 8
)
PNCP_INGEST_PLANNER_CONTRACTS_WITHOUT_ITEMS: int = _env_int(
    "PNCP_INGEST_PLANNER_CONTRACTS_WITHOUT_ITEMS", 400
)
# Quando a fila de itens está baixa, o planner/worker enfileiram até este teto por rodada.
PNCP_INGEST_PLANNER_CONTRACTS_WITHOUT_ITEMS_MAX: int = _env_int(
    "PNCP_INGEST_PLANNER_CONTRACTS_WITHOUT_ITEMS_MAX", 1200
)
# Abaixo deste backlog de itens, prioriza encher contract_items e reduz catálogo.
PNCP_INGEST_ITEMS_STARVE_BACKLOG: int = _env_int("PNCP_INGEST_ITEMS_STARVE_BACKLOG", 150)
# Com muitas páginas de catálogo pending e poucos itens na fila, pausa catálogo (anti-trava).
PNCP_INGEST_CATALOG_HEAVY_PENDING: int = _env_int("PNCP_INGEST_CATALOG_HEAVY_PENDING", 300)
# Só pausa catálogo por starve/heavy se gap SQLite >= este valor; senão reabre catálogo p/ descobrir contratos.
PNCP_INGEST_CATALOG_PAUSE_MIN_GAP: int = _env_int("PNCP_INGEST_CATALOG_PAUSE_MIN_GAP", 50)
# Sem items_ok por N segundos enquanto há trabalho de itens → stall recovery (não confundir com catalog_ok).
PNCP_INGEST_ITEMS_STALL_SECONDS: int = _env_int("PNCP_INGEST_ITEMS_STALL_SECONDS", 600)
# Retentativas extras quando o corpo da resposta não é JSON válido.
PNCP_INGEST_JSON_INVALID_RETRIES: int = _env_int("PNCP_INGEST_JSON_INVALID_RETRIES", 3)
PNCP_INGEST_JSON_INVALID_RETRY_SECONDS: float = float(
    os.getenv("PNCP_INGEST_JSON_INVALID_RETRY_SECONDS", "2")
)
# Se > 0, não refaz GET /itens se o contrato já tem itens buscados há menos de N dias (0 = sempre busca).
PNCP_INGEST_ITEMS_REFRESH_DAYS: int = _env_int("PNCP_INGEST_ITEMS_REFRESH_DAYS", 7)
# Modo backfill: pipeline cheio, refresh=0 efetivo, backpressure relaxada (365d × UFs × modalidades).
PNCP_INGEST_BACKFILL_MODE: bool = _env_bool("PNCP_INGEST_BACKFILL_MODE", False)
PNCP_INGEST_BACKFILL_TARGET_BACKLOG: int = _env_int(
    "PNCP_INGEST_BACKFILL_TARGET_BACKLOG", 10000
)
PNCP_INGEST_BACKFILL_TOPUP_CHUNK: int = _env_int("PNCP_INGEST_BACKFILL_TOPUP_CHUNK", 5000)
PNCP_INGEST_BACKFILL_ITEMS_FIRST_BACKLOG: int = _env_int(
    "PNCP_INGEST_BACKFILL_ITEMS_FIRST_BACKLOG", 1000
)
PNCP_INGEST_BACKFILL_LOW_ROWS_1H_ALERT: int = _env_int(
    "PNCP_INGEST_BACKFILL_LOW_ROWS_1H_ALERT", 2000
)
PNCP_INGEST_BACKFILL_LOW_ROWS_ALERT_SECONDS: int = _env_int(
    "PNCP_INGEST_BACKFILL_LOW_ROWS_ALERT_SECONDS", 7200
)
# GET /resultados por item homologado (valorUnitarioHomologado) durante ingest.
PNCP_INGEST_FETCH_ITEM_RESULTADOS: bool = _env_bool("PNCP_INGEST_FETCH_ITEM_RESULTADOS", True)


def is_ingest_backfill_mode() -> bool:
    return bool(PNCP_INGEST_BACKFILL_MODE)


def effective_items_refresh_days() -> int:
    if is_ingest_backfill_mode():
        return 0
    return max(0, int(PNCP_INGEST_ITEMS_REFRESH_DAYS or 0))


def effective_items_starve_backlog() -> int:
    if is_ingest_backfill_mode():
        return max(1, int(PNCP_INGEST_BACKFILL_TARGET_BACKLOG))
    return max(0, int(PNCP_INGEST_ITEMS_STARVE_BACKLOG))


def effective_backlog_pause_catalog() -> int:
    return max(0, int(PNCP_INGEST_ITEMS_BACKLOG_PAUSE_CATALOG))


# UFs varridas pelo planejador (mesma ordem do loop bash).
PNCP_UFS_DEFAULT: list[str] = _env_str_list(
    "PNCP_UFS_DEFAULT",
    [
        "AC",
        "AL",
        "AP",
        "AM",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MT",
        "MS",
        "MG",
        "PA",
        "PB",
        "PR",
        "PE",
        "PI",
        "RJ",
        "RN",
        "RS",
        "RO",
        "RR",
        "SC",
        "SP",
        "SE",
        "TO",
    ],
)
# Timeout por contratação no backfill (evita travar a ingestão num único GET de itens).
PNCP_BACKFILL_ITEM_TIMEOUT_SECONDS: float = float(
    os.getenv("PNCP_BACKFILL_ITEM_TIMEOUT_SECONDS", "45")
)
# GET de itens em paralelo por página no backfill (constância + rapidez).
PNCP_BACKFILL_ITEM_CONCURRENCY: int = _env_int("PNCP_BACKFILL_ITEM_CONCURRENCY", 12)
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
# Retoma backfill a partir de last_page+1 (pncp_ingest_state) — cobertura profunda 24/7.
PNCP_INGEST_WATERMARK_RESUME: bool = _env_bool("PNCP_INGEST_WATERMARK_RESUME", True)

# Autocura 24/7: requeue processing, scopes expirados, retry de dead (sem ops manual).
PNCP_INGEST_SELF_HEAL_ENABLED: bool = _env_bool("PNCP_INGEST_SELF_HEAL_ENABLED", True)
PNCP_INGEST_SELF_HEAL_INTERVAL_SECONDS: int = _env_int(
    "PNCP_INGEST_SELF_HEAL_INTERVAL_SECONDS", 300
)
PNCP_INGEST_PROCESSING_STALE_SECONDS: int = _env_int(
    "PNCP_INGEST_PROCESSING_STALE_SECONDS", 900
)
PNCP_INGEST_DEAD_REVIVE_BATCH: int = _env_int("PNCP_INGEST_DEAD_REVIVE_BATCH", 200)
PNCP_INGEST_DEAD_REVIVE_MIN_AGE_SECONDS: int = _env_int(
    "PNCP_INGEST_DEAD_REVIVE_MIN_AGE_SECONDS", 3600
)
# Detecção de parada: fila com trabalho sem progresso → autocura + replanejamento automático.
PNCP_INGEST_STALL_RECOVERY_ENABLED: bool = _env_bool("PNCP_INGEST_STALL_RECOVERY_ENABLED", True)
PNCP_INGEST_STALL_SECONDS: int = _env_int("PNCP_INGEST_STALL_SECONDS", 900)
PNCP_INGEST_STALL_MIN_PENDING: int = _env_int("PNCP_INGEST_STALL_MIN_PENDING", 100)
PNCP_INGEST_HEARTBEAT_LOG_SECONDS: int = _env_int("PNCP_INGEST_HEARTBEAT_LOG_SECONDS", 300)

# Busca local FTS5 (pncp_itens_fts) — fallback LIKE se desativado ou índice vazio.
PNCP_FTS5_ENABLED: bool = _env_bool("PNCP_FTS5_ENABLED", True)

# Busca híbrida: complemento via PNCP ao vivo quando o índice local retorna poucos itens.
PNCP_HYBRID_FALLBACK_ENABLED: bool = _env_bool("PNCP_HYBRID_FALLBACK_ENABLED", True)
PNCP_HYBRID_MIN_LOCAL_RESULTS: int = _env_int("PNCP_HYBRID_MIN_LOCAL_RESULTS", 8)
PNCP_HYBRID_MAX_LIVE_PAGES: int = _env_int("PNCP_HYBRID_MAX_LIVE_PAGES", 6)

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

# Cobertura de fornecedor vencedor (Fase A+): elegibilidade e cache BrasilAPI.
PNCP_SUPPLIER_ELIGIBLE_SITUATIONS: list[str] = _env_str_list(
    "PNCP_SUPPLIER_ELIGIBLE_SITUATIONS",
    ["homolog", "adjudic", "encerr"],
)
PNCP_SUPPLIER_SKIP_SITUATIONS: list[str] = _env_str_list(
    "PNCP_SUPPLIER_SKIP_SITUATIONS",
    ["revog", "anul", "cancel"],
)
PNCP_BRASILAPI_CACHE_DAYS: int = _env_int("PNCP_BRASILAPI_CACHE_DAYS", 90)

# Busca de preços: só itens homologados/adjudicados (exclui «Em andamento» sem vencedor publicado).
PNCP_SEARCH_ONLY_HOMOLOGATED: bool = _env_bool("PNCP_SEARCH_ONLY_HOMOLOGATED", True)
# Após filtrar, consulta PNCP/BrasilAPI nos primeiros N homologados sem CNPJ no índice.
PNCP_SEARCH_ENRICH_HOMOLOG_MAX: int = _env_int("PNCP_SEARCH_ENRICH_HOMOLOG_MAX", 16)
# Limite SQL no índice local quando busca_lote=true (evita varrer 100k linhas por item).
PNCP_BULK_SEARCH_SQL_LIMIT: int = _env_int("PNCP_BULK_SEARCH_SQL_LIMIT", 200)
# Score mínimo (0–100) para considerar item aderente na busca inteligente (antes ~60–70 implícito).
PNCP_SEARCH_MIN_SCORE_APROVACAO: int = _env_int("PNCP_SEARCH_MIN_SCORE_APROVACAO", 50)
# Descrições de cotação: até N tokens usam busca completa; acima disso cap de âncoras (recall).
PNCP_SEARCH_ANCHOR_FULL_TERM_MAX: int = _env_int("PNCP_SEARCH_ANCHOR_FULL_TERM_MAX", 5)
PNCP_SEARCH_ANCHOR_MAX_GROUPS: int = _env_int("PNCP_SEARCH_ANCHOR_MAX_GROUPS", 8)

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
