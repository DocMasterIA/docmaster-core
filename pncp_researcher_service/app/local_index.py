from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
import zlib
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

from .config import (
    PNCP_BACKFILL_ITEM_CONCURRENCY,
    PNCP_BACKFILL_ITEM_TIMEOUT_SECONDS,
    PNCP_SEARCH_ENRICH_HOMOLOG_MAX,
    PNCP_SEARCH_ONLY_HOMOLOGATED,
    PNCP_FTS5_ENABLED,
    PNCP_INGEST_AUTOPAUSE_BASE_SECONDS,
    PNCP_INGEST_AUTOPAUSE_ENABLED,
    PNCP_INGEST_AUTOPAUSE_JSON_INVALID_SECONDS,
    PNCP_INGEST_AUTOPAUSE_MAX_SECONDS,
    PNCP_INGEST_WATERMARK_RESUME,
    effective_items_refresh_days,
    PNCP_LOCAL_BACKFILL_MONTHS,
    PNCP_LOCAL_DB_PATH,
    PNCP_LOCAL_INCLUDE_ITEMS,
    PNCP_MODALIDADES_DEFAULT,
)
from .ingest_dates import PNCP_API_MAX_LOOKBACK_DAYS, resolve_backfill_window

logger = logging.getLogger(__name__)
from .fornecedor_cache import cache_stats, ensure_fornecedor_cache_table
from .pncp_client import (
    PNCPClientError,
    create_pncp_http_client,
    fetch_contract_items_with_resultados,
    fetch_resultados_map_for_items,
    get_contract_items,
    search_contracts,
)
from .search_text_clean import apply_item_display_cleanup, normalize_for_search
from .supplier_resolver import (
    extract_homologated_pricing,
    item_homologado_para_busca,
    item_elegivel,
    nome_fornecedor_e_util,
    resolution_to_api_dict,
    resolve_from_item_catalog_row,
    resolve_from_resultados_payload,
)


def _sqlite_pncp_search_norm(value: Any) -> str:
    """Função SQLite: mesmo pipeline de `normalize_for_search` para cruzar município PNCP × lista do usuário."""
    return normalize_for_search(str(value) if value is not None else "")


@contextmanager
def _conn():
    conn = sqlite3.connect(PNCP_LOCAL_DB_PATH, timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.row_factory = sqlite3.Row
        conn.create_function("pncp_search_norm", 1, _sqlite_pncp_search_norm)
        yield conn
        conn.commit()
    finally:
        conn.close()


def ensure_local_index() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS pncp_contratos (
                numero_pncp TEXT PRIMARY KEY,
                ano_compra INTEGER,
                sequencial_compra INTEGER,
                objeto TEXT,
                orgao TEXT,
                municipio TEXT,
                uf TEXT,
                modalidade_codigo INTEGER,
                modalidade_nome TEXT,
                valor_global REAL,
                situacao TEXT,
                data_publicacao TEXT,
                updated_at TEXT NOT NULL,
                raw_json TEXT NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS pncp_itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_pncp TEXT NOT NULL,
                ano_compra INTEGER,
                sequencial_compra INTEGER,
                numero_item TEXT,
                descricao TEXT,
                material_servico TEXT,
                quantidade REAL,
                unidade_medida TEXT,
                valor_unitario REAL,
                valor_total REAL,
                orgao TEXT,
                municipio TEXT,
                uf TEXT,
                modalidade_nome TEXT,
                data_publicacao TEXT,
                item_fingerprint TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                raw_json_zlib BLOB,
                UNIQUE(numero_pncp, item_fingerprint)
            )
            """
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pncp_objeto ON pncp_contratos(objeto)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pncp_uf_municipio ON pncp_contratos(uf, municipio)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pncp_modalidade ON pncp_contratos(modalidade_codigo)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pncp_data_pub ON pncp_contratos(data_publicacao)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pncp_itens_desc ON pncp_itens(descricao)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pncp_itens_pncp ON pncp_itens(numero_pncp)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pncp_itens_uf_municipio ON pncp_itens(uf, municipio)"
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS pesquisador_sessoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT,
                termo_busca TEXT NOT NULL,
                filtros_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'aberta',
                modelo_cotacao TEXT NOT NULL DEFAULT 'pesquisa_precos_padrao',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        _migrate_pesquisador_sessoes_columns(c)
        _migrate_pncp_contratos_items_verified(c)
        _migrate_pncp_itens_supplier_columns(c)
        _migrate_pncp_itens_homolog_columns(c)
        ensure_fornecedor_cache_table(c)
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS pesquisador_sessao_itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sessao_id INTEGER NOT NULL,
                numero_pncp TEXT,
                ano_compra INTEGER,
                sequencial_compra INTEGER,
                numero_item TEXT,
                descricao_item TEXT,
                quantidade REAL,
                unidade_medida TEXT,
                valor_unitario REAL,
                valor_total REAL,
                orgao TEXT,
                municipio TEXT,
                uf TEXT,
                modalidade TEXT,
                source_json_zlib BLOB,
                created_at TEXT NOT NULL,
                FOREIGN KEY(sessao_id) REFERENCES pesquisador_sessoes(id)
            )
            """
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pesq_sess_created ON pesquisador_sessoes(created_at DESC)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pesq_sess_itens_sessao ON pesquisador_sessao_itens(sessao_id)"
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS pncp_ingest_state (
                uf TEXT NOT NULL,
                modalidade INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                error_streak INTEGER NOT NULL DEFAULT 0,
                last_error_kind TEXT,
                last_error_message TEXT,
                paused_until TEXT,
                last_success_at TEXT,
                last_attempt_at TEXT,
                last_data_inicial TEXT,
                last_data_final TEXT,
                last_page INTEGER,
                total_upserts INTEGER NOT NULL DEFAULT 0,
                total_item_upserts INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (uf, modalidade)
            )
            """
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_ingest_state_status ON pncp_ingest_state(status, paused_until)"
        )
        from .ingest_queue import ensure_ingest_queue

        ensure_ingest_queue(c)
        _ensure_fts5_schema(c)


def _ensure_fts5_schema(c: sqlite3.Cursor) -> None:
    """Índice FTS5 em descrição/material (content= pncp_itens). Triggers mantêm sincronia."""
    c.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS pncp_itens_fts USING fts5(
            descricao,
            material_servico,
            content='pncp_itens',
            content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        )
        """
    )

    def _trigger_exists(name: str) -> bool:
        row = c.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'trigger' AND name = ?",
            (name,),
        ).fetchone()
        return row is not None

    if not _trigger_exists("pncp_itens_fts_ai"):
        c.execute(
            """
            CREATE TRIGGER pncp_itens_fts_ai AFTER INSERT ON pncp_itens BEGIN
                INSERT INTO pncp_itens_fts(rowid, descricao, material_servico)
                VALUES (new.id, new.descricao, new.material_servico);
            END
            """
        )
    if not _trigger_exists("pncp_itens_fts_ad"):
        c.execute(
            """
            CREATE TRIGGER pncp_itens_fts_ad AFTER DELETE ON pncp_itens BEGIN
                INSERT INTO pncp_itens_fts(pncp_itens_fts, rowid, descricao, material_servico)
                VALUES ('delete', old.id, old.descricao, old.material_servico);
            END
            """
        )
    if not _trigger_exists("pncp_itens_fts_au"):
        c.execute(
            """
            CREATE TRIGGER pncp_itens_fts_au AFTER UPDATE ON pncp_itens BEGIN
                INSERT INTO pncp_itens_fts(pncp_itens_fts, rowid, descricao, material_servico)
                VALUES ('delete', old.id, old.descricao, old.material_servico);
                INSERT INTO pncp_itens_fts(rowid, descricao, material_servico)
                VALUES (new.id, new.descricao, new.material_servico);
            END
            """
        )


def _escape_fts_token(token: str) -> str:
    return re.sub(r'["*]', " ", (token or "")).strip()


def _build_fts_match_query(termo_busca: str, *, anchor_only: bool = True) -> Optional[str]:
    """
    Monta MATCH FTS5.

    ``anchor_only=True`` (padrão): só o 1º token — recall alto; o AND completo fica
    em ``_row_matches_search_tokens`` (mesma estratégia do fallback LIKE).
    """
    token_groups = _build_search_tokens(termo_busca)
    if not token_groups:
        return None
    groups = token_groups[:1] if anchor_only else token_groups
    parts: List[str] = []
    for variants in groups:
        opts = [_escape_fts_token(v) for v in variants if _escape_fts_token(v)]
        if not opts:
            continue
        if len(opts) == 1:
            parts.append(f'"{opts[0]}"*')
        else:
            inner = " OR ".join(f'"{o}"*' for o in opts[:4])
            parts.append(f"({inner})")
    if not parts:
        return None
    return " AND ".join(parts)


def fts_index_status() -> Dict[str, Any]:
    ensure_local_index()
    with _conn() as c:
        items_total = int(c.execute("SELECT COUNT(*) AS n FROM pncp_itens").fetchone()["n"] or 0)
        try:
            fts_total = int(c.execute("SELECT COUNT(*) AS n FROM pncp_itens_fts").fetchone()["n"] or 0)
            fts_ready = True
        except sqlite3.OperationalError:
            fts_total = 0
            fts_ready = False
    needs_rebuild = fts_ready and items_total > 0 and fts_total < int(items_total * 0.85)
    return {
        "enabled": bool(PNCP_FTS5_ENABLED),
        "ready": fts_ready,
        "items_total": items_total,
        "fts_rows": fts_total,
        "needs_rebuild": needs_rebuild,
    }


def rebuild_fts_index() -> Dict[str, Any]:
    """Reconstrói FTS5 a partir de pncp_itens (pode demorar em bases grandes)."""
    ensure_local_index()
    with _conn() as c:
        items_total = int(c.execute("SELECT COUNT(*) AS n FROM pncp_itens").fetchone()["n"] or 0)
        c.execute("INSERT INTO pncp_itens_fts(pncp_itens_fts) VALUES('rebuild')")
        fts_total = int(c.execute("SELECT COUNT(*) AS n FROM pncp_itens_fts").fetchone()["n"] or 0)
    return {
        "ok": True,
        "items_total": items_total,
        "fts_rows": fts_total,
        "rebuilt_at": _utc_now_iso(),
    }


def local_index_operational_status(*, uf: Optional[str] = None) -> Dict[str, Any]:
    stats = local_index_stats()
    ingest = ingest_operational_status(uf=uf)
    fts = fts_index_status()
    return {
        "ok": True,
        "index": stats,
        "ingest": ingest,
        "fts": fts,
    }


def _ingest_scope_uf(uf: Optional[str]) -> str:
    u = str(uf or "").strip().upper()
    return u if u else "*"


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _parse_iso_utc(v: Any) -> Optional[datetime]:
    s = str(v or "").strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _classify_ingest_error(message: str) -> str:
    t = (message or "").lower()
    if "429" in t or "rate" in t:
        return "rate_limit"
    if "json inválido" in t or "json invalido" in t:
        return "json_invalid"
    if "502" in t or "503" in t or "504" in t or "gateway" in t or "waf" in t:
        return "waf_or_gateway"
    if "timeout" in t or "timed out" in t:
        return "timeout"
    return "other"


def _compute_pause_seconds(error_kind: str, streak: int) -> int:
    if not PNCP_INGEST_AUTOPAUSE_ENABLED:
        return 0
    s = max(1, int(streak))
    if error_kind == "json_invalid":
        return max(0, int(PNCP_INGEST_AUTOPAUSE_JSON_INVALID_SECONDS))
    base = max(1, int(PNCP_INGEST_AUTOPAUSE_BASE_SECONDS))
    cap = max(base, int(PNCP_INGEST_AUTOPAUSE_MAX_SECONDS))
    return min(cap, base * (2 ** max(0, s - 1)))


def _get_ingest_state(uf: Optional[str], modalidade: int) -> Optional[sqlite3.Row]:
    ensure_local_index()
    with _conn() as c:
        return c.execute(
            """
            SELECT *
            FROM pncp_ingest_state
            WHERE uf = ? AND modalidade = ?
            """,
            (_ingest_scope_uf(uf), int(modalidade)),
        ).fetchone()


def _upsert_ingest_state(
    uf: Optional[str],
    modalidade: int,
    **fields: Any,
) -> None:
    ensure_local_index()
    scope_uf = _ingest_scope_uf(uf)
    now = _utc_now_iso()
    base: Dict[str, Any] = {
        "status": "active",
        "error_streak": 0,
        "last_error_kind": None,
        "last_error_message": None,
        "paused_until": None,
        "last_success_at": None,
        "last_attempt_at": None,
        "last_data_inicial": None,
        "last_data_final": None,
        "last_page": None,
        "total_upserts": 0,
        "total_item_upserts": 0,
    }
    base.update(fields)
    with _conn() as c:
        c.execute(
            """
            INSERT INTO pncp_ingest_state (
                uf, modalidade, status, error_streak, last_error_kind, last_error_message,
                paused_until, last_success_at, last_attempt_at, last_data_inicial, last_data_final,
                last_page, total_upserts, total_item_upserts, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(uf, modalidade) DO UPDATE SET
                status=excluded.status,
                error_streak=excluded.error_streak,
                last_error_kind=excluded.last_error_kind,
                last_error_message=excluded.last_error_message,
                paused_until=excluded.paused_until,
                last_success_at=excluded.last_success_at,
                last_attempt_at=excluded.last_attempt_at,
                last_data_inicial=excluded.last_data_inicial,
                last_data_final=excluded.last_data_final,
                last_page=excluded.last_page,
                total_upserts=excluded.total_upserts,
                total_item_upserts=excluded.total_item_upserts,
                updated_at=excluded.updated_at
            """,
            (
                scope_uf,
                int(modalidade),
                str(base.get("status") or "active"),
                int(base.get("error_streak") or 0),
                base.get("last_error_kind"),
                base.get("last_error_message"),
                base.get("paused_until"),
                base.get("last_success_at"),
                base.get("last_attempt_at"),
                base.get("last_data_inicial"),
                base.get("last_data_final"),
                int(base.get("last_page")) if base.get("last_page") is not None else None,
                int(base.get("total_upserts") or 0),
                int(base.get("total_item_upserts") or 0),
                now,
            ),
        )


def _mark_ingest_success(
    uf: Optional[str],
    modalidade: int,
    *,
    data_inicial: str,
    data_final: str,
    page: int,
    add_upserts: int,
    add_item_upserts: int,
) -> None:
    row = _get_ingest_state(uf, modalidade)
    total_upserts = int((row["total_upserts"] if row else 0) or 0) + max(0, int(add_upserts))
    total_item_upserts = int((row["total_item_upserts"] if row else 0) or 0) + max(
        0, int(add_item_upserts)
    )
    now = _utc_now_iso()
    _upsert_ingest_state(
        uf,
        modalidade,
        status="active",
        error_streak=0,
        last_error_kind=None,
        last_error_message=None,
        paused_until=None,
        last_success_at=now,
        last_attempt_at=now,
        last_data_inicial=data_inicial,
        last_data_final=data_final,
        last_page=page,
        total_upserts=total_upserts,
        total_item_upserts=total_item_upserts,
    )


def _mark_ingest_error(
    uf: Optional[str],
    modalidade: int,
    *,
    data_inicial: str,
    data_final: str,
    page: int,
    message: str,
) -> Dict[str, Any]:
    prev = _get_ingest_state(uf, modalidade)
    prev_streak = int((prev["error_streak"] if prev else 0) or 0)
    streak = prev_streak + 1
    kind = _classify_ingest_error(message)
    pause_seconds = _compute_pause_seconds(kind, streak)
    now_dt = datetime.utcnow()
    paused_until = (
        (now_dt + timedelta(seconds=pause_seconds)).isoformat(timespec="seconds") + "Z"
        if pause_seconds > 0
        else None
    )
    status = "paused_blocked" if paused_until else "degraded"
    _upsert_ingest_state(
        uf,
        modalidade,
        status=status,
        error_streak=streak,
        last_error_kind=kind,
        last_error_message=(message or "")[:800],
        paused_until=paused_until,
        last_attempt_at=now_dt.isoformat(timespec="seconds") + "Z",
        last_data_inicial=data_inicial,
        last_data_final=data_final,
        last_page=page,
        total_upserts=int((prev["total_upserts"] if prev else 0) or 0),
        total_item_upserts=int((prev["total_item_upserts"] if prev else 0) or 0),
    )
    return {
        "error_kind": kind,
        "error_streak": streak,
        "pause_seconds": pause_seconds,
        "paused_until": paused_until,
        "status": status,
    }


def resume_expired_ingest_scopes() -> int:
    """Reativa scopes cuja pausa expirou ou ficaram presos em paused_blocked/degraded."""
    ensure_local_index()
    now = _utc_now_iso()
    with _conn() as c:
        cur = c.execute(
            """
            UPDATE pncp_ingest_state
            SET status = 'active', paused_until = NULL, updated_at = ?
            WHERE status IN ('paused_blocked', 'degraded')
              AND (
                paused_until IS NULL
                OR paused_until <= ?
              )
            """,
            (now, now),
        )
        n = int(cur.rowcount or 0)
        c.commit()
    return n


def _resolve_backfill_start_page(
    uf: Optional[str],
    modalidade: int,
    *,
    data_inicial: str,
    data_final: str,
) -> tuple[int, bool]:
    if not PNCP_INGEST_WATERMARK_RESUME:
        return 1, False
    state = _get_ingest_state(uf, modalidade)
    if not state:
        return 1, False
    if (
        state["last_data_inicial"] != data_inicial
        or state["last_data_final"] != data_final
    ):
        return 1, False
    last_page = state["last_page"]
    if last_page is None:
        return 1, False
    last = int(last_page)
    if last <= 0:
        return 1, False
    return last + 1, True


def _contract_keys_for_items(raw: Dict[str, Any]) -> Optional[tuple[str, Any, Any]]:
    cnpj = (
        (raw.get("orgaoEntidade") or {}).get("cnpj")
        or (raw.get("orgaoEntidade") or {}).get("cnpjOrgaoEntidade")
        or raw.get("cnpjOrgaoEntidade")
    )
    numero = str(raw.get("numeroControlePNCP") or "")
    if (not cnpj) and "-" in numero:
        cnpj = numero.split("-")[0]
    ano = raw.get("anoCompra")
    seq = raw.get("sequencialCompra")
    if not cnpj or ano is None or seq is None:
        return None
    return str(cnpj), ano, seq


async def _backfill_fetch_contract_items(
    raw: Dict[str, Any],
    *,
    client: Any,
    item_timeout: float,
    sem: asyncio.Semaphore,
) -> tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    numero = str(raw.get("numeroControlePNCP") or "").strip()
    if numero and not contract_needs_items_refresh(numero):
        return raw, [], {}
    keys = _contract_keys_for_items(raw)
    if not keys:
        return raw, [], {}
    cnpj, ano, seq = keys
    async with sem:
        try:
            rows, resultados = await asyncio.wait_for(
                fetch_contract_items_with_resultados(cnpj, ano, seq, client=client),
                timeout=item_timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "backfill timeout itens cnpj=%s ano=%s seq=%s (>%.0fs)",
                cnpj,
                ano,
                seq,
                item_timeout,
            )
            rows, resultados = [], {}
        except Exception as exc:
            logger.warning(
                "backfill erro itens cnpj=%s ano=%s seq=%s: %s",
                cnpj,
                ano,
                seq,
                exc,
            )
            rows, resultados = [], {}
    return raw, rows, resultados


def ingest_operational_status(*, uf: Optional[str] = None) -> Dict[str, Any]:
    ensure_local_index()
    now = datetime.utcnow()
    scope_uf = _ingest_scope_uf(uf) if uf else None
    where = "WHERE uf = ?" if scope_uf else ""
    params: tuple[Any, ...] = (scope_uf,) if scope_uf else ()
    with _conn() as c:
        rows = c.execute(
            f"""
            SELECT uf, modalidade, status, error_streak, last_error_kind, last_error_message,
                   paused_until, last_success_at, last_attempt_at, last_data_inicial, last_data_final,
                   last_page, total_upserts, total_item_upserts, updated_at
            FROM pncp_ingest_state
            {where}
            ORDER BY uf, modalidade
            """,
            params,
        ).fetchall()
    scopes: List[Dict[str, Any]] = []
    paused = 0
    degraded = 0
    for r in rows:
        pu = _parse_iso_utc(r["paused_until"])
        is_paused = bool(pu and pu > now)
        db_status = str(r["status"] or "active")
        if is_paused:
            status = "paused_blocked"
        elif db_status in ("paused_blocked", "degraded"):
            status = "active"
        else:
            status = db_status
        if status == "paused_blocked":
            paused += 1
        elif status != "active":
            degraded += 1
        last_page_raw = r["last_page"]
        last_page_int = int(last_page_raw) if last_page_raw is not None else None
        next_page = 1 if (last_page_int is None or last_page_int <= 0) else last_page_int + 1
        scopes.append(
            {
                "uf": r["uf"],
                "modalidade": r["modalidade"],
                "status": status,
                "error_streak": int(r["error_streak"] or 0),
                "last_error_kind": r["last_error_kind"],
                "last_error_message": r["last_error_message"],
                "paused_until": r["paused_until"] if is_paused else None,
                "last_success_at": r["last_success_at"],
                "last_attempt_at": r["last_attempt_at"],
                "watermark": {
                    "data_inicial": r["last_data_inicial"],
                    "data_final": r["last_data_final"],
                    "last_page": last_page_raw,
                    "next_page": next_page,
                    "resume_enabled": PNCP_INGEST_WATERMARK_RESUME,
                },
                "total_upserts": int(r["total_upserts"] or 0),
                "total_item_upserts": int(r["total_item_upserts"] or 0),
                "updated_at": r["updated_at"],
            }
        )
    overall = "active"
    if paused > 0:
        overall = "paused_blocked"
    elif degraded > 0:
        overall = "degraded"
    return {
        "ok": True,
        "overall_status": overall,
        "scopes_total": len(scopes),
        "scopes_paused": paused,
        "scopes_degraded": degraded,
        "scopes_active": max(0, len(scopes) - paused - degraded),
        "scopes": scopes,
    }


def _migrate_pesquisador_sessoes_columns(c: sqlite3.Cursor) -> None:
    """Compatibiliza bases antigas sem modelo_cotacao."""
    cols = {row[1] for row in c.execute("PRAGMA table_info(pesquisador_sessoes)")}
    if "modelo_cotacao" not in cols:
        c.execute(
            """
            ALTER TABLE pesquisador_sessoes
            ADD COLUMN modelo_cotacao TEXT DEFAULT 'pesquisa_precos_padrao'
            """
        )


def _migrate_pncp_contratos_items_verified(c: sqlite3.Cursor) -> None:
    """Contratos consultados no PNCP sem linhas em pncp_itens (evita gap eterno)."""
    cols = {row[1] for row in c.execute("PRAGMA table_info(pncp_contratos)")}
    if "itens_verificados_at" not in cols:
        c.execute("ALTER TABLE pncp_contratos ADD COLUMN itens_verificados_at TEXT")


def mark_contract_items_verified(numero_pncp: str) -> None:
    """Marca contrato como verificado no PNCP mesmo sem linhas em pncp_itens."""
    numero = str(numero_pncp or "").strip()
    if not numero:
        return
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with _conn() as c:
        _migrate_pncp_contratos_items_verified(c)
        c.execute(
            "UPDATE pncp_contratos SET itens_verificados_at = ? WHERE numero_pncp = ?",
            (now, numero),
        )


_PNCP_ITENS_SUPPLIER_COLUMNS: List[tuple[str, str]] = [
    ("cnpj_fornecedor", "TEXT"),
    ("fornecedor", "TEXT"),
    ("fornecedor_fonte", "TEXT"),
    ("situacao_item", "TEXT"),
    ("situacao_compra", "TEXT"),
    ("fornecedor_elegivel", "INTEGER NOT NULL DEFAULT 0"),
    ("fornecedor_resolvido_at", "TEXT"),
]


_PNCP_ITENS_HOMOLOG_COLUMNS: List[tuple[str, str]] = [
    ("valor_unitario_estimado", "REAL"),
    ("valor_total_estimado", "REAL"),
    ("quantidade_estimada", "REAL"),
    ("valor_unitario_homologado", "REAL"),
    ("valor_total_homologado", "REAL"),
    ("quantidade_homologada", "REAL"),
    ("resultado_resolvido_at", "TEXT"),
]


def _migrate_pncp_itens_homolog_columns(c: sqlite3.Cursor) -> None:
    cols = {row[1] for row in c.execute("PRAGMA table_info(pncp_itens)")}
    for name, col_type in _PNCP_ITENS_HOMOLOG_COLUMNS:
        if name not in cols:
            c.execute(f"ALTER TABLE pncp_itens ADD COLUMN {name} {col_type}")


def _migrate_pncp_itens_supplier_columns(c: sqlite3.Cursor) -> None:
    """Fase A: colunas de fornecedor vencedor em pncp_itens (bases existentes)."""
    cols = {row[1] for row in c.execute("PRAGMA table_info(pncp_itens)")}
    for name, col_type in _PNCP_ITENS_SUPPLIER_COLUMNS:
        if name not in cols:
            c.execute(f"ALTER TABLE pncp_itens ADD COLUMN {name} {col_type}")
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_pncp_itens_fornecedor_elegivel "
        "ON pncp_itens(fornecedor_elegivel, cnpj_fornecedor)"
    )
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_pncp_itens_pncp_numero_item "
        "ON pncp_itens(numero_pncp, numero_item)"
    )


def _objeto(raw: Dict[str, Any]) -> str:
    for k in ("objetoCompra", "objeto", "descricaoObjeto", "titulo"):
        v = raw.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def upsert_contracts(raw_items: Iterable[Dict[str, Any]]) -> int:
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    count = 0
    with _conn() as c:
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            numero = str(raw.get("numeroControlePNCP") or "").strip()
            if not numero:
                continue
            org = raw.get("orgaoEntidade") or {}
            unid = raw.get("unidadeOrgao") or {}
            valor = raw.get("valorTotalEstimado")
            try:
                valor_f = float(valor) if valor is not None else None
            except Exception:
                valor_f = None
            c.execute(
                """
                INSERT INTO pncp_contratos (
                    numero_pncp, ano_compra, sequencial_compra, objeto, orgao, municipio, uf,
                    modalidade_codigo, modalidade_nome, valor_global, situacao, data_publicacao,
                    updated_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(numero_pncp) DO UPDATE SET
                    ano_compra=excluded.ano_compra,
                    sequencial_compra=excluded.sequencial_compra,
                    objeto=excluded.objeto,
                    orgao=excluded.orgao,
                    municipio=excluded.municipio,
                    uf=excluded.uf,
                    modalidade_codigo=excluded.modalidade_codigo,
                    modalidade_nome=excluded.modalidade_nome,
                    valor_global=excluded.valor_global,
                    situacao=excluded.situacao,
                    data_publicacao=excluded.data_publicacao,
                    updated_at=excluded.updated_at,
                    raw_json=excluded.raw_json
                """,
                (
                    numero,
                    raw.get("anoCompra"),
                    raw.get("sequencialCompra"),
                    _objeto(raw),
                    org.get("razaoSocial") or org.get("razaosocial"),
                    unid.get("municipioNome"),
                    unid.get("ufSigla"),
                    raw.get("modalidadeId"),
                    raw.get("modalidadeNome"),
                    valor_f,
                    raw.get("situacaoCompraNome"),
                    raw.get("dataPublicacaoPncp") or raw.get("dataPublicacao"),
                    now,
                    json.dumps(raw, ensure_ascii=False),
                ),
            )
            count += 1
    return count


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def _item_desc(raw: Dict[str, Any]) -> str:
    for k in ("descricao", "descricaoItem", "descricaoResumida", "item", "nomeItem"):
        v = raw.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _parse_item_updated_at_iso(value: str) -> Optional[datetime]:
    s = (value or "").strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        elif "T" not in s and " " in s:
            s = s.replace(" ", "T", 1)
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except Exception:
        return None


def contract_needs_items_refresh(numero_pncp: str) -> bool:
    """
    True = deve buscar GET /itens no PNCP.
    Com PNCP_INGEST_ITEMS_REFRESH_DAYS > 0, pula contratos cujos itens foram buscados recentemente.
    """
    days = effective_items_refresh_days()
    if days <= 0:
        return True
    numero = str(numero_pncp or "").strip()
    if not numero:
        return True
    with _conn() as c:
        _migrate_pncp_contratos_items_verified(c)
        ctr = c.execute(
            "SELECT itens_verificados_at FROM pncp_contratos WHERE numero_pncp = ?",
            (numero,),
        ).fetchone()
        row = c.execute(
            """
            SELECT COUNT(*) AS n, MAX(updated_at) AS last_upd
            FROM pncp_itens
            WHERE numero_pncp = ?
            """,
            (numero,),
        ).fetchone()
    if (not row or int(row["n"] or 0) <= 0) and ctr and ctr["itens_verificados_at"]:
        verified_dt = _parse_item_updated_at_iso(str(ctr["itens_verificados_at"] or ""))
        if verified_dt is not None and datetime.utcnow() - verified_dt < timedelta(days=days):
            return False
    if not row or int(row["n"] or 0) <= 0:
        return True
    last_dt = _parse_item_updated_at_iso(str(row["last_upd"] or ""))
    if last_dt is None:
        return True
    return datetime.utcnow() - last_dt >= timedelta(days=days)


def upsert_contract_items(
    raw_contract: Dict[str, Any],
    item_rows: Iterable[Dict[str, Any]],
    *,
    resultados_by_item: Optional[Dict[str, Dict[str, Any]]] = None,
) -> int:
    numero = str(raw_contract.get("numeroControlePNCP") or "").strip()
    if not numero:
        return 0
    org = raw_contract.get("orgaoEntidade") or {}
    unid = raw_contract.get("unidadeOrgao") or {}
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    ano = raw_contract.get("anoCompra")
    seq = raw_contract.get("sequencialCompra")
    modalidade_nome = raw_contract.get("modalidadeNome")
    data_pub = raw_contract.get("dataPublicacaoPncp") or raw_contract.get("dataPublicacao")
    sit_compra_row = str(raw_contract.get("situacaoCompra") or raw_contract.get("situacao") or "").strip()
    resultados_map = resultados_by_item or {}
    count = 0
    with _conn() as c:
        _migrate_pncp_itens_homolog_columns(c)
        _migrate_pncp_itens_supplier_columns(c)
        for r in item_rows:
            if not isinstance(r, dict):
                continue
            desc = _item_desc(r)
            if not desc:
                continue
            numero_item = str(
                r.get("numeroItem") or r.get("ordemItem") or r.get("sequencialItem") or ""
            ).strip()
            resultado = resultados_map.get(numero_item) if numero_item else None

            qtd_est = _safe_float(r.get("quantidade"))
            vu_est = _safe_float(r.get("valorUnitarioEstimado"))
            vt_est = _safe_float(r.get("valorTotal") or r.get("valorTotalEstimado"))

            pricing_src = resultado if isinstance(resultado, dict) else r
            homolog = extract_homologated_pricing(pricing_src)
            qtd_hom = homolog["quantidade_homologada"]
            vu_hom = homolog["valor_unitario_homologado"]
            vt_hom = homolog["valor_total_homologado"]
            has_homolog = vu_hom is not None or vt_hom is not None or qtd_hom is not None

            qtd = qtd_hom if qtd_hom is not None else qtd_est
            valor_unit = vu_hom if vu_hom is not None else vu_est
            valor_total = vt_hom if vt_hom is not None else vt_est

            material_servico = str(r.get("materialOuServicoNome") or r.get("tipoItemNome") or "").strip()
            unidade = str(r.get("unidadeMedida") or r.get("unidadeFornecimentoNome") or "").strip()
            fingerprint = (
                f"item:{numero_item}" if numero_item else f"{desc}|{qtd}|{unidade}|{valor_unit}|{valor_total}"
            )
            raw_blob = zlib.compress(json.dumps(r, ensure_ascii=False).encode("utf-8"), level=6)
            sit_item_row = str(
                r.get("situacaoCompraItemNome") or r.get("situacaoCompraItem") or ""
            ).strip()
            elegivel = 1 if item_elegivel(r, situacao_compra=sit_compra_row) else 0

            if isinstance(resultado, dict):
                res = resolve_from_resultados_payload(
                    resultado,
                    numero_item=numero_item or None,
                    situacao_compra=sit_compra_row,
                    fonte_prefix="pncp_resultado_ingest",
                )
            else:
                res = resolve_from_item_catalog_row(r, situacao_compra=sit_compra_row)
            cnpj_forn = str(res.cnpj_fornecedor or "").strip()
            fornecedor = str(res.fornecedor or "").strip()
            fornecedor_fonte = str(res.fornecedor_fonte or "").strip()
            fornecedor_resolvido_at = now if (cnpj_forn or fornecedor) else None
            resultado_resolvido_at = now if has_homolog else None

            values = (
                numero,
                ano,
                seq,
                numero_item,
                desc,
                material_servico,
                qtd,
                unidade,
                valor_unit,
                valor_total,
                org.get("razaoSocial") or org.get("razaosocial"),
                unid.get("municipioNome"),
                unid.get("ufSigla"),
                modalidade_nome,
                data_pub,
                fingerprint,
                now,
                raw_blob,
                sit_item_row,
                sit_compra_row,
                elegivel,
                cnpj_forn or None,
                fornecedor or None,
                fornecedor_fonte or None,
                vu_est,
                vt_est,
                qtd_est,
                vu_hom,
                vt_hom,
                qtd_hom,
                resultado_resolvido_at,
                fornecedor_resolvido_at,
            )
            updated = False
            if numero_item:
                cur = c.execute(
                    """
                    UPDATE pncp_itens SET
                        ano_compra=?, sequencial_compra=?, descricao=?, material_servico=?,
                        quantidade=?, unidade_medida=?, valor_unitario=?, valor_total=?,
                        orgao=?, municipio=?, uf=?, modalidade_nome=?, data_publicacao=?,
                        item_fingerprint=?, updated_at=?, raw_json_zlib=?,
                        situacao_item=?, situacao_compra=?, fornecedor_elegivel=?,
                        cnpj_fornecedor=?, fornecedor=?, fornecedor_fonte=?,
                        valor_unitario_estimado=?, valor_total_estimado=?, quantidade_estimada=?,
                        valor_unitario_homologado=?, valor_total_homologado=?, quantidade_homologada=?,
                        resultado_resolvido_at=COALESCE(?, resultado_resolvido_at),
                        fornecedor_resolvido_at=COALESCE(?, fornecedor_resolvido_at)
                    WHERE numero_pncp=? AND numero_item=?
                    """,
                    (
                        ano,
                        seq,
                        desc,
                        material_servico,
                        qtd,
                        unidade,
                        valor_unit,
                        valor_total,
                        org.get("razaoSocial") or org.get("razaosocial"),
                        unid.get("municipioNome"),
                        unid.get("ufSigla"),
                        modalidade_nome,
                        data_pub,
                        fingerprint,
                        now,
                        raw_blob,
                        sit_item_row,
                        sit_compra_row,
                        elegivel,
                        cnpj_forn or None,
                        fornecedor or None,
                        fornecedor_fonte or None,
                        vu_est,
                        vt_est,
                        qtd_est,
                        vu_hom,
                        vt_hom,
                        qtd_hom,
                        resultado_resolvido_at,
                        fornecedor_resolvido_at,
                        numero,
                        numero_item,
                    ),
                )
                updated = int(cur.rowcount or 0) > 0
            if not updated:
                c.execute(
                    """
                    INSERT INTO pncp_itens (
                        numero_pncp, ano_compra, sequencial_compra, numero_item, descricao, material_servico,
                        quantidade, unidade_medida, valor_unitario, valor_total, orgao, municipio, uf,
                        modalidade_nome, data_publicacao, item_fingerprint, updated_at, raw_json_zlib,
                        situacao_item, situacao_compra, fornecedor_elegivel,
                        cnpj_fornecedor, fornecedor, fornecedor_fonte,
                        valor_unitario_estimado, valor_total_estimado, quantidade_estimada,
                        valor_unitario_homologado, valor_total_homologado, quantidade_homologada,
                        resultado_resolvido_at, fornecedor_resolvido_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(numero_pncp, item_fingerprint) DO UPDATE SET
                        ano_compra=excluded.ano_compra,
                        sequencial_compra=excluded.sequencial_compra,
                        numero_item=excluded.numero_item,
                        descricao=excluded.descricao,
                        material_servico=excluded.material_servico,
                        quantidade=excluded.quantidade,
                        unidade_medida=excluded.unidade_medida,
                        valor_unitario=excluded.valor_unitario,
                        valor_total=excluded.valor_total,
                        orgao=excluded.orgao,
                        municipio=excluded.municipio,
                        uf=excluded.uf,
                        modalidade_nome=excluded.modalidade_nome,
                        data_publicacao=excluded.data_publicacao,
                        updated_at=excluded.updated_at,
                        raw_json_zlib=excluded.raw_json_zlib,
                        situacao_item=excluded.situacao_item,
                        situacao_compra=excluded.situacao_compra,
                        fornecedor_elegivel=excluded.fornecedor_elegivel,
                        cnpj_fornecedor=excluded.cnpj_fornecedor,
                        fornecedor=excluded.fornecedor,
                        fornecedor_fonte=excluded.fornecedor_fonte,
                        valor_unitario_estimado=excluded.valor_unitario_estimado,
                        valor_total_estimado=excluded.valor_total_estimado,
                        quantidade_estimada=excluded.quantidade_estimada,
                        valor_unitario_homologado=excluded.valor_unitario_homologado,
                        valor_total_homologado=excluded.valor_total_homologado,
                        quantidade_homologada=excluded.quantidade_homologada,
                        resultado_resolvido_at=COALESCE(excluded.resultado_resolvido_at, resultado_resolvido_at),
                        fornecedor_resolvido_at=COALESCE(excluded.fornecedor_resolvido_at, fornecedor_resolvido_at)
                    """,
                    values,
                )
            count += 1
    return count


def supplier_coverage_stats() -> Dict[str, Any]:
    """Métricas de cobertura de fornecedor (Fase A — leitura; preenchimento nas fases B/C)."""
    ensure_local_index()
    with _conn() as c:
        row = c.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN TRIM(COALESCE(cnpj_fornecedor,'')) != '' THEN 1 ELSE 0 END) AS com_cnpj,
                SUM(CASE WHEN TRIM(COALESCE(fornecedor,'')) != '' THEN 1 ELSE 0 END) AS com_nome,
                SUM(CASE WHEN fornecedor_elegivel = 1 THEN 1 ELSE 0 END) AS elegiveis,
                SUM(
                    CASE WHEN fornecedor_elegivel = 1
                         AND TRIM(COALESCE(cnpj_fornecedor,'')) != ''
                         AND TRIM(COALESCE(fornecedor,'')) != ''
                    THEN 1 ELSE 0 END
                ) AS elegiveis_completos
            FROM pncp_itens
            """
        ).fetchone()
        cache = cache_stats(c)
    total = int(row["total"] or 0)
    com_cnpj = int(row["com_cnpj"] or 0)
    com_nome = int(row["com_nome"] or 0)
    elegiveis = int(row["elegiveis"] or 0)
    elegiveis_ok = int(row["elegiveis_completos"] or 0)

    def _pct(num: int, den: int) -> float:
        if den <= 0:
            return 0.0
        return round(100.0 * num / den, 2)

    return {
        "total_itens": total,
        "itens_com_cnpj_fornecedor": com_cnpj,
        "itens_com_nome_fornecedor": com_nome,
        "itens_elegiveis": elegiveis,
        "itens_elegiveis_com_cnpj_e_nome": elegiveis_ok,
        "cobertura_cnpj_pct": _pct(com_cnpj, total),
        "cobertura_nome_pct": _pct(com_nome, total),
        "cobertura_elegivel_pct": _pct(elegiveis_ok, elegiveis),
        **cache,
    }


def local_index_stats() -> Dict[str, Any]:
    ensure_local_index()
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) AS n FROM pncp_contratos").fetchone()["n"]
        total_itens = c.execute("SELECT COUNT(*) AS n FROM pncp_itens").fetchone()["n"]
        by_uf_rows = c.execute(
            "SELECT COALESCE(uf,'') AS uf, COUNT(*) AS n FROM pncp_contratos GROUP BY uf ORDER BY n DESC LIMIT 27"
        ).fetchall()
        by_modal_rows = c.execute(
            "SELECT COALESCE(modalidade_nome,'') AS modalidade, COUNT(*) AS n FROM pncp_contratos GROUP BY modalidade_nome ORDER BY n DESC LIMIT 20"
        ).fetchall()
    out = {
        "ok": True,
        "db_path": PNCP_LOCAL_DB_PATH,
        "total_contratos": int(total or 0),
        "total_itens": int(total_itens or 0),
        "por_uf": [{"uf": r["uf"], "total": r["n"]} for r in by_uf_rows],
        "por_modalidade": [{"modalidade": r["modalidade"], "total": r["n"]} for r in by_modal_rows],
    }
    out["fornecedor"] = supplier_coverage_stats()
    return out


def local_search(
    termo_busca: str,
    *,
    uf: Optional[str] = None,
    codigo_modalidade: Optional[int] = None,
    limit: int = 200,
) -> Dict[str, Any]:
    ensure_local_index()
    term = (termo_busca or "").strip()
    if not term:
        return {"ok": True, "itens": [], "stats": {"total_registros": 0}}
    where = ["objeto LIKE ?"]
    params: List[Any] = [f"%{term}%"]
    if uf:
        where.append("uf = ?")
        params.append(uf)
    if codigo_modalidade is not None:
        where.append("modalidade_codigo = ?")
        params.append(int(codigo_modalidade))
    sql = f"""
        SELECT numero_pncp, objeto, orgao, municipio, uf, modalidade_nome, valor_global,
               situacao, ano_compra, sequencial_compra
        FROM pncp_contratos
        WHERE {' AND '.join(where)}
        ORDER BY updated_at DESC
        LIMIT ?
    """
    params.append(max(1, min(int(limit), 2000)))
    with _conn() as c:
        rows = c.execute(sql, params).fetchall()
    itens = [
        {
            "numero_pncp": r["numero_pncp"],
            "objeto_resumido": r["objeto"],
            "orgao": r["orgao"],
            "municipio": r["municipio"],
            "uf": r["uf"],
            "modalidade": r["modalidade_nome"],
            "valor_global": r["valor_global"],
            "situacao": r["situacao"],
            "ano_compra": r["ano_compra"],
            "sequencial_compra": r["sequencial_compra"],
            "origem": "base_local",
        }
        for r in rows
    ]
    return {"ok": True, "itens": itens, "stats": {"total_registros": len(itens)}}


def _normalize_search_text(text: str) -> str:
    return normalize_for_search(text or "")


def _token_variants(token: str) -> List[str]:
    t = _normalize_search_text(token)
    if not t:
        return []
    variants = {t}
    # plural/singular simples para aumentar recall (pneu <-> pneus)
    if t.endswith("s") and len(t) > 3:
        variants.add(t[:-1])
    else:
        variants.add(f"{t}s")
    return sorted(v for v in variants if v)


def _build_search_tokens(termo_busca: str) -> List[List[str]]:
    norm = _normalize_search_text(termo_busca)
    if not norm:
        return []
    raw_tokens = [tok for tok in norm.split(" ") if len(tok) >= 2]
    return [_token_variants(tok) for tok in raw_tokens if _token_variants(tok)]


_SEARCH_ANCHOR_DROP = frozenset(
    {
        "cx",
        "un",
        "und",
        "pct",
        "ref",
        "tipo",
        "modelo",
        "marca",
        "item",
        "itens",
        "para",
        "com",
    }
)


def derive_anchor_search_term(
    termo_busca: str,
    *,
    max_groups: Optional[int] = None,
    full_term_max: Optional[int] = None,
) -> tuple[str, Dict[str, Any]]:
    """
    Descrições longas de cotação geram AND de dezenas de tokens — recall ~0.
    Até ``full_term_max`` tokens: busca com todos; acima: cap de ``max_groups`` âncoras.
    """
    from .config import PNCP_SEARCH_ANCHOR_FULL_TERM_MAX, PNCP_SEARCH_ANCHOR_MAX_GROUPS

    cap = max(2, int(max_groups if max_groups is not None else PNCP_SEARCH_ANCHOR_MAX_GROUPS))
    full_max = max(2, int(full_term_max if full_term_max is not None else PNCP_SEARCH_ANCHOR_FULL_TERM_MAX))
    raw = (termo_busca or "").strip()
    groups = _build_search_tokens(raw)
    meta: Dict[str, Any] = {
        "termo_original": raw,
        "termo_original_tokens": len(groups),
        "termo_efetivo_tokens": len(groups),
        "termo_truncado": False,
        "termo_efetivo": raw,
    }
    if not groups:
        return raw, meta
    if len(groups) <= full_max:
        return raw, meta
    picked: List[str] = []
    for variants in groups:
        anchor = variants[0]
        if anchor in _SEARCH_ANCHOR_DROP:
            continue
        picked.append(anchor)
        if len(picked) >= cap:
            break
    if len(picked) < 2:
        picked = [g[0] for g in groups[:cap]]
    meta["termo_truncado"] = True
    meta["termo_efetivo_tokens"] = len(picked)
    meta["termo_efetivo"] = " ".join(picked)
    return meta["termo_efetivo"], meta


def _search_token_hit(opt: str, words: set[str], normalized_text: str) -> bool:
    if opt in words or opt in normalized_text:
        return True
    # ex.: busca "120ml" vs descrição "120 ml" ou "frasco 120 ml"
    m = re.match(r"^(\d+(?:[.,]\d+)?)(ml|mg|g|kg|l|lt|mcg|ui|un|und|cp|caps)$", opt)
    if m:
        num, unit = m.group(1), m.group(2)
        num_norm = num.replace(",", ".")
        if num_norm in words and unit in words:
            return True
        compact = normalized_text.replace(" ", "")
        if f"{num_norm}{unit}" in compact or f"{num}{unit}" in compact:
            return True
    return False


def _row_matches_search_tokens(text: str, tokens: List[List[str]]) -> bool:
    if not tokens:
        return False
    normalized_text = _normalize_search_text(text)
    if not normalized_text:
        return False
    words = set(normalized_text.split())
    for options in tokens:
        # cada token de busca deve casar ao menos uma variante (AND entre tokens)
        matched = any(_search_token_hit(opt, words, normalized_text) for opt in options)
        if not matched:
            return False
    return True


def _decompress_zlib_json_blob(raw_blob: Any) -> Optional[Dict[str, Any]]:
    if not raw_blob:
        return None
    try:
        if isinstance(raw_blob, memoryview):
            raw_blob = raw_blob.tobytes()
        if isinstance(raw_blob, (bytes, bytearray)):
            payload = zlib.decompress(raw_blob)
            raw = json.loads(payload.decode("utf-8"))
        else:
            return None
    except Exception:
        return None
    return raw if isinstance(raw, dict) else None


def _situacao_compra_from_contract_blob(contrato_raw_json: Any) -> str:
    raw = contrato_raw_json
    if isinstance(contrato_raw_json, (bytes, bytearray, memoryview)):
        try:
            raw = bytes(contrato_raw_json).decode("utf-8")
        except Exception:
            return ""
    if not raw:
        return ""
    try:
        data = json.loads(str(raw))
    except Exception:
        return ""
    if not isinstance(data, dict):
        return ""
    return str(data.get("situacaoCompraNome") or data.get("situacao") or "").strip()


def _row_get(r: sqlite3.Row, key: str, default: Any = None) -> Any:
    try:
        val = r[key]
    except (KeyError, IndexError):
        return default
    return default if val is None else val


def _supplier_fields_from_local_row(r: sqlite3.Row) -> Dict[str, Any]:
    """
    Fornecedor para busca local: colunas persistidas (futuro) ou JSON do item em raw_json_zlib.
    """
    cnpj_db = str(_row_get(r, "cnpj_fornecedor", "") or "").strip()
    nome_db = str(_row_get(r, "fornecedor", "") or "").strip()
    fonte_db = str(_row_get(r, "fornecedor_fonte", "") or "").strip()
    elegivel_db = _row_get(r, "fornecedor_elegivel", 0)

    if cnpj_db and nome_fornecedor_e_util(nome_db):
        out: Dict[str, Any] = {
            "cnpj_fornecedor": cnpj_db,
            "fornecedor": nome_db,
            "fornecedor_fonte": fonte_db or "indice_local",
        }
        if fonte_db:
            out["fornecedor_fonte_nome"] = fonte_db
        if int(elegivel_db or 0) == 1:
            out["fornecedor_elegivel"] = True
        return out

    sit_compra = str(_row_get(r, "situacao_compra", "") or "").strip()
    if not sit_compra:
        sit_compra = _situacao_compra_from_contract_blob(_row_get(r, "contrato_raw_json"))

    catalog = _decompress_zlib_json_blob(_row_get(r, "raw_json_zlib"))
    if not catalog:
        if cnpj_db:
            return {
                "cnpj_fornecedor": cnpj_db,
                "fornecedor": nome_db,
                "fornecedor_fonte": fonte_db or "indice_local",
            }
        return {}

    res = resolve_from_item_catalog_row(catalog, situacao_compra=sit_compra)
    if not res.cnpj_fornecedor and not res.fornecedor:
        if cnpj_db:
            return {"cnpj_fornecedor": cnpj_db, "fornecedor": nome_db}
        return {}

    out = resolution_to_api_dict(res)
    out["fornecedor_origem_indice"] = "raw_json_catalog"
    if out.get("fornecedor") and out.get("fornecedor_fonte") and "fornecedor_fonte_nome" not in out:
        out["fornecedor_fonte_nome"] = str(out.get("fornecedor_fonte") or "")
    return out


def _extract_esfera_from_raw_blob(raw_blob: Any) -> tuple[Optional[str], Optional[str], Optional[str]]:
    if not raw_blob:
        return None, None, None
    try:
        if isinstance(raw_blob, memoryview):
            raw_blob = raw_blob.tobytes()
        if isinstance(raw_blob, (bytes, bytearray)):
            payload = zlib.decompress(raw_blob)
            raw = json.loads(payload.decode("utf-8"))
        else:
            return None, None, None
    except Exception:
        return None, None, None
    if not isinstance(raw, dict):
        return None, None, None
    org = raw.get("orgaoEntidade") or {}
    sub = raw.get("orgaoSubRogado") or {}
    esfera = str(org.get("esferaId") or sub.get("esferaId") or "").strip().upper()
    poder = str(org.get("poderId") or sub.get("poderId") or "").strip().upper()
    if esfera == "F":
        esfera_adm = "federal"
    elif esfera == "E":
        esfera_adm = "estadual"
    elif esfera == "M":
        esfera_adm = "municipal"
    elif esfera == "D":
        esfera_adm = "distrital"
    else:
        esfera = ""
        esfera_adm = None
    return (esfera or None), esfera_adm, (poder or None)


def _extract_esfera_from_contract_raw_json(raw_json_text: Any) -> tuple[Optional[str], Optional[str], Optional[str]]:
    if not raw_json_text:
        return None, None, None
    try:
        if isinstance(raw_json_text, (bytes, bytearray, memoryview)):
            raw_json_text = bytes(raw_json_text).decode("utf-8")
        raw = json.loads(str(raw_json_text))
    except Exception:
        return None, None, None
    if not isinstance(raw, dict):
        return None, None, None
    org = raw.get("orgaoEntidade") or {}
    sub = raw.get("orgaoSubRogado") or {}
    esfera = str(org.get("esferaId") or sub.get("esferaId") or "").strip().upper()
    poder = str(org.get("poderId") or sub.get("poderId") or "").strip().upper()
    if esfera == "F":
        esfera_adm = "federal"
    elif esfera == "E":
        esfera_adm = "estadual"
    elif esfera == "M":
        esfera_adm = "municipal"
    elif esfera == "D":
        esfera_adm = "distrital"
    else:
        esfera = ""
        esfera_adm = None
    return (esfera or None), esfera_adm, (poder or None)


def _normalize_recortes_geograficos(recortes_geograficos: Optional[List[Any]]) -> List[Dict[str, Optional[str]]]:
    out: List[Dict[str, Optional[str]]] = []
    if not recortes_geograficos:
        return out
    seen: set = set()
    for raw in recortes_geograficos:
        if raw is None:
            continue
        if isinstance(raw, dict):
            u = str(raw.get("uf") or "").strip().upper()[:2]
            m_raw = raw.get("municipio")
        else:
            u = str(getattr(raw, "uf", "") or "").strip().upper()[:2]
            m_raw = getattr(raw, "municipio", None)
        if len(u) != 2:
            continue
        m = (str(m_raw).strip() if m_raw is not None else "") or None
        key = (u, m or "")
        if key in seen:
            continue
        seen.add(key)
        out.append({"uf": u, "municipio": m})
        if len(out) >= 30:
            break
    return out


def _resolve_somente_homologados_flag(explicit: Optional[bool]) -> bool:
    if explicit is not None:
        return bool(explicit)
    return bool(PNCP_SEARCH_ONLY_HOMOLOGATED)


def _row_passes_homolog_filter(r: sqlite3.Row, *, somente_homologados: bool) -> bool:
    if not somente_homologados:
        return True
    sit_compra = str(_row_get(r, "situacao_compra", "") or _row_get(r, "situacao_compra", "") or "").strip()
    if not sit_compra:
        sit_compra = _situacao_compra_from_contract_blob(_row_get(r, "contrato_raw_json"))
    sit_item_db = str(_row_get(r, "situacao_item", "") or "").strip()
    if sit_item_db and item_homologado_para_busca(
        {"situacaoCompraItemNome": sit_item_db}, situacao_compra=sit_compra
    ):
        return True
    catalog = _decompress_zlib_json_blob(_row_get(r, "raw_json_zlib"))
    if isinstance(catalog, dict):
        return item_homologado_para_busca(catalog, situacao_compra=sit_compra)
    return False


async def enrich_homolog_items_from_pncp(
    itens: List[Dict[str, Any]],
    *,
    max_n: int,
) -> int:
    """Consulta /resultados (+ contratos) para homologados sem CNPJ no índice."""
    if max_n <= 0 or not itens:
        return 0
    from .pncp_client import get_contract_supplier_snapshot, create_pncp_http_client

    enriched = 0
    client = create_pncp_http_client()
    try:
        for entry in itens:
            if enriched >= max_n:
                break
            if str(entry.get("cnpj_fornecedor") or "").strip():
                continue
            if not entry.get("item_homologado"):
                continue
            cnpj = re.sub(r"\D", "", str(entry.get("numero_pncp") or "").split("-")[0])
            ano = entry.get("ano_compra")
            seq = entry.get("sequencial_compra")
            ni = str(entry.get("numero_item") or "").strip()
            if len(cnpj) != 14 or not ano or not seq:
                continue
            snap = await get_contract_supplier_snapshot(
                cnpj,
                ano,
                seq,
                numero_item=ni or None,
                situacao_compra=str(entry.get("situacao_compra") or entry.get("situacao") or ""),
                client=client,
            )
            if not str(snap.get("cnpj_fornecedor") or "").strip():
                continue
            entry.update({k: v for k, v in snap.items() if v})
            entry["fornecedor_busca_pncp"] = True
            enriched += 1
    finally:
        await client.aclose()
    return enriched


def _enrich_homolog_items_from_pncp_sync(itens: List[Dict[str, Any]], *, max_n: int) -> int:
    """
    Wrapper síncrono — só funciona fora de event loop (scripts/CLI).
    Handlers FastAPI devem usar ``await enrich_homolog_items_from_pncp(...)``.
    """
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(enrich_homolog_items_from_pncp(itens, max_n=max_n))
    return 0


async def enrich_local_search_result(
    result: Dict[str, Any],
    *,
    max_n: Optional[int] = None,
) -> Dict[str, Any]:
    """Enriquece fornecedor nos itens retornados por ``local_item_search`` (contexto async)."""
    itens = list(result.get("itens") or [])
    if not itens:
        return result
    cap = int(PNCP_SEARCH_ENRICH_HOMOLOG_MAX if max_n is None else max_n)
    enrich_n = await enrich_homolog_items_from_pncp(itens, max_n=max(0, cap))
    stats = dict(result.get("stats") or {})
    stats["enriquecidos_pncp_na_busca"] = enrich_n
    stats["itens_com_cnpj_fornecedor"] = sum(
        1 for it in itens if str(it.get("cnpj_fornecedor") or "").strip()
    )
    return {**result, "itens": itens, "stats": stats}


def _local_item_filter_clauses(
    *,
    uf: Optional[str],
    municipio: Optional[str],
    recortes_geograficos: Optional[List[Any]],
    codigo_modalidade: Optional[int],
) -> tuple[List[str], List[Any]]:
    where: List[str] = []
    params: List[Any] = []
    rec_norm = _normalize_recortes_geograficos(recortes_geograficos)
    if rec_norm:
        geo_parts: List[str] = []
        for r in rec_norm:
            if r.get("municipio"):
                geo_parts.append(
                    "(i.uf = ? AND pncp_search_norm(COALESCE(i.municipio,'')) = pncp_search_norm(?))"
                )
                params.append(r["uf"])
                params.append(r["municipio"])
            else:
                geo_parts.append("(i.uf = ?)")
                params.append(r["uf"])
        where.append("(" + " OR ".join(geo_parts) + ")")
    elif uf:
        where.append("i.uf = ?")
        params.append(uf)
        muni = (municipio or "").strip()
        if muni:
            where.append("pncp_search_norm(COALESCE(i.municipio, '')) = pncp_search_norm(?)")
            params.append(muni)
    else:
        muni = (municipio or "").strip()
        if muni:
            where.append("pncp_search_norm(COALESCE(i.municipio, '')) = pncp_search_norm(?)")
            params.append(muni)
    if codigo_modalidade is not None:
        modalidade_patterns = {
            6: ["concorr"],
            7: ["chamada publica", "chamada pública"],
            8: ["pregao", "pregão"],
            9: ["dispensa", "compra direta"],
            10: ["inexigibilidade"],
            11: ["leilao", "leilão"],
            12: ["concurso"],
            13: ["dialogo competitivo", "diálogo competitivo"],
        }.get(int(codigo_modalidade), [])
        if modalidade_patterns:
            where.append(
                "(" + " OR ".join(["LOWER(COALESCE(i.modalidade_nome, '')) LIKE ?" for _ in modalidade_patterns]) + ")"
            )
            params.extend([f"%{pattern}%" for pattern in modalidade_patterns])
    return where, params


def _row_to_local_item(
    r: sqlite3.Row,
    *,
    cleanup_for_display: bool,
    origem: str = "base_local_itens",
) -> Dict[str, Any]:
    esfera_id, esfera_adm, poder_id = _extract_esfera_from_raw_blob(r["raw_json_zlib"])
    if not esfera_id:
        esfera_id, esfera_adm, poder_id = _extract_esfera_from_contract_raw_json(r["contrato_raw_json"])
    entry: Dict[str, Any] = {
        "numero_pncp": r["numero_pncp"],
        "ano_compra": r["ano_compra"],
        "sequencial_compra": r["sequencial_compra"],
        "numero_item": r["numero_item"],
        "descricao_item": r["descricao"],
        "material_servico": r["material_servico"],
        "quantidade": r["quantidade"],
        "unidade_medida": r["unidade_medida"],
        "valor_unitario": r["valor_unitario"],
        "valor_total": r["valor_total"],
        "valor_unitario_estimado": _row_get(r, "valor_unitario_estimado"),
        "valor_total_estimado": _row_get(r, "valor_total_estimado"),
        "quantidade_estimada": _row_get(r, "quantidade_estimada"),
        "valor_unitario_homologado": _row_get(r, "valor_unitario_homologado"),
        "valor_total_homologado": _row_get(r, "valor_total_homologado"),
        "quantidade_homologada": _row_get(r, "quantidade_homologada"),
        "orgao": r["orgao"],
        "municipio": r["municipio"],
        "uf": r["uf"],
        "modalidade": r["modalidade_nome"],
        "data_publicacao": r["data_publicacao"],
        "esfera_id": esfera_id,
        "esfera_administrativa": esfera_adm,
        "poder_id": poder_id,
        "origem": origem,
    }
    situacao_compra = str(_row_get(r, "situacao_compra", "") or "").strip()
    if situacao_compra:
        entry["situacao"] = situacao_compra
        entry["situacao_compra"] = situacao_compra
    catalog = _decompress_zlib_json_blob(_row_get(r, "raw_json_zlib"))
    if isinstance(catalog, dict):
        if catalog.get("temResultado") is not None:
            entry["temResultado"] = bool(catalog.get("temResultado"))
        sit_item = str(catalog.get("situacaoCompraItemNome") or catalog.get("situacaoCompraItem") or "").strip()
        if sit_item:
            entry["situacaoCompraItemNome"] = sit_item
    entry.update(_supplier_fields_from_local_row(r))
    if cleanup_for_display:
        apply_item_display_cleanup(entry)
    return entry


def local_item_search(
    termo_busca: str,
    *,
    uf: Optional[str] = None,
    municipio: Optional[str] = None,
    recortes_geograficos: Optional[List[Any]] = None,
    codigo_modalidade: Optional[int] = None,
    limit: int = 500,
    cleanup_for_display: bool = True,
    somente_homologados: Optional[bool] = None,
) -> Dict[str, Any]:
    ensure_local_index()
    only_homolog = _resolve_somente_homologados_flag(somente_homologados)
    termo_efetivo, term_meta = derive_anchor_search_term(termo_busca)
    token_groups = _build_search_tokens(termo_efetivo)
    if not token_groups:
        return {
            "ok": True,
            "itens": [],
            "stats": {
                "total_registros": 0,
                "search_engine": "none",
                "somente_homologados": only_homolog,
                "termo_busca": term_meta,
            },
        }

    filter_where, filter_params = _local_item_filter_clauses(
        uf=uf,
        municipio=municipio,
        recortes_geograficos=recortes_geograficos,
        codigo_modalidade=codigo_modalidade,
    )
    sql_limit = max(1, min(int(limit) * 8, 20000))
    fts_meta = fts_index_status()
    fts_match = _build_fts_match_query(termo_efetivo) if PNCP_FTS5_ENABLED else None
    use_fts = bool(
        PNCP_FTS5_ENABLED
        and fts_meta.get("ready")
        and fts_match
        and not fts_meta.get("needs_rebuild")
    )
    search_engine = "fts5_anchor" if use_fts else "like_anchor"

    select_cols = """
        SELECT i.numero_pncp, i.ano_compra, i.sequencial_compra, i.numero_item, i.descricao, i.material_servico,
               i.quantidade, i.unidade_medida, i.valor_unitario, i.valor_total,
               i.valor_unitario_estimado, i.valor_total_estimado, i.quantidade_estimada,
               i.valor_unitario_homologado, i.valor_total_homologado, i.quantidade_homologada,
               i.orgao, i.municipio, i.uf,
               i.modalidade_nome, i.data_publicacao, i.raw_json_zlib,
               i.cnpj_fornecedor, i.fornecedor, i.fornecedor_fonte, i.fornecedor_elegivel,
               c.raw_json AS contrato_raw_json, c.situacao AS situacao_compra
    """

    def _like_anchor_sql() -> tuple[str, List[Any]]:
        anchor = token_groups[0][0]
        where = ["i.descricao LIKE ?"]
        pr: List[Any] = [f"%{anchor}%"]
        where.extend(filter_where)
        sql_like = f"""
            {select_cols}
            FROM pncp_itens i
            LEFT JOIN pncp_contratos c ON c.numero_pncp = i.numero_pncp
            WHERE {' AND '.join(where)}
            ORDER BY i.updated_at DESC
            LIMIT ?
        """
        return sql_like, pr + list(filter_params) + [sql_limit]

    if use_fts:
        where = ["pncp_itens_fts MATCH ?"]
        params: List[Any] = [fts_match]
        where.extend(filter_where)
        sql = f"""
            {select_cols}, bm25(pncp_itens_fts) AS fts_rank
            FROM pncp_itens_fts
            JOIN pncp_itens i ON i.id = pncp_itens_fts.rowid
            LEFT JOIN pncp_contratos c ON c.numero_pncp = i.numero_pncp
            WHERE {' AND '.join(where)}
            ORDER BY fts_rank
            LIMIT ?
        """
        params = list(params) + list(filter_params) + [sql_limit]
    else:
        sql, params = _like_anchor_sql()

    rows: List[sqlite3.Row] = []
    try:
        with _conn() as c:
            rows = c.execute(sql, params).fetchall()
        if use_fts and not rows:
            logger.info("local_item_search fts5_anchor retornou 0 linhas; fallback LIKE")
            search_engine = "fts5_empty_fallback_like"
            sql_fb, params_fb = _like_anchor_sql()
            with _conn() as c:
                rows = c.execute(sql_fb, params_fb).fetchall()
    except sqlite3.OperationalError as e:
        logger.warning("local_item_search %s falhou (%s); fallback LIKE", search_engine, e)
        use_fts = False
        search_engine = "like_anchor"
        sql_fb, params_fb = _like_anchor_sql()
        with _conn() as c:
            rows = c.execute(sql_fb, params_fb).fetchall()

    itens: List[Dict[str, Any]] = []
    com_fornecedor = 0
    filtrados_nao_homolog = 0
    filtrados_token = 0
    candidatos_enrich: List[Dict[str, Any]] = []
    for r in rows:
        desc = r["descricao"] or ""
        mat = r["material_servico"] or ""
        texto_item = f"{desc} {mat}".strip()
        if not _row_matches_search_tokens(texto_item, token_groups):
            filtrados_token += 1
            continue
        if only_homolog and not _row_passes_homolog_filter(r, somente_homologados=True):
            filtrados_nao_homolog += 1
            continue
        entry = _row_to_local_item(r, cleanup_for_display=cleanup_for_display)
        sit_compra = str(entry.get("situacao_compra") or entry.get("situacao") or "").strip()
        catalog = _decompress_zlib_json_blob(_row_get(r, "raw_json_zlib"))
        homolog = item_homologado_para_busca(
            catalog if isinstance(catalog, dict) else {},
            situacao_compra=sit_compra,
        )
        entry["item_homologado"] = homolog
        if str(entry.get("situacaoCompraItemNome") or "").strip():
            entry["situacao_item_exibicao"] = entry.get("situacaoCompraItemNome")
        if str(entry.get("cnpj_fornecedor") or "").strip():
            com_fornecedor += 1
        elif homolog:
            candidatos_enrich.append(entry)
        itens.append(entry)
        if len(itens) >= max(1, min(int(limit), 5000)):
            break

    enrich_max = max(0, int(PNCP_SEARCH_ENRICH_HOMOLOG_MAX))
    enrich_n = 0
    if enrich_max and candidatos_enrich:
        enrich_n = _enrich_homolog_items_from_pncp_sync(candidatos_enrich, max_n=enrich_max)
        com_fornecedor = sum(1 for it in itens if str(it.get("cnpj_fornecedor") or "").strip())

    return {
        "ok": True,
        "itens": itens,
        "stats": {
            "total_registros": len(itens),
            "itens_com_cnpj_fornecedor": com_fornecedor,
            "search_engine": search_engine,
            "fts_needs_rebuild": bool(fts_meta.get("needs_rebuild")),
            "somente_homologados": only_homolog,
            "sql_rows_fetched": len(rows),
            "filtrados_token_match": filtrados_token,
            "filtrados_nao_homologados": filtrados_nao_homolog,
            "enriquecidos_pncp_na_busca": enrich_n,
            "termo_busca": term_meta,
        },
    }


def create_research_session(
    *,
    titulo: str,
    termo_busca: str,
    modelo_cotacao: str = "pesquisa_precos_padrao",
    filtros: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ensure_local_index()
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    filtros_json = json.dumps(filtros or {}, ensure_ascii=False)
    titulo_s = (titulo or "").strip()
    termo_s = (termo_busca or "").strip()
    modelo_s = (modelo_cotacao or "").strip() or "pesquisa_precos_padrao"
    with _conn() as c:
        cur = c.execute(
            """
            INSERT INTO pesquisador_sessoes (
                titulo, termo_busca, filtros_json, status, modelo_cotacao, created_at, updated_at
            )
            VALUES (?, ?, ?, 'aberta', ?, ?, ?)
            """,
            (titulo_s, termo_s, filtros_json, modelo_s, now, now),
        )
        sessao_id = int(cur.lastrowid)
    cotacao = {
        "id": sessao_id,
        "titulo": titulo_s,
        "termo_busca": termo_s,
        "modelo_cotacao": modelo_s,
        "filtros": filtros or {},
        "status": "aberta",
        "created_at": now,
    }
    return {
        "ok": True,
        "sessao_id": sessao_id,
        "cotacao_id": sessao_id,
        "titulo": titulo_s,
        "termo_busca": termo_s,
        "modelo_cotacao": modelo_s,
        "filtros": filtros or {},
        "status": "aberta",
        "created_at": now,
        "cotacao": cotacao,
    }


def add_items_to_research_session(sessao_id: int, itens: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    ensure_local_index()
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    inserted = 0
    with _conn() as c:
        row = c.execute(
            "SELECT id FROM pesquisador_sessoes WHERE id = ?",
            (int(sessao_id),),
        ).fetchone()
        if not row:
            return {"ok": False, "error": "Sessão não encontrada.", "sessao_id": int(sessao_id)}
        for it in itens or []:
            if not isinstance(it, dict):
                continue
            source_blob = zlib.compress(json.dumps(it, ensure_ascii=False).encode("utf-8"), level=6)
            c.execute(
                """
                INSERT INTO pesquisador_sessao_itens (
                    sessao_id, numero_pncp, ano_compra, sequencial_compra, numero_item, descricao_item,
                    quantidade, unidade_medida, valor_unitario, valor_total, orgao, municipio, uf, modalidade,
                    source_json_zlib, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(sessao_id),
                    it.get("numero_pncp"),
                    it.get("ano_compra"),
                    it.get("sequencial_compra"),
                    it.get("numero_item"),
                    it.get("descricao_item") or it.get("descricao") or it.get("objeto_resumido"),
                    _safe_float(it.get("quantidade")),
                    it.get("unidade_medida"),
                    _safe_float(it.get("valor_unitario")),
                    _safe_float(it.get("valor_total")) or _safe_float(it.get("valor_global")),
                    it.get("orgao"),
                    it.get("municipio"),
                    it.get("uf"),
                    it.get("modalidade"),
                    source_blob,
                    now,
                ),
            )
            inserted += 1
        c.execute(
            "UPDATE pesquisador_sessoes SET updated_at = ? WHERE id = ?",
            (now, int(sessao_id)),
        )
    return {"ok": True, "sessao_id": int(sessao_id), "itens_inseridos": inserted}


def get_research_session(sessao_id: int) -> Dict[str, Any]:
    ensure_local_index()
    with _conn() as c:
        s = c.execute(
            """
            SELECT id, titulo, termo_busca, filtros_json, status, modelo_cotacao, created_at, updated_at
            FROM pesquisador_sessoes
            WHERE id = ?
            """,
            (int(sessao_id),),
        ).fetchone()
        if not s:
            return {"ok": False, "error": "Sessão não encontrada.", "sessao_id": int(sessao_id)}
        rows = c.execute(
            """
            SELECT id, numero_pncp, ano_compra, sequencial_compra, numero_item, descricao_item,
                   quantidade, unidade_medida, valor_unitario, valor_total, orgao, municipio, uf, modalidade, created_at
            FROM pesquisador_sessao_itens
            WHERE sessao_id = ?
            ORDER BY id DESC
            """,
            (int(sessao_id),),
        ).fetchall()
    return {
        "ok": True,
        "sessao": {
            "id": s["id"],
            "titulo": s["titulo"],
            "termo_busca": s["termo_busca"],
            "modelo_cotacao": s["modelo_cotacao"] or "pesquisa_precos_padrao",
            "filtros": json.loads(s["filtros_json"] or "{}"),
            "status": s["status"],
            "created_at": s["created_at"],
            "updated_at": s["updated_at"],
        },
        "itens": [
            {
                "id": r["id"],
                "numero_pncp": r["numero_pncp"],
                "ano_compra": r["ano_compra"],
                "sequencial_compra": r["sequencial_compra"],
                "numero_item": r["numero_item"],
                "descricao_item": r["descricao_item"],
                "quantidade": r["quantidade"],
                "unidade_medida": r["unidade_medida"],
                "valor_unitario": r["valor_unitario"],
                "valor_total": r["valor_total"],
                "orgao": r["orgao"],
                "municipio": r["municipio"],
                "uf": r["uf"],
                "modalidade": r["modalidade"],
                "created_at": r["created_at"],
            }
            for r in rows
        ],
        "stats": {"total_itens": len(rows)},
    }


def list_research_sessions(limit: int = 100) -> Dict[str, Any]:
    ensure_local_index()
    with _conn() as c:
        rows = c.execute(
            """
            SELECT s.id, s.titulo, s.termo_busca, s.status, s.modelo_cotacao, s.created_at, s.updated_at,
                   (SELECT COUNT(*) FROM pesquisador_sessao_itens si WHERE si.sessao_id = s.id) AS total_itens
            FROM pesquisador_sessoes s
            ORDER BY s.id DESC
            LIMIT ?
            """,
            (max(1, min(int(limit), 1000)),),
        ).fetchall()
    return {
        "ok": True,
        "sessoes": [
            {
                "id": r["id"],
                "titulo": r["titulo"],
                "termo_busca": r["termo_busca"],
                "modelo_cotacao": r["modelo_cotacao"] or "pesquisa_precos_padrao",
                "status": r["status"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "total_itens": r["total_itens"],
            }
            for r in rows
        ],
    }


def update_research_session(
    sessao_id: int,
    *,
    titulo: Optional[str] = None,
    status: Optional[str] = None,
    termo_busca: Optional[str] = None,
    modelo_cotacao: Optional[str] = None,
) -> Dict[str, Any]:
    ensure_local_index()
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with _conn() as c:
        row = c.execute(
            "SELECT id, titulo, status, termo_busca, modelo_cotacao FROM pesquisador_sessoes WHERE id = ?",
            (int(sessao_id),),
        ).fetchone()
        if not row:
            return {"ok": False, "error": "Sessão não encontrada.", "sessao_id": int(sessao_id)}

        next_titulo = row["titulo"] if titulo is None else str(titulo).strip()
        next_status = row["status"] if status is None else str(status).strip() or row["status"]
        next_termo = row["termo_busca"]
        if termo_busca is not None:
            t = str(termo_busca).strip()
            if t:
                next_termo = t
        base_modelo = row["modelo_cotacao"] or "pesquisa_precos_padrao"
        next_modelo = base_modelo
        if modelo_cotacao is not None:
            m = str(modelo_cotacao).strip()
            if m:
                next_modelo = m

        c.execute(
            """
            UPDATE pesquisador_sessoes
            SET titulo = ?, status = ?, termo_busca = ?, modelo_cotacao = ?, updated_at = ?
            WHERE id = ?
            """,
            (next_titulo, next_status, next_termo, next_modelo, now, int(sessao_id)),
        )

    return {
        "ok": True,
        "sessao_id": int(sessao_id),
        "titulo": next_titulo,
        "status": next_status,
        "termo_busca": next_termo,
        "modelo_cotacao": next_modelo,
        "updated_at": now,
    }


async def backfill_local_index(
    *,
    months: Optional[int] = None,
    days: Optional[int] = None,
    max_paginas: Optional[int] = None,
    tamanho_pagina: int = 50,
    uf: Optional[str] = None,
    codigo_municipio_ibge: Optional[str] = None,
    include_items: Optional[bool] = None,
) -> Dict[str, Any]:
    ensure_local_index()
    data_inicial, data_final, dias_efetivos = resolve_backfill_window(months=months, days=days)
    m = max(1, int(months or PNCP_LOCAL_BACKFILL_MONTHS))
    modalidades = PNCP_MODALIDADES_DEFAULT
    total_paginas = 0
    total_upserts = 0
    total_upserts_itens = 0
    erros_modalidade: List[Dict[str, Any]] = []
    use_items = PNCP_LOCAL_INCLUDE_ITEMS if include_items is None else bool(include_items)
    unlimited_pages = max_paginas is None or int(max_paginas) <= 0
    paginas_limite = 0 if unlimited_pages else int(max_paginas)
    async with create_pncp_http_client() as http:
        for modalidade in modalidades:
            pagina, resumed_from_watermark = _resolve_backfill_start_page(
                uf,
                modalidade,
                data_inicial=data_inicial,
                data_final=data_final,
            )
            pages_this_run = 0
            if resumed_from_watermark:
                logger.info(
                    "backfill resume modalidade=%s uf=%s pagina=%s",
                    modalidade,
                    uf or "*",
                    pagina,
                )
            while True:
                state = _get_ingest_state(uf, modalidade)
                pause_until = _parse_iso_utc(state["paused_until"]) if state else None
                if pause_until and pause_until > datetime.utcnow():
                    erros_modalidade.append(
                        {
                            "modalidade": modalidade,
                            "pagina": pagina,
                            "erro": "ingestao_pausada_automaticamente",
                            "paused_until": state["paused_until"],
                            "error_streak": int(state["error_streak"] or 0),
                            "error_kind": state["last_error_kind"],
                        }
                    )
                    break
                try:
                    batch = await search_contracts(
                        data_inicial=data_inicial,
                        data_final=data_final,
                        codigo_modalidade=modalidade,
                        uf=uf,
                        codigo_municipio_ibge=codigo_municipio_ibge,
                        pagina=pagina,
                        tamanho_pagina=tamanho_pagina,
                        tolerate_rate_limit=False,
                        client=http,
                    )
                except PNCPClientError as e:
                    ingest_err = _mark_ingest_error(
                        uf,
                        modalidade,
                        data_inicial=data_inicial,
                        data_final=data_final,
                        page=pagina,
                        message=str(e),
                    )
                    erros_modalidade.append(
                        {
                            "modalidade": modalidade,
                            "pagina": pagina,
                            "erro": str(e),
                            "error_kind": ingest_err["error_kind"],
                            "error_streak": ingest_err["error_streak"],
                            "paused_until": ingest_err["paused_until"],
                        }
                    )
                    # Em erro persistente de modalidade/página, segue para próxima modalidade.
                    break
                total_paginas += 1
                pages_this_run += 1
                if not batch:
                    logger.info(
                        "backfill fim lote vazio modalidade=%s pagina=%s uf=%s",
                        modalidade,
                        pagina,
                        uf or "*",
                    )
                    _mark_ingest_success(
                        uf,
                        modalidade,
                        data_inicial=data_inicial,
                        data_final=data_final,
                        page=0,
                        add_upserts=0,
                        add_item_upserts=0,
                    )
                    break
                total_upserts += upsert_contracts(batch)
                page_item_upserts = 0
                if use_items:
                    item_timeout = max(5.0, float(PNCP_BACKFILL_ITEM_TIMEOUT_SECONDS or 45))
                    item_sem = asyncio.Semaphore(
                        max(1, int(PNCP_BACKFILL_ITEM_CONCURRENCY or 12))
                    )
                    fetch_results = await asyncio.gather(
                        *[
                            _backfill_fetch_contract_items(
                                raw,
                                client=http,
                                item_timeout=item_timeout,
                                sem=item_sem,
                            )
                            for raw in batch
                        ],
                        return_exceptions=True,
                    )
                    for fetched in fetch_results:
                        if isinstance(fetched, Exception):
                            logger.warning("backfill erro itens lote: %s", fetched)
                            continue
                        raw, rows, resultados = fetched
                        if rows:
                            n = upsert_contract_items(raw, rows, resultados_by_item=resultados)
                            page_item_upserts += n
                            total_upserts_itens += n
                logger.info(
                    "backfill modalidade=%s pagina=%s uf=%s contratos=%s itens_pagina=%s "
                    "acum_contratos=%s acum_itens=%s",
                    modalidade,
                    pagina,
                    uf or "*",
                    len(batch),
                    page_item_upserts,
                    total_upserts,
                    total_upserts_itens,
                )
                end_of_catalog = len(batch) < 10
                _mark_ingest_success(
                    uf,
                    modalidade,
                    data_inicial=data_inicial,
                    data_final=data_final,
                    page=0 if end_of_catalog else pagina,
                    add_upserts=len(batch),
                    add_item_upserts=page_item_upserts,
                )
                if end_of_catalog:
                    break
                if (not unlimited_pages) and pages_this_run >= paginas_limite:
                    break
                pagina += 1
    stats = local_index_stats()
    stats.update(
        {
            "data_inicial": data_inicial,
            "data_final": data_final,
            "dias_lookback": dias_efetivos,
            "meses_lookback": m,
            "dias_lookback_max_api": PNCP_API_MAX_LOOKBACK_DAYS,
            "paginas_processadas": total_paginas,
            "upserts_executados": total_upserts,
            "upserts_itens_executados": total_upserts_itens,
            "include_items": use_items,
            "unbounded_paginas": unlimited_pages,
            "max_paginas_efetivo": None if unlimited_pages else paginas_limite,
            "watermark_resume": PNCP_INGEST_WATERMARK_RESUME,
            "erros_modalidade": erros_modalidade,
            "ingestao_operacional": ingest_operational_status(uf=uf),
        }
    )
    return stats
