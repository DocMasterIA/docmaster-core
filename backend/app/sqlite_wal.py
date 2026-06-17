"""SQLite WAL + busy_timeout — reduz bloqueio global durante cargas PNCP."""
from __future__ import annotations

from django.db.backends.signals import connection_created


def _configure_sqlite(sender, connection, **kwargs):
    if connection.vendor != "sqlite":
        return
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")


def connect_sqlite_wal_signal() -> None:
    connection_created.connect(_configure_sqlite, dispatch_uid="docmaster_sqlite_wal")
