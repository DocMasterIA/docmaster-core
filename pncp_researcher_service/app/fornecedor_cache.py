"""
Cache SQLite CNPJ → razão social (BrasilAPI) no índice local PNCP.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from .config import PNCP_BRASILAPI_CACHE_DAYS, PNCP_LOCAL_DB_PATH
from .supplier_resolver import cnpj_digits, normalize_cnpj, parse_brasilapi_to_fornecedor


def ensure_fornecedor_cache_table(cursor: sqlite3.Cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pncp_fornecedor_cache (
            cnpj_digits TEXT PRIMARY KEY,
            razao_social TEXT NOT NULL DEFAULT '',
            nome_fantasia TEXT NOT NULL DEFAULT '',
            cadastro_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL,
            fonte TEXT NOT NULL DEFAULT 'brasilapi'
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_pncp_forn_cache_updated ON pncp_fornecedor_cache(updated_at)"
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso_utc(value: str) -> Optional[datetime]:
    s = (value or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def cache_is_fresh(updated_at: str, *, max_age_days: Optional[int] = None) -> bool:
    days = PNCP_BRASILAPI_CACHE_DAYS if max_age_days is None else max_age_days
    if days <= 0:
        return True
    dt = _parse_iso_utc(updated_at)
    if dt is None:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt >= datetime.now(timezone.utc) - timedelta(days=days)


def cache_get(
    conn: sqlite3.Connection,
    cnpj_raw: str,
    *,
    max_age_days: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    d = cnpj_digits(cnpj_raw)
    if len(d) != 14:
        return None
    row = conn.execute(
        """
        SELECT cnpj_digits, razao_social, nome_fantasia, cadastro_json, updated_at, fonte
        FROM pncp_fornecedor_cache WHERE cnpj_digits = ?
        """,
        (d,),
    ).fetchone()
    if not row:
        return None
    if not cache_is_fresh(str(row["updated_at"] or ""), max_age_days=max_age_days):
        return None
    cad: Dict[str, Any] = {}
    try:
        cad = json.loads(row["cadastro_json"] or "{}")
    except (TypeError, json.JSONDecodeError):
        cad = {}
    return {
        "cnpj_digits": row["cnpj_digits"],
        "cnpj_fornecedor": normalize_cnpj(d),
        "fornecedor": str(row["razao_social"] or row["nome_fantasia"] or "").strip(),
        "razao_social": str(row["razao_social"] or "").strip(),
        "nome_fantasia": str(row["nome_fantasia"] or "").strip(),
        "fornecedor_cadastro": cad,
        "updated_at": row["updated_at"],
        "fonte": row["fonte"],
    }


def cache_upsert(
    conn: sqlite3.Connection,
    cnpj_raw: str,
    *,
    razao_social: str = "",
    nome_fantasia: str = "",
    cadastro: Optional[Dict[str, Any]] = None,
    fonte: str = "brasilapi",
) -> None:
    d = cnpj_digits(cnpj_raw)
    if len(d) != 14:
        return
    now = _utc_now_iso()
    cad_json = json.dumps(cadastro or {}, ensure_ascii=False)
    conn.execute(
        """
        INSERT INTO pncp_fornecedor_cache (
            cnpj_digits, razao_social, nome_fantasia, cadastro_json, updated_at, fonte
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(cnpj_digits) DO UPDATE SET
            razao_social=excluded.razao_social,
            nome_fantasia=excluded.nome_fantasia,
            cadastro_json=excluded.cadastro_json,
            updated_at=excluded.updated_at,
            fonte=excluded.fonte
        """,
        (
            d,
            str(razao_social or "").strip(),
            str(nome_fantasia or "").strip(),
            cad_json,
            now,
            str(fonte or "brasilapi").strip() or "brasilapi",
        ),
    )


def cache_upsert_from_brasilapi_payload(
    conn: sqlite3.Connection,
    cnpj_raw: str,
    payload: Dict[str, Any],
) -> Tuple[str, Dict[str, Any]]:
    d = cnpj_digits(cnpj_raw)
    nome, cad = parse_brasilapi_to_fornecedor(payload, cnpj_digits_val=d)
    razao = str(payload.get("razao_social") or "").strip()
    fantasia = str(payload.get("nome_fantasia") or "").strip()
    cache_upsert(
        conn,
        d,
        razao_social=razao or nome,
        nome_fantasia=fantasia,
        cadastro=cad,
        fonte="brasilapi",
    )
    return nome, cad


def cache_stats(conn: sqlite3.Connection) -> Dict[str, Any]:
    row = conn.execute("SELECT COUNT(*) AS n FROM pncp_fornecedor_cache").fetchone()
    return {
        "cache_fornecedor_total": int(row["n"] if row else 0),
        "cache_db_path": PNCP_LOCAL_DB_PATH,
    }
