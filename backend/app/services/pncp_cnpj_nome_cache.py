"""Cache persistente de razão social por CNPJ (BrasilAPI / cnpj.ws)."""
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
_FONTE_SEM_NOME = "sem_nome"


def _cnpj_digits(raw: str) -> str:
    return re.sub(r"\D", "", str(raw or ""))


def _cache_path() -> Path:
    root = Path(getattr(settings, "MEDIA_ROOT", "/tmp") or "/tmp")
    root.mkdir(parents=True, exist_ok=True)
    return root / "pncp_cnpj_nome_cache.json"


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
        logger.warning("falha ao gravar cache nome CNPJ: %s", exc)


def _row_valid(row: Any) -> bool:
    if not isinstance(row, dict):
        return False
    ts = float(row.get("ts") or 0)
    if not ts:
        return False
    return (time.time() - ts) <= _CACHE_TTL_SEC


def get_cached_cnpj_nome(cnpj_formatted: str) -> str:
    d = _cnpj_digits(cnpj_formatted)
    if len(d) != 14:
        return ""
    with _CACHE_LOCK:
        row = _load_cache().get(d)
    if not _row_valid(row):
        return ""
    if str(row.get("fonte") or "").strip() == _FONTE_SEM_NOME:
        return ""
    return str(row.get("razao_social") or row.get("nome") or "").strip()


def get_cached_cnpj_cadastro(cnpj_formatted: str) -> Dict[str, Any]:
    d = _cnpj_digits(cnpj_formatted)
    if len(d) != 14:
        return {}
    with _CACHE_LOCK:
        row = _load_cache().get(d)
    if not _row_valid(row):
        return {}
    if str(row.get("fonte") or "").strip() == _FONTE_SEM_NOME:
        return {}
    cad = row.get("cadastro")
    if isinstance(cad, dict) and cad:
        return dict(cad)
    nome = str(row.get("razao_social") or "").strip()
    if nome:
        return {"razao_social": nome, "cnpj": d}
    return {}


def set_cached_cnpj_nome(
    cnpj_formatted: str,
    nome: str,
    *,
    cadastro: Optional[Dict[str, Any]] = None,
    fonte: str = "",
) -> None:
    d = _cnpj_digits(cnpj_formatted)
    nm = str(nome or "").strip()
    if len(d) != 14 or len(nm) < 3:
        return
    cad = dict(cadastro) if isinstance(cadastro, dict) else {}
    if nm and not cad.get("razao_social"):
        cad["razao_social"] = nm
    with _CACHE_LOCK:
        data = _load_cache()
        data[d] = {
            "razao_social": nm,
            "cadastro": cad,
            "ts": time.time(),
            "fonte": str(fonte or "").strip()[:32],
        }
        _save_cache(data)


def set_cached_cnpj_sem_nome(cnpj_formatted: str) -> None:
    d = _cnpj_digits(cnpj_formatted)
    if len(d) != 14:
        return
    with _CACHE_LOCK:
        data = _load_cache()
        data[d] = {"razao_social": "", "ts": time.time(), "fonte": _FONTE_SEM_NOME}
        _save_cache(data)
