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


PNCP_BASE_URL: str = os.getenv("PNCP_BASE_URL", "https://pncp.gov.br/api/consulta").rstrip("/")
# API de compras/itens/arquivos (diferente da API de consulta por publicação).
PNCP_PNCP_API_BASE_URL: str = os.getenv("PNCP_PNCP_API_BASE_URL", "https://pncp.gov.br/pncp-api").rstrip("/")
PNCP_TIMEOUT: float | None = _env_timeout("PNCP_TIMEOUT", 120.0)
PNCP_DEFAULT_LOOKBACK_DAYS: int = _env_int("PNCP_DEFAULT_LOOKBACK_DAYS", 180)
PNCP_MAX_RETRIES: int = _env_int("PNCP_MAX_RETRIES", 4)
PNCP_RETRY_BACKOFF_SECONDS: float = float(os.getenv("PNCP_RETRY_BACKOFF_SECONDS", "1.5"))
# Espaço mínimo entre cada GET ao PNCP (reduz 429 por rajada).
PNCP_MIN_REQUEST_INTERVAL_SECONDS: float = float(os.getenv("PNCP_MIN_REQUEST_INTERVAL_SECONDS", "0.25"))
# Tentativas extras além de PNCP_MAX_RETRIES quando resposta for 429/503.
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
PNCP_ITEM_LOOKUP_PER_PAGE: int = _env_int("PNCP_ITEM_LOOKUP_PER_PAGE", 30)
PNCP_ITEM_LOOKUP_CONCURRENCY: int = _env_int("PNCP_ITEM_LOOKUP_CONCURRENCY", 3)
# Timeout específico do lookup de itens (evita travar o stream quando PNCP está lento).
PNCP_ITEM_LOOKUP_TIMEOUT_SECONDS: float = float(os.getenv("PNCP_ITEM_LOOKUP_TIMEOUT_SECONDS", "8"))
# Orçamento máximo de tempo por página para lookup de itens.
PNCP_ITEM_LOOKUP_MAX_SECONDS_PER_PAGE: float = float(os.getenv("PNCP_ITEM_LOOKUP_MAX_SECONDS_PER_PAGE", "6"))
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
