"""
Ingest Notas Fiscais — Portal da Transparência → platform_index.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ....config import NOTAS_FISCAIS_LOCAL_DB_PATH
from ...schema import platform_index_stats
from .column_map import column_map_spec
from .config import (
    FIXTURES_DIR,
    NOTAS_FISCAIS_INGEST_DATA_DIR,
    PLATFORM_ID,
    RAW_ROOT_DIR,
)
from .files import (
    discover_ingest_dirs,
    find_evento_csv,
    find_item_csv,
    find_nota_csv,
)
from .materialize import ensure_notas_fiscais_index, materialize_notas_fiscais_parsed
from .parser import parse_notas_fiscais_directory, validate_bundle_structure


def list_available_raw_bundles(raw_root: Optional[Path] = None) -> List[str]:
    root = (raw_root or RAW_ROOT_DIR).expanduser().resolve()
    if not root.is_dir():
        return []
    try:
        return [str(p.relative_to(root)) for p in discover_ingest_dirs(root)]
    except FileNotFoundError:
        return []


def resolve_default_data_dir() -> Path:
    env = (NOTAS_FISCAIS_INGEST_DATA_DIR or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return RAW_ROOT_DIR.expanduser().resolve()


def ensure_notas_fiscais_db(*, db_path: Optional[str] = None) -> Dict[str, Any]:
    out = ensure_notas_fiscais_index(db_path=db_path)
    stats = out.get("index_stats") or {}
    out["search_ready"] = bool(stats.get("search_ready"))
    out["note"] = "Schema platform_index criado/atualizado."
    return out


def validate_notas_fiscais_structure(data_dir: Optional[str] = None) -> Dict[str, Any]:
    directory = Path(data_dir).expanduser().resolve() if data_dir else resolve_default_data_dir()
    return validate_bundle_structure(directory)


def notas_fiscais_ingest_status(*, db_path: Optional[str] = None) -> Dict[str, Any]:
    path = (db_path or NOTAS_FISCAIS_LOCAL_DB_PATH).strip()
    stats = platform_index_stats(path)
    state: Dict[str, Any] = {}
    if stats.get("db_exists"):
        from ...connection import platform_conn

        with platform_conn(path) as c:
            row = c.execute(
                "SELECT scope_key, watermark, last_error, rows_total, updated_at "
                "FROM platform_ingest_state WHERE scope_key='notas_fiscais_full' LIMIT 1"
            ).fetchone()
            if row:
                state = dict(row)

    data_root = resolve_default_data_dir()
    bundles: List[Dict[str, Any]] = []
    try:
        for d in discover_ingest_dirs(data_root) if data_root.is_dir() else []:
            nota = find_nota_csv(d)
            item = find_item_csv(d)
            evento = find_evento_csv(d)
            bundles.append(
                {
                    "dir": str(d),
                    "nota_csv": str(nota) if nota else None,
                    "item_csv": str(item) if item else None,
                    "evento_csv": str(evento) if evento else None,
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
        "inciso_default": "inciso_v",
        "esfera_default": "federal",
        "column_map": column_map_spec(),
        "views": {
            "nota": "NotaFiscal",
            "item": "NotaFiscalItem",
            "evento": "NotaFiscalEvento",
        },
        "raw_root": str(RAW_ROOT_DIR),
        "data_dir": str(data_root),
        "raw_bundles_available": list_available_raw_bundles(),
        "discovered_bundles": bundles,
        "fixtures_dir": str(FIXTURES_DIR),
        "note": (
            "Ingest ativo: NotaFiscalItem + join NotaFiscal (evento Autorização de Uso). "
            "VALOR UNITÁRIO → valor_unitario e valor_unitario_homologado."
        ),
    }


def ingest_notas_fiscais_from_directory(
    data_dir: str | Path,
    *,
    max_rows: Optional[int] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parse CSVs Nota+Item e materializa no índice notas_fiscais.

    `data_dir` pode ser pasta bundle (…/202601_NFe) ou raiz raw/ com subpastas.
    """
    directory = Path(data_dir).expanduser().resolve()
    bundle_dirs = discover_ingest_dirs(directory)

    per_bundle: List[Dict[str, Any]] = []
    last_mat: Dict[str, Any] = {}
    total_notas = 0
    total_itens = 0
    for bundle_dir in bundle_dirs:
        parsed = parse_notas_fiscais_directory(bundle_dir, max_rows=max_rows)
        mat = materialize_notas_fiscais_parsed(parsed, db_path=db_path)
        last_mat = mat
        total_notas += int((parsed.get("stats") or {}).get("notas") or 0)
        total_itens += int((parsed.get("stats") or {}).get("itens") or 0)
        per_bundle.append(
            {
                "dir": str(bundle_dir),
                "parsed": parsed.get("stats"),
                "materialize": mat.get("materialize"),
            }
        )

    db = last_mat.get("db_path") or db_path or NOTAS_FISCAIS_LOCAL_DB_PATH
    index_stats = platform_index_stats(db)
    return {
        "ok": True,
        "platform_id": PLATFORM_ID,
        "data_dir": str(directory),
        "bundles": per_bundle,
        "parsed": {"notas": total_notas, "itens": total_itens},
        "materialize": last_mat.get("materialize"),
        "index_stats": index_stats,
        "search_ready": bool(index_stats.get("search_ready")),
        "db_path": db,
    }


def ingest_notas_fiscais_sample(*, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Carrega fixtures mínimas (dev/teste)."""
    if not FIXTURES_DIR.is_dir():
        raise FileNotFoundError(f"Fixtures ausentes: {FIXTURES_DIR}")
    return ingest_notas_fiscais_from_directory(FIXTURES_DIR, db_path=db_path)
