from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from ...schema import platform_index_stats
from ....config import TCE_RS_LOCAL_DB_PATH
from .config import FIXTURES_DIR, PLATFORM_ID, TCE_RS_INGEST_DATA_DIR
from .materialize import materialize_tce_rs_parsed
from .parser import parse_tce_rs_directory


def _resolve_data_dir(data_dir: Optional[str]) -> Path:
    if data_dir and str(data_dir).strip():
        return Path(data_dir).expanduser().resolve()
    if TCE_RS_INGEST_DATA_DIR:
        return Path(TCE_RS_INGEST_DATA_DIR).expanduser().resolve()
    raise ValueError(
        "Informe data_dir no corpo da requisição ou configure TCE_RS_INGEST_DATA_DIR"
    )


def ingest_tce_rs_from_directory(
    data_dir: str | Path,
    *,
    max_rows: Optional[int] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Parse CSVs LicitaCon (layout provisório) e materializa no índice tce_rs."""
    directory = Path(data_dir).expanduser().resolve()
    if not directory.is_dir():
        raise FileNotFoundError(f"Diretório TCE-RS não encontrado: {directory}")

    parsed = parse_tce_rs_directory(directory, max_rows=max_rows)
    stats = materialize_tce_rs_parsed(parsed, db_path=db_path)
    index_stats = platform_index_stats(stats["db_path"])
    return {
        "ok": True,
        "platform_id": PLATFORM_ID,
        "parsed": {
            "data_dir": parsed.get("data_dir"),
            "files": parsed.get("files"),
            "licitacoes": len(parsed.get("licitacoes") or []),
            "itens": len(parsed.get("itens") or []),
            "propostas": len(parsed.get("propostas") or []),
        },
        "materialize": stats,
        "index_stats": index_stats,
        "search_ready": bool(index_stats.get("search_ready")),
    }


def ingest_tce_rs_sample(*, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Carrega fixtures locais para desenvolvimento e testes de integração."""
    if not FIXTURES_DIR.is_dir():
        raise FileNotFoundError(f"Fixtures TCE-RS ausentes: {FIXTURES_DIR}")
    return ingest_tce_rs_from_directory(FIXTURES_DIR, db_path=db_path)


def tce_rs_ingest_status(*, db_path: Optional[str] = None) -> Dict[str, Any]:
    path = (db_path or TCE_RS_LOCAL_DB_PATH).strip()
    stats = platform_index_stats(path)
    state: Dict[str, Any] = {}
    if stats.get("db_exists"):
        from ...connection import platform_conn

        with platform_conn(path) as c:
            row = c.execute(
                "SELECT scope_key, watermark, last_error, rows_total, updated_at "
                "FROM platform_ingest_state WHERE scope_key='tce_rs_full' LIMIT 1"
            ).fetchone()
            if row:
                state = dict(row)
    return {
        "ok": True,
        "platform_id": PLATFORM_ID,
        "db_path": path,
        "index_stats": stats,
        "ingest_state": state,
        "search_ready": bool(stats.get("search_ready")),
        "ckan_download": "not_implemented",
    }
