from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .connection import platform_conn
from .registry import crosslink_db_path


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_crosslink_db(db_path: Optional[str] = None) -> str:
    """Banco central de identificadores cruzados entre plataformas."""
    path = (db_path or crosslink_db_path()).strip()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with platform_conn(path) as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS price_cross_refs (
                canonical_key TEXT NOT NULL,
                plataforma TEXT NOT NULL,
                plataforma_item_id TEXT NOT NULL,
                numero_pncp TEXT,
                numero_item TEXT,
                numero_processo TEXT,
                cnpj_fornecedor TEXT,
                valor_bucket INTEGER,
                desc_norm TEXT,
                metodo TEXT NOT NULL DEFAULT 'auto',
                confianca REAL NOT NULL DEFAULT 1.0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (plataforma, plataforma_item_id)
            )
            """
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_cross_canonical ON price_cross_refs(canonical_key)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_cross_pncp_item "
            "ON price_cross_refs(numero_pncp, numero_item) "
            "WHERE numero_pncp IS NOT NULL AND numero_pncp != ''"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_cross_processo "
            "ON price_cross_refs(numero_processo, plataforma) "
            "WHERE numero_processo IS NOT NULL AND numero_processo != ''"
        )
    return path


def upsert_cross_ref(
    *,
    canonical_key: str,
    plataforma: str,
    plataforma_item_id: str,
    numero_pncp: Optional[str] = None,
    numero_item: Optional[str] = None,
    numero_processo: Optional[str] = None,
    cnpj_fornecedor: Optional[str] = None,
    valor_bucket: Optional[int] = None,
    desc_norm: Optional[str] = None,
    metodo: str = "auto",
    confianca: float = 1.0,
    db_path: Optional[str] = None,
) -> None:
    path = ensure_crosslink_db(db_path)
    now = _utc_now()
    with platform_conn(path) as c:
        c.execute(
            """
            INSERT INTO price_cross_refs (
                canonical_key, plataforma, plataforma_item_id,
                numero_pncp, numero_item, numero_processo,
                cnpj_fornecedor, valor_bucket, desc_norm,
                metodo, confianca, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(plataforma, plataforma_item_id) DO UPDATE SET
                canonical_key=excluded.canonical_key,
                numero_pncp=excluded.numero_pncp,
                numero_item=excluded.numero_item,
                numero_processo=excluded.numero_processo,
                cnpj_fornecedor=excluded.cnpj_fornecedor,
                valor_bucket=excluded.valor_bucket,
                desc_norm=excluded.desc_norm,
                metodo=excluded.metodo,
                confianca=excluded.confianca,
                updated_at=excluded.updated_at
            """,
            (
                canonical_key,
                plataforma,
                plataforma_item_id,
                numero_pncp or None,
                numero_item or None,
                numero_processo or None,
                cnpj_fornecedor or None,
                valor_bucket,
                desc_norm or None,
                metodo,
                confianca,
                now,
            ),
        )


def resolve_canonical_key(
    *,
    plataforma: str,
    plataforma_item_id: str,
    numero_pncp: Optional[str] = None,
    numero_item: Optional[str] = None,
    numero_processo: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Optional[str]:
    """Resolve chave canônica persistida para um item de plataforma."""
    path = ensure_crosslink_db(db_path)
    if not os.path.isfile(path):
        return None
    with platform_conn(path) as c:
        row = c.execute(
            """
            SELECT canonical_key FROM price_cross_refs
            WHERE plataforma=? AND plataforma_item_id=?
            LIMIT 1
            """,
            (plataforma, plataforma_item_id),
        ).fetchone()
        if row:
            return str(row["canonical_key"] or "") or None

        if numero_pncp:
            q = """
                SELECT canonical_key FROM price_cross_refs
                WHERE numero_pncp=? AND (numero_item IS NULL OR numero_item=? OR numero_item='')
                ORDER BY confianca DESC LIMIT 1
            """
            row = c.execute(q, (numero_pncp, numero_item or "")).fetchone()
            if row:
                return str(row["canonical_key"] or "") or None

        if numero_processo:
            row = c.execute(
                """
                SELECT canonical_key FROM price_cross_refs
                WHERE numero_processo=? AND plataforma=?
                ORDER BY confianca DESC LIMIT 1
                """,
                (numero_processo, plataforma),
            ).fetchone()
            if row:
                return str(row["canonical_key"] or "") or None
    return None


def find_cross_platform_siblings(
    canonical_key: str,
    *,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Todos os IDs de plataforma ligados à mesma compra/preço."""
    path = ensure_crosslink_db(db_path)
    if not os.path.isfile(path):
        return []
    with platform_conn(path) as c:
        rows = c.execute(
            """
            SELECT plataforma, plataforma_item_id, numero_pncp, numero_item,
                   numero_processo, confianca, metodo
            FROM price_cross_refs
            WHERE canonical_key=?
            ORDER BY confianca DESC, plataforma
            """,
            (canonical_key,),
        ).fetchall()
    return [dict(r) for r in rows]


def crosslink_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    path = ensure_crosslink_db(db_path)
    with platform_conn(path) as c:
        total = int(c.execute("SELECT COUNT(*) AS n FROM price_cross_refs").fetchone()["n"] or 0)
        keys = int(
            c.execute("SELECT COUNT(DISTINCT canonical_key) AS n FROM price_cross_refs").fetchone()["n"]
            or 0
        )
    return {"db_path": path, "refs_total": total, "canonical_keys": keys}
