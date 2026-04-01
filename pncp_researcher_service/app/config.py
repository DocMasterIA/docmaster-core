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
PNCP_TIMEOUT: float | None = _env_timeout("PNCP_TIMEOUT", 120.0)
PNCP_DEFAULT_LOOKBACK_DAYS: int = _env_int("PNCP_DEFAULT_LOOKBACK_DAYS", 180)
PNCP_MAX_RETRIES: int = _env_int("PNCP_MAX_RETRIES", 4)
PNCP_RETRY_BACKOFF_SECONDS: float = float(os.getenv("PNCP_RETRY_BACKOFF_SECONDS", "1.5"))


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
