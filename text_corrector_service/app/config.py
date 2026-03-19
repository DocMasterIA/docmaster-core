from __future__ import annotations

import os


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


LANGUAGETOOL_BASE_URL: str = os.getenv(
    "LANGUAGETOOL_BASE_URL",
    "http://languagetool:8010",
).rstrip("/")

LANGUAGETOOL_CHECK_PATH: str = os.getenv("LANGUAGETOOL_CHECK_PATH", "/v2/check")

CORRECTOR_HTTP_TIMEOUT: float = _env_float("CORRECTOR_HTTP_TIMEOUT", 20.0)
