from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .connection import platform_conn
from .registry import PlatformIndexSpec, get_platform_spec


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _trigger_exists(c: sqlite3.Cursor, name: str) -> bool:
    row = c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='trigger' AND name=? LIMIT 1",
        (name,),
    ).fetchone()
    return row is not None


def _ensure_fts_triggers(c: sqlite3.Cursor) -> None:
    if not _trigger_exists(c, "platform_itens_fts_ai"):
        c.execute(
            """
            CREATE TRIGGER platform_itens_fts_ai AFTER INSERT ON platform_itens_leitura BEGIN
                INSERT INTO platform_itens_fts(rowid, descricao, material_servico)
                VALUES (new.id, new.descricao, COALESCE(new.material_servico, ''));
            END
            """
        )
    if not _trigger_exists(c, "platform_itens_fts_ad"):
        c.execute(
            """
            CREATE TRIGGER platform_itens_fts_ad AFTER DELETE ON platform_itens_leitura BEGIN
                INSERT INTO platform_itens_fts(platform_itens_fts, rowid, descricao, material_servico)
                VALUES ('delete', old.id, old.descricao, COALESCE(old.material_servico, ''));
            END
            """
        )
    if not _trigger_exists(c, "platform_itens_fts_au"):
        c.execute(
            """
            CREATE TRIGGER platform_itens_fts_au AFTER UPDATE ON platform_itens_leitura BEGIN
                INSERT INTO platform_itens_fts(platform_itens_fts, rowid, descricao, material_servico)
                VALUES ('delete', old.id, old.descricao, COALESCE(old.material_servico, ''));
                INSERT INTO platform_itens_fts(rowid, descricao, material_servico)
                VALUES (new.id, new.descricao, COALESCE(new.material_servico, ''));
            END
            """
        )


def ensure_platform_index(platform_id: str, *, db_path: Optional[str] = None) -> str:
    """
    Cria schema canônico para plataformas batch (TCE, PCP, …).
    PNCP usa legacy_pncp — não chamar aqui.
    Retorna o caminho do arquivo .db.
    """
    spec = get_platform_spec(platform_id)
    if spec is None:
        raise ValueError(f"plataforma desconhecida: {platform_id}")
    if spec.schema_kind == "legacy_pncp":
        raise ValueError(f"plataforma {platform_id} usa schema legacy (local_index.py)")
    if spec.schema_kind == "api_only":
        raise ValueError(f"plataforma {platform_id} não possui índice SQLite")

    path = (db_path or spec.db_path or "").strip()
    if not path:
        raise ValueError(f"db_path ausente para plataforma {platform_id}")

    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with platform_conn(path) as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS platform_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS platform_processos (
                id TEXT PRIMARY KEY,
                plataforma TEXT NOT NULL,
                numero_processo TEXT,
                numero_pncp TEXT,
                orgao TEXT,
                municipio TEXT,
                uf TEXT,
                objeto TEXT,
                data_publicacao TEXT,
                updated_at TEXT NOT NULL,
                raw_json_zlib BLOB
            )
            """
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_platform_proc_pncp ON platform_processos(numero_pncp)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_platform_proc_numero ON platform_processos(numero_processo)"
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS platform_itens_bruto (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                processo_id TEXT NOT NULL,
                plataforma TEXT NOT NULL,
                numero_item TEXT,
                descricao TEXT,
                material_servico TEXT,
                quantidade REAL,
                unidade_medida TEXT,
                valor_unitario REAL,
                valor_unitario_homologado REAL,
                fornecedor_nome TEXT,
                cnpj_fornecedor TEXT,
                item_fingerprint TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                raw_json_zlib BLOB,
                UNIQUE(processo_id, item_fingerprint),
                FOREIGN KEY(processo_id) REFERENCES platform_processos(id)
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS platform_itens_leitura (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plataforma TEXT NOT NULL,
                plataforma_item_id TEXT NOT NULL,
                processo_id TEXT NOT NULL,
                numero_item TEXT,
                descricao TEXT NOT NULL,
                material_servico TEXT,
                valor_unitario REAL,
                valor_unitario_homologado REAL,
                unidade_medida TEXT,
                quantidade REAL,
                orgao TEXT,
                municipio TEXT,
                uf TEXT,
                fornecedor_nome TEXT,
                cnpj_fornecedor TEXT,
                data_referencia TEXT,
                inciso_classificacao TEXT,
                esfera TEXT,
                url_origem TEXT,
                numero_pncp TEXT,
                numero_processo TEXT,
                updated_at TEXT NOT NULL,
                UNIQUE(plataforma, plataforma_item_id)
            )
            """
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_platform_leitura_uf "
            "ON platform_itens_leitura(uf, municipio)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_platform_leitura_pncp "
            "ON platform_itens_leitura(numero_pncp, numero_item)"
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS platform_ingest_state (
                scope_key TEXT PRIMARY KEY,
                watermark TEXT,
                last_error TEXT,
                rows_total INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS platform_cross_refs_local (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plataforma_origem TEXT NOT NULL,
                plataforma_destino TEXT NOT NULL,
                id_origem TEXT NOT NULL,
                id_destino TEXT NOT NULL,
                metodo TEXT NOT NULL,
                confianca REAL NOT NULL DEFAULT 1.0,
                updated_at TEXT NOT NULL,
                UNIQUE(plataforma_origem, plataforma_destino, id_origem, id_destino)
            )
            """
        )
        c.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS platform_itens_fts USING fts5(
                descricao,
                material_servico,
                content='platform_itens_leitura',
                content_rowid='id',
                tokenize='unicode61 remove_diacritics 2'
            )
            """
        )
        _ensure_fts_triggers(c)
        now = _utc_now()
        c.execute(
            """
            INSERT INTO platform_meta(key, value, updated_at)
            VALUES ('schema_version', '1', ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """,
            (now,),
        )
        c.execute(
            """
            INSERT INTO platform_meta(key, value, updated_at)
            VALUES ('plataforma', ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """,
            (platform_id, now),
        )
    return path


def platform_index_stats(db_path: str) -> Dict[str, Any]:
    """Estatísticas rápidas de um índice platform_index."""
    if not os.path.isfile(db_path):
        return {"db_exists": False, "itens_leitura": 0, "fts_rows": 0}
    with platform_conn(db_path) as c:
        leitura = int(
            c.execute("SELECT COUNT(*) AS n FROM platform_itens_leitura").fetchone()["n"] or 0
        )
        try:
            fts = int(c.execute("SELECT COUNT(*) AS n FROM platform_itens_fts").fetchone()["n"] or 0)
        except sqlite3.Error:
            fts = 0
    return {
        "db_exists": True,
        "itens_leitura": leitura,
        "fts_rows": fts,
        "search_ready": leitura > 0 and fts > 0,
    }


def platform_spec_with_stats(spec: PlatformIndexSpec) -> Dict[str, Any]:
    out = spec.to_dict()
    if spec.schema_kind == "platform_index" and spec.db_path:
        out["index_stats"] = platform_index_stats(spec.db_path)
        out["search_ready"] = bool(out["index_stats"].get("search_ready"))
    elif spec.schema_kind == "legacy_pncp":
        out["search_ready"] = spec.db_exists()
    return out
