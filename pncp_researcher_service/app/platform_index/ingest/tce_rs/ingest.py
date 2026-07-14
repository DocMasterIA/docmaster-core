from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ...schema import platform_index_stats
from ....config import TCE_RS_LOCAL_DB_PATH
from .config import (
    FIXTURES_DIR,
    PLATFORM_ID,
    RAW_ROOT_DIR,
    TCE_RS_FILE_LICITACAO,
    TCE_RS_INGEST_DATA_DIR,
)
from .materialize import materialize_tce_rs_parsed
from .parser import find_csv_file, find_item_csv, parse_tce_rs_directory


def is_licitacon_year_dir(path: Path) -> bool:
    """Pasta de um ano com licitacao + item/itemw."""
    if not path.is_dir():
        return False
    lic = find_csv_file(path, TCE_RS_FILE_LICITACAO) or find_csv_file(path, "LICITACAO")
    item = find_item_csv(path)
    return bool(lic and item)


def discover_ingest_dirs(root: Path) -> List[Path]:
    """
    Aceita:
    - pasta de um ano (com CSVs direto);
    - pasta mãe com subpastas 2025/, 2026/, … cada uma com CSVs.
    """
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Diretório TCE-RS não encontrado: {root}")
    if is_licitacon_year_dir(root):
        return [root]
    year_dirs = [
        p
        for p in sorted(root.iterdir())
        if p.is_dir() and p.name.isdigit() and is_licitacon_year_dir(p)
    ]
    if year_dirs:
        return year_dirs
    raise FileNotFoundError(
        f"Nenhum CSV LicitaCon em {root} (esperado licitacao + item/itemw "
        f"na pasta ou em subpastas YYYY/)"
    )


def list_available_raw_years(raw_root: Optional[Path] = None) -> List[str]:
    root = (raw_root or RAW_ROOT_DIR).expanduser().resolve()
    if not root.is_dir():
        return []
    try:
        return [p.name for p in discover_ingest_dirs(root) if p.name.isdigit()]
    except FileNotFoundError:
        return []


def ingest_tce_rs_from_directory(
    data_dir: str | Path,
    *,
    max_rows: Optional[int] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parse CSVs LicitaCon e materializa no índice tce_rs.

    `data_dir` pode ser um ano (…/2025 ou …/2026) ou a raiz `raw/`
    (ingere todos os anos encontrados, upsert no mesmo SQLite).
    """
    directory = Path(data_dir).expanduser().resolve()
    year_dirs = discover_ingest_dirs(directory)

    per_year: List[Dict[str, Any]] = []
    last_stats: Dict[str, Any] = {}
    for year_dir in year_dirs:
        parsed = parse_tce_rs_directory(year_dir, max_rows=max_rows)
        stats = materialize_tce_rs_parsed(parsed, db_path=db_path)
        last_stats = stats
        per_year.append(
            {
                "data_dir": parsed.get("data_dir"),
                "year": year_dir.name if year_dir.name.isdigit() else None,
                "files": parsed.get("files"),
                "licitacoes": len(parsed.get("licitacoes") or []),
                "itens": len(parsed.get("itens") or []),
                "propostas": len(parsed.get("propostas") or []),
                "pessoas": len(parsed.get("pessoas") or []),
                "materialize": {
                    "itens_leitura_upserted": stats.get("itens_leitura_upserted"),
                    "itens_sem_preco": stats.get("itens_sem_preco"),
                    "preco_origem": stats.get("preco_origem"),
                },
            }
        )

    db = last_stats.get("db_path") or db_path or TCE_RS_LOCAL_DB_PATH
    index_stats = platform_index_stats(db)
    return {
        "ok": True,
        "platform_id": PLATFORM_ID,
        "years": [y.get("year") for y in per_year if y.get("year")],
        "parsed": {
            "data_dir": str(directory),
            "year_dirs": [str(p) for p in year_dirs],
            "licitacoes": sum(y["licitacoes"] for y in per_year),
            "itens": sum(y["itens"] for y in per_year),
            "propostas": sum(y["propostas"] for y in per_year),
            "by_year": per_year,
        },
        "materialize": last_stats,
        "index_stats": index_stats,
        "search_ready": bool(index_stats.get("search_ready")),
    }


def ingest_tce_rs_raw_years(
    *,
    max_rows: Optional[int] = None,
    db_path: Optional[str] = None,
    raw_root: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Ingere todas as pastas de ano sob data/tce_rs/raw (ou raw_root)."""
    root = Path(raw_root).expanduser().resolve() if raw_root else RAW_ROOT_DIR
    return ingest_tce_rs_from_directory(root, max_rows=max_rows, db_path=db_path)


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
        "raw_root": str(RAW_ROOT_DIR),
        "raw_years_available": list_available_raw_years(),
    }
