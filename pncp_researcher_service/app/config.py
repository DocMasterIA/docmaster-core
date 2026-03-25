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


PNCP_BASE_URL: str = os.getenv("PNCP_BASE_URL", "https://pncp.gov.br/api/consulta").rstrip("/")
PNCP_TIMEOUT: float = float(os.getenv("PNCP_TIMEOUT", "60"))
PNCP_DEFAULT_LOOKBACK_DAYS: int = _env_int("PNCP_DEFAULT_LOOKBACK_DAYS", 180)
