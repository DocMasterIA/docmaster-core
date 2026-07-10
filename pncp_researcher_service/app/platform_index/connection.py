from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def platform_conn(db_path: str) -> Iterator[sqlite3.Connection]:
    """Conexão SQLite WAL para índice de plataforma (não-PNCP)."""
    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    finally:
        conn.close()
