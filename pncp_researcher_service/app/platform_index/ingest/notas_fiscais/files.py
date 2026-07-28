"""Discover de CSVs Notas Fiscais (Portal da Transparência) — sem parse de linhas."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from .config import (
    NF_FILE_EVENTO_MARKERS,
    NF_FILE_ITEM_MARKERS,
    NF_FILE_NOTA_MARKERS,
)


def _name_matches(name: str, markers: Tuple[str, ...]) -> bool:
    low = name.lower()
    return any(m.lower() in low for m in markers)


def _is_item_csv(name: str) -> bool:
    return _name_matches(name, NF_FILE_ITEM_MARKERS)


def _is_evento_csv(name: str) -> bool:
    return _name_matches(name, NF_FILE_EVENTO_MARKERS)


def _is_nota_csv(name: str) -> bool:
    """NotaFiscal antes de Item/Evento (substring overlap)."""
    if _is_item_csv(name) or _is_evento_csv(name):
        return False
    return _name_matches(name, NF_FILE_NOTA_MARKERS)


def find_nota_csv(directory: Path) -> Optional[Path]:
    if not directory.is_dir():
        return None
    for p in sorted(directory.iterdir()):
        if p.is_file() and p.suffix.lower() == ".csv" and _is_nota_csv(p.name):
            return p
    return None


def find_item_csv(directory: Path) -> Optional[Path]:
    if not directory.is_dir():
        return None
    for p in sorted(directory.iterdir()):
        if p.is_file() and p.suffix.lower() == ".csv" and _is_item_csv(p.name):
            return p
    return None


def find_evento_csv(directory: Path) -> Optional[Path]:
    if not directory.is_dir():
        return None
    for p in sorted(directory.iterdir()):
        if p.is_file() and p.suffix.lower() == ".csv" and _is_evento_csv(p.name):
            return p
    return None


def is_notas_fiscais_bundle_dir(path: Path) -> bool:
    """Pasta com pelo menos o CSV de itens (Nota/Evento são join opcional)."""
    if not path.is_dir():
        return False
    return find_item_csv(path) is not None


def discover_ingest_dirs(root: Path) -> List[Path]:
    """
    Aceita:
    - pasta com *NotaFiscalItem*.csv direto;
    - pasta mãe com subpastas YYYY/MM/ (ou mensal/) que tenham o bundle.

    Preferência: subpastas com bundle antes da raiz (evita *-latest* engolir meses).
    """
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Diretório Notas Fiscais não encontrado: {root}")
    child_dirs = [
        p for p in sorted(root.iterdir()) if p.is_dir() and is_notas_fiscais_bundle_dir(p)
    ]
    nested: List[Path] = []
    for p in sorted(root.iterdir()):
        if not p.is_dir() or is_notas_fiscais_bundle_dir(p):
            continue
        for sub in sorted(p.iterdir()):
            if sub.is_dir() and is_notas_fiscais_bundle_dir(sub):
                nested.append(sub)
    found = child_dirs + nested
    if found:
        return found
    if is_notas_fiscais_bundle_dir(root):
        return [root]
    raise FileNotFoundError(
        f"Nenhum CSV Notas Fiscais em {root} "
        f"(esperado *NotaFiscalItem*.csv; opcional *NotaFiscal*.csv / *NotaFiscalEvento*.csv)"
    )
