from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ....config import COMPRAS_GOV_LOCAL_DB_PATH
from ...schema import platform_index_stats
from .column_map import column_map_spec
from .config import (
    COMPRAS_GOV_INGEST_DATA_DIR,
    COMPRAS_GOV_VIEW_COMPRA,
    COMPRAS_GOV_VIEW_COMPRA_ITEM,
    FIXTURES_DIR,
    PLATFORM_ID,
    RAW_ROOT_DIR,
)
from .files import (
    discover_ingest_dirs,
    find_compra_csv,
    find_compra_item_csv,
    is_compras_gov_bundle_dir,
)
from .materialize import ensure_compras_gov_index, materialize_compras_gov_parsed
from .parser import parse_compras_gov_directory, validate_bundle_structure


def list_available_raw_bundles(raw_root: Optional[Path] = None) -> List[str]:
    root = (raw_root or RAW_ROOT_DIR).expanduser().resolve()
    if not root.is_dir():
        return []
    try:
        return [str(p.relative_to(root)) for p in discover_ingest_dirs(root)]
    except FileNotFoundError:
        return []


def resolve_default_data_dir() -> Path:
    env = (COMPRAS_GOV_INGEST_DATA_DIR or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return RAW_ROOT_DIR.expanduser().resolve()


def compras_gov_ingest_status(*, db_path: Optional[str] = None) -> Dict[str, Any]:
    path = (db_path or COMPRAS_GOV_LOCAL_DB_PATH).strip()
    stats = platform_index_stats(path)
    state: Dict[str, Any] = {}
    if stats.get("db_exists"):
        from ...connection import platform_conn

        with platform_conn(path) as c:
            row = c.execute(
                "SELECT scope_key, watermark, last_error, rows_total, updated_at "
                "FROM platform_ingest_state WHERE scope_key='compras_gov_full' LIMIT 1"
            ).fetchone()
            if row:
                state = dict(row)

    data_root = resolve_default_data_dir()
    bundles: List[Dict[str, Any]] = []
    try:
        for d in discover_ingest_dirs(data_root) if data_root.is_dir() else []:
            compra = find_compra_csv(d)
            item = find_compra_item_csv(d)
            bundles.append(
                {
                    "dir": str(d),
                    "compra_csv": str(compra) if compra else None,
                    "compra_item_csv": str(item) if item else None,
                }
            )
    except FileNotFoundError:
        bundles = []

    return {
        "ok": True,
        "platform_id": PLATFORM_ID,
        "db_path": path,
        "index_stats": stats,
        "ingest_state": state,
        "search_ready": bool(stats.get("search_ready")),
        "structure_ready": True,
        "ingest_implemented": True,
        "item_materialize_enabled": True,
        "column_map": column_map_spec(),
        "views": {
            "compra": COMPRAS_GOV_VIEW_COMPRA,
            "compra_item": COMPRAS_GOV_VIEW_COMPRA_ITEM,
        },
        "raw_root": str(RAW_ROOT_DIR),
        "data_dir": str(data_root),
        "raw_bundles_available": list_available_raw_bundles(),
        "discovered_bundles": bundles,
        "fixtures_dir": str(FIXTURES_DIR),
        "note": (
            "Ingest/materialize ativos (fixtures + diretório). "
            "Carga de 1 ano: apontar data_dir/raw com os CSVs anuais."
        ),
    }


def validate_compras_gov_structure(
    data_dir: Optional[str | Path] = None,
) -> Dict[str, Any]:
    directory = Path(data_dir).expanduser().resolve() if data_dir else resolve_default_data_dir()
    return validate_bundle_structure(directory).to_dict()


def ensure_compras_gov_db(*, db_path: Optional[str] = None) -> Dict[str, Any]:
    return ensure_compras_gov_index(db_path=db_path)


def ingest_compras_gov_from_directory(
    data_dir: str | Path,
    *,
    max_rows: Optional[int] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parse CSVs COMPRA+ITEM e materializa no índice compras_gov.

    `data_dir` pode ser pasta com CSVs ou raiz com subpastas bundle.
    """
    directory = Path(data_dir).expanduser().resolve()
    year_dirs = discover_ingest_dirs(directory)

    per_bundle: List[Dict[str, Any]] = []
    last_mat: Dict[str, Any] = {}
    total_compras = 0
    total_itens = 0
    for bundle_dir in year_dirs:
        parsed = parse_compras_gov_directory(bundle_dir, max_rows=max_rows)
        mat = materialize_compras_gov_parsed(parsed, db_path=db_path)
        last_mat = mat
        total_compras += int((parsed.get("stats") or {}).get("compras") or 0)
        total_itens += int((parsed.get("stats") or {}).get("itens") or 0)
        per_bundle.append(
            {
                "dir": str(bundle_dir),
                "parsed": parsed.get("stats"),
                "materialize": mat.get("materialize"),
            }
        )

    db = (last_mat.get("db_path") or db_path or COMPRAS_GOV_LOCAL_DB_PATH)
    index_stats = platform_index_stats(db)
    return {
        "ok": True,
        "platform_id": PLATFORM_ID,
        "data_dir": str(directory),
        "bundles": per_bundle,
        "parsed": {"compras": total_compras, "itens": total_itens},
        "materialize": last_mat.get("materialize"),
        "index_stats": index_stats,
        "search_ready": bool(index_stats.get("search_ready")),
        "db_path": db,
    }


def ingest_compras_gov_sample(*, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Carrega fixtures locais para dev/teste E2E."""
    if not FIXTURES_DIR.is_dir():
        raise FileNotFoundError(f"Fixtures Compras.gov ausentes: {FIXTURES_DIR}")
    return ingest_compras_gov_from_directory(FIXTURES_DIR, db_path=db_path)


__all__ = [
    "discover_ingest_dirs",
    "find_compra_csv",
    "find_compra_item_csv",
    "is_compras_gov_bundle_dir",
    "list_available_raw_bundles",
    "compras_gov_ingest_status",
    "validate_compras_gov_structure",
    "ensure_compras_gov_db",
    "ingest_compras_gov_from_directory",
    "ingest_compras_gov_sample",
]
