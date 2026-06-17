"""Cache persistente de e-mail por CNPJ (ReceitaWS/cnpj.ws omitem na BrasilAPI)."""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

_CACHE_LOCK = threading.Lock()
_CACHE_TTL_SEC = 60 * 60 * 24 * 90  # 90 dias
_HTTP_UA = "DocMaster-PNCP/1.0"


def _cnpj_digits(raw: str) -> str:
    return re.sub(r"\D", "", str(raw or ""))


def _cache_path() -> Path:
    root = Path(getattr(settings, "MEDIA_ROOT", "/tmp") or "/tmp")
    root.mkdir(parents=True, exist_ok=True)
    return root / "pncp_cnpj_email_cache.json"


def _load_cache() -> Dict[str, Dict[str, Any]]:
    path = _cache_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _save_cache(data: Dict[str, Dict[str, Any]]) -> None:
    path = _cache_path()
    try:
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        logger.warning("falha ao gravar cache e-mail CNPJ: %s", exc)


def get_cached_cnpj_email(cnpj_formatted: str) -> str:
    d = _cnpj_digits(cnpj_formatted)
    if len(d) != 14:
        return ""
    with _CACHE_LOCK:
        row = _load_cache().get(d)
    if not isinstance(row, dict):
        return ""
    em = str(row.get("email") or "").strip()
    if "@" not in em:
        return ""
    ts = float(row.get("ts") or 0)
    if ts and (time.time() - ts) > _CACHE_TTL_SEC:
        return ""
    return em


def set_cached_cnpj_email(cnpj_formatted: str, email: str, *, fonte: str = "") -> None:
    d = _cnpj_digits(cnpj_formatted)
    em = str(email or "").strip()
    if len(d) != 14 or "@" not in em:
        return
    with _CACHE_LOCK:
        data = _load_cache()
        data[d] = {"email": em, "ts": time.time(), "fonte": str(fonte or "").strip()[:32]}
        _save_cache(data)
