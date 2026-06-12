"""Fila SQLite para ingestão PNCP em 2 fases: catálogo (página) → itens (contrato)."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .config import (
    PNCP_INGEST_QUEUE_MAX_ATTEMPTS,
    PNCP_LOCAL_DB_PATH,
)

TASK_CATALOG_PAGE = "catalog_page"
TASK_CONTRACT_ITEMS = "contract_items"

_STATUS_PENDING = "pending"
_STATUS_PROCESSING = "processing"
_STATUS_DONE = "done"
_STATUS_FAILED = "failed"
_STATUS_DEAD = "dead"


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def ensure_ingest_queue(c: sqlite3.Cursor) -> None:
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS pncp_ingest_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 100,
            uf TEXT,
            modalidade INTEGER,
            pagina INTEGER,
            data_inicial TEXT,
            data_final TEXT,
            numero_pncp TEXT,
            payload_json TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 5,
            last_error TEXT,
            available_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    c.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_ingest_queue_catalog
        ON pncp_ingest_queue (
            task_type, uf, modalidade, pagina, data_inicial, data_final
        )
        WHERE task_type = 'catalog_page' AND status IN ('pending', 'processing')
        """
    )
    c.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_ingest_queue_contract
        ON pncp_ingest_queue (task_type, numero_pncp)
        WHERE task_type = 'contract_items' AND status IN ('pending', 'processing')
        """
    )
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_ingest_queue_pick "
        "ON pncp_ingest_queue (status, available_at, priority, id)"
    )


def _queue_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(PNCP_LOCAL_DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def enqueue_catalog_page(
    *,
    uf: str,
    modalidade: int,
    pagina: int,
    data_inicial: str,
    data_final: str,
    priority: int = 100,
    tamanho_pagina: int = 50,
) -> bool:
    uf_k = str(uf).strip().upper()
    pag = int(pagina)
    mod = int(modalidade)
    now = _utc_now_iso()
    payload = json.dumps({"tamanho_pagina": int(tamanho_pagina)}, ensure_ascii=False)
    with _queue_conn() as c:
        skipped = c.execute(
            """
            SELECT 1 FROM pncp_ingest_queue
            WHERE task_type = ?
              AND uf = ? AND modalidade = ? AND pagina = ?
              AND data_inicial = ? AND data_final = ?
              AND status = 'done'
              AND last_error LIKE 'skip:%'
            LIMIT 1
            """,
            (
                TASK_CATALOG_PAGE,
                uf_k,
                mod,
                pag,
                data_inicial,
                data_final,
            ),
        ).fetchone()
        if skipped:
            return False
        cur = c.execute(
            """
            INSERT OR IGNORE INTO pncp_ingest_queue (
                task_type, priority, uf, modalidade, pagina, data_inicial, data_final,
                numero_pncp, payload_json, status, attempts, max_attempts,
                last_error, available_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, 0, ?, NULL, ?, ?, ?)
            """,
            (
                TASK_CATALOG_PAGE,
                int(priority),
                str(uf).strip().upper(),
                int(modalidade),
                int(pagina),
                data_inicial,
                data_final,
                payload,
                _STATUS_PENDING,
                int(PNCP_INGEST_QUEUE_MAX_ATTEMPTS),
                now,
                now,
                now,
            ),
        )
        c.commit()
        return int(cur.rowcount or 0) > 0


def enqueue_contract_items(
    *,
    numero_pncp: str,
    priority: int = 100,
    payload: Optional[Dict[str, Any]] = None,
) -> bool:
    numero = str(numero_pncp or "").strip()
    if not numero:
        return False
    now = _utc_now_iso()
    blob = json.dumps(payload or {}, ensure_ascii=False)
    with _queue_conn() as c:
        cur = c.execute(
            """
            INSERT OR IGNORE INTO pncp_ingest_queue (
                task_type, priority, uf, modalidade, pagina, data_inicial, data_final,
                numero_pncp, payload_json, status, attempts, max_attempts,
                last_error, available_at, created_at, updated_at
            ) VALUES (?, ?, NULL, NULL, NULL, NULL, NULL, ?, ?, ?, 0, ?, NULL, ?, ?, ?)
            """,
            (
                TASK_CONTRACT_ITEMS,
                int(priority),
                numero,
                blob,
                _STATUS_PENDING,
                int(PNCP_INGEST_QUEUE_MAX_ATTEMPTS),
                now,
                now,
                now,
            ),
        )
        c.commit()
        return int(cur.rowcount or 0) > 0


def claim_tasks(*, task_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    now = _utc_now_iso()
    lim = int(limit)
    if lim <= 0:
        return []
    with _queue_conn() as c:
        where = "status = ? AND available_at <= ?"
        params: List[Any] = [_STATUS_PENDING, now]
        if task_type:
            where += " AND task_type = ?"
            params.append(task_type)
        rows = c.execute(
            f"""
            SELECT id FROM pncp_ingest_queue
            WHERE {where}
            ORDER BY priority ASC, id ASC
            LIMIT ?
            """,
            (*params, lim),
        ).fetchall()
        ids = [int(r["id"]) for r in rows]
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        c.execute(
            f"""
            UPDATE pncp_ingest_queue
            SET status = ?, updated_at = ?, attempts = attempts + 1
            WHERE id IN ({placeholders}) AND status = ?
            """,
            (_STATUS_PROCESSING, now, *ids, _STATUS_PENDING),
        )
        claimed = c.execute(
            f"""
            SELECT * FROM pncp_ingest_queue
            WHERE id IN ({placeholders}) AND status = ?
            """,
            (*ids, _STATUS_PROCESSING),
        ).fetchall()
        c.commit()
        return [dict(r) for r in claimed]


def mark_task_done(task_id: int) -> None:
    now = _utc_now_iso()
    with _queue_conn() as c:
        c.execute(
            """
            UPDATE pncp_ingest_queue
            SET status = ?, last_error = NULL, updated_at = ?
            WHERE id = ?
            """,
            (_STATUS_DONE, now, int(task_id)),
        )
        c.commit()


def mark_task_failed(task_id: int, message: str, *, retry_seconds: int = 120) -> str:
    now_dt = datetime.utcnow()
    now = now_dt.isoformat(timespec="seconds") + "Z"
    with _queue_conn() as c:
        row = c.execute(
            "SELECT attempts, max_attempts FROM pncp_ingest_queue WHERE id = ?",
            (int(task_id),),
        ).fetchone()
        if not row:
            return _STATUS_DEAD
        attempts = int(row["attempts"] or 0)
        max_attempts = int(row["max_attempts"] or PNCP_INGEST_QUEUE_MAX_ATTEMPTS)
        if attempts >= max_attempts:
            status = _STATUS_DEAD
            available = now
        else:
            status = _STATUS_PENDING
            available = (
                now_dt + timedelta(seconds=max(1, int(retry_seconds)))
            ).isoformat(timespec="seconds") + "Z"
        c.execute(
            """
            UPDATE pncp_ingest_queue
            SET status = ?, last_error = ?, available_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, (message or "")[:800], available, now, int(task_id)),
        )
        c.commit()
        return status


def queue_stats() -> Dict[str, Any]:
    with _queue_conn() as c:
        rows = c.execute(
            """
            SELECT status, task_type, COUNT(*) AS n
            FROM pncp_ingest_queue
            GROUP BY status, task_type
            ORDER BY status, task_type
            """
        ).fetchall()
    by_status: Dict[str, int] = {}
    by_type: Dict[str, Dict[str, int]] = {}
    for r in rows:
        st = str(r["status"])
        tt = str(r["task_type"])
        n = int(r["n"])
        by_status[st] = by_status.get(st, 0) + n
        by_type.setdefault(tt, {})[st] = n
    pending = int(by_status.get(_STATUS_PENDING, 0))
    return {
        "pending": pending,
        "processing": int(by_status.get(_STATUS_PROCESSING, 0)),
        "done": int(by_status.get(_STATUS_DONE, 0)),
        "failed": int(by_status.get(_STATUS_FAILED, 0)),
        "dead": int(by_status.get(_STATUS_DEAD, 0)),
        "by_task_type": by_type,
        "total_rows": sum(by_status.values()),
    }


def pending_by_task_type(task_type: str) -> int:
    stats = queue_stats()
    return int((stats.get("by_task_type") or {}).get(task_type, {}).get("pending", 0) or 0)


def backlog_by_task_type(task_type: str) -> int:
    """pending + processing — evita liberar catálogo com tarefas presas em processing."""
    stats = queue_stats()
    by_type = (stats.get("by_task_type") or {}).get(task_type, {}) or {}
    return int(by_type.get("pending", 0) or 0) + int(by_type.get("processing", 0) or 0)


def count_contracts_without_items() -> int:
    """Contratos sem linhas em pncp_itens e ainda não verificados vazios no PNCP."""
    with _queue_conn() as c:
        row = c.execute(
            """
            SELECT COUNT(*) AS n
            FROM pncp_contratos c
            WHERE NOT EXISTS (
                SELECT 1 FROM pncp_itens i WHERE i.numero_pncp = c.numero_pncp LIMIT 1
            )
            AND (c.itens_verificados_at IS NULL OR TRIM(c.itens_verificados_at) = '')
            """
        ).fetchone()
        return int(row["n"] or 0) if row else 0
