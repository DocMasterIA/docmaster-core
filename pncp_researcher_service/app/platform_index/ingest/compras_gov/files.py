"""Discover de arquivos CSV Compras.gov (sem parse de linhas)."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from .config import (
    COMPRAS_GOV_FILE_COMPRA_MARKERS,
    COMPRAS_GOV_FILE_ITEM_MARKERS,
    COMPRAS_GOV_VIEW_COMPRA,
    COMPRAS_GOV_VIEW_COMPRA_ITEM,
)


def _name_matches(name: str, markers: Tuple[str, ...]) -> bool:
    low = name.lower()
    return any(m.lower() in low for m in markers)


def _is_item_csv(name: str) -> bool:
    """COMPRA_ITEM antes de COMPRA (substring overlap)."""
    return _name_matches(name, COMPRAS_GOV_FILE_ITEM_MARKERS)


def _is_compra_csv(name: str) -> bool:
    if _is_item_csv(name):
        return False
    return _name_matches(name, COMPRAS_GOV_FILE_COMPRA_MARKERS)


def find_compra_csv(directory: Path) -> Optional[Path]:
    if not directory.is_dir():
        return None
    for p in sorted(directory.iterdir()):
        if p.is_file() and p.suffix.lower() == ".csv" and _is_compra_csv(p.name):
            return p
    return None


def find_compra_item_csv(directory: Path) -> Optional[Path]:
    if not directory.is_dir():
        return None
    for p in sorted(directory.iterdir()):
        if p.is_file() and p.suffix.lower() == ".csv" and _is_item_csv(p.name):
            return p
    return None


def is_compras_gov_bundle_dir(path: Path) -> bool:
    """Pasta com pelo menos o CSV de itens (COMPRA é join opcional)."""
    if not path.is_dir():
        return False
    return find_compra_item_csv(path) is not None


def discover_ingest_dirs(root: Path) -> List[Path]:
    """
    Aceita:
    - pasta com CSVs VW_FT_PNCP_COMPRA(_ITEM) direto;
    - pasta mãe com subpastas (anual/, mensal/YYYY/MM/, …) que tenham o bundle.

    Preferência: subpastas YYYY/MM (ou filhas com bundle) antes da raiz.
    Assim *-latest.csv na raiz não engole os meses.
    """
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Diretório Compras.gov não encontrado: {root}")
    child_dirs = [
        p
        for p in sorted(root.iterdir())
        if p.is_dir() and is_compras_gov_bundle_dir(p)
    ]
    nested: List[Path] = []
    for p in sorted(root.iterdir()):
        if not p.is_dir() or is_compras_gov_bundle_dir(p):
            continue
        for sub in sorted(p.iterdir()):
            if sub.is_dir() and is_compras_gov_bundle_dir(sub):
                nested.append(sub)
    found = child_dirs + nested
    if found:
        return found
    if is_compras_gov_bundle_dir(root):
        return [root]
    raise FileNotFoundError(
        f"Nenhum CSV Compras.gov em {root} "
        f"(esperado *{COMPRAS_GOV_VIEW_COMPRA_ITEM}*.csv; "
        f"opcional *{COMPRAS_GOV_VIEW_COMPRA}*.csv)"
    )
