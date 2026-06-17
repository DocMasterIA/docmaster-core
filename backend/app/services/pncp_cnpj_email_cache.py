"""Cache persistente de e-mail por CNPJ (ReceitaWS/cnpj.ws omitem na BrasilAPI)."""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

_CACHE_LOCK = threading.Lock()
_CACHE_TTL_SEC = 60 * 60 * 24 * 90  # 90 dias
_NEGATIVE_TTL_SEC = 60 * 60 * 24 * 14  # 14 dias — RF/API sem e-mail
_FONTE_SEM_EMAIL = "sem_email"


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


def _row_ttl_sec(row: Dict[str, Any]) -> float:
    if str(row.get("fonte") or "").strip() == _FONTE_SEM_EMAIL:
        return _NEGATIVE_TTL_SEC
    return _CACHE_TTL_SEC


def _row_valid(row: Any) -> bool:
    if not isinstance(row, dict):
        return False
    ts = float(row.get("ts") or 0)
    if not ts:
        return False
    return (time.time() - ts) <= _row_ttl_sec(row)


def get_cached_cnpj_email(cnpj_formatted: str) -> str:
    d = _cnpj_digits(cnpj_formatted)
    if len(d) != 14:
        return ""
    with _CACHE_LOCK:
        row = _load_cache().get(d)
    if not _row_valid(row):
        return ""
    em = str(row.get("email") or "").strip()
    if str(row.get("fonte") or "").strip() == _FONTE_SEM_EMAIL:
        return ""
    if "@" not in em:
        return ""
    return em


def is_cnpj_email_negative_cached(cnpj_formatted: str) -> bool:
    d = _cnpj_digits(cnpj_formatted)
    if len(d) != 14:
        return False
    with _CACHE_LOCK:
        row = _load_cache().get(d)
    if not _row_valid(row):
        return False
    return str(row.get("fonte") or "").strip() == _FONTE_SEM_EMAIL


def get_cached_cnpj_emails_bulk(cnpj_digits_list: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for raw in cnpj_digits_list:
        d = _cnpj_digits(raw)
        if len(d) != 14:
            continue
        em = get_cached_cnpj_email(d)
        if em:
            out[d] = em
    return out


def set_cached_cnpj_email(cnpj_formatted: str, email: str, *, fonte: str = "") -> None:
    d = _cnpj_digits(cnpj_formatted)
    em = str(email or "").strip()
    if len(d) != 14 or "@" not in em:
        return
    with _CACHE_LOCK:
        data = _load_cache()
        data[d] = {"email": em, "ts": time.time(), "fonte": str(fonte or "").strip()[:32]}
        _save_cache(data)


def set_cached_cnpj_sem_email(cnpj_formatted: str) -> None:
    d = _cnpj_digits(cnpj_formatted)
    if len(d) != 14:
        return
    with _CACHE_LOCK:
        data = _load_cache()
        data[d] = {"email": "", "ts": time.time(), "fonte": _FONTE_SEM_EMAIL}
        _save_cache(data)
