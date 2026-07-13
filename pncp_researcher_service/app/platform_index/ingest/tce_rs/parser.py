from __future__ import annotations

import csv
import glob
import re
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

from .column_map import (
    map_item_row,
    map_licitacao_row,
    map_proposta_row,
    normalize_csv_row,
)
from .config import TCE_RS_FILE_ITEM, TCE_RS_FILE_LICITACAO, TCE_RS_FILE_PROPOSTA


def find_csv_file(data_dir: Path, stem: str) -> Optional[Path]:
    """Localiza CSV por stem (ex.: LICITACAO → *LICITACAO*.csv)."""
    if not data_dir.is_dir():
        return None
    patterns = [
        str(data_dir / f"{stem}.csv"),
        str(data_dir / f"{stem.lower()}.csv"),
        str(data_dir / f"*{stem}*.csv"),
        str(data_dir / f"*{stem.lower()}*.csv"),
    ]
    seen: set[str] = set()
    for pattern in patterns:
        for match in sorted(glob.glob(pattern)):
            p = Path(match)
            if p.is_file() and str(p) not in seen:
                seen.add(str(p))
                return p
    return None


def _read_csv_rows(path: Path, *, max_rows: Optional[int] = None) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,|\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(fh, dialect=dialect)
        count = 0
        for row in reader:
            if not row:
                continue
            yield normalize_csv_row(row)
            count += 1
            if max_rows is not None and count >= max_rows:
                break


def _parse_file(
    path: Optional[Path],
    mapper: Callable[[Dict[str, Any]], Optional[Dict[str, Any]]],
    *,
    max_rows: Optional[int] = None,
) -> List[Dict[str, Any]]:
    if path is None or not path.is_file():
        return []
    out: List[Dict[str, Any]] = []
    for raw in _read_csv_rows(path, max_rows=max_rows):
        mapped = mapper(raw)
        if mapped:
            out.append(mapped)
    return out


def parse_licitacao_csv(path: Optional[Path], *, max_rows: Optional[int] = None) -> List[Dict[str, Any]]:
    return _parse_file(path, map_licitacao_row, max_rows=max_rows)


def parse_item_csv(path: Optional[Path], *, max_rows: Optional[int] = None) -> List[Dict[str, Any]]:
    return _parse_file(path, map_item_row, max_rows=max_rows)


def parse_proposta_csv(path: Optional[Path], *, max_rows: Optional[int] = None) -> List[Dict[str, Any]]:
    return _parse_file(path, map_proposta_row, max_rows=max_rows)


def parse_tce_rs_directory(
    data_dir: Path,
    *,
    max_rows: Optional[int] = None,
) -> Dict[str, Any]:
    lic_path = find_csv_file(data_dir, TCE_RS_FILE_LICITACAO)
    item_path = find_csv_file(data_dir, TCE_RS_FILE_ITEM)
    prop_path = find_csv_file(data_dir, TCE_RS_FILE_PROPOSTA)
    licitacoes = parse_licitacao_csv(lic_path, max_rows=max_rows)
    itens = parse_item_csv(item_path, max_rows=max_rows)
    propostas = parse_proposta_csv(prop_path, max_rows=max_rows)
    return {
        "data_dir": str(data_dir),
        "files": {
            "licitacao": str(lic_path) if lic_path else None,
            "item": str(item_path) if item_path else None,
            "proposta": str(prop_path) if prop_path else None,
        },
        "licitacoes": licitacoes,
        "itens": itens,
        "propostas": propostas,
    }


def _classificacao_rank(classificacao: Optional[str]) -> int:
    if not classificacao:
        return 999
    s = str(classificacao).strip().lower()
    if s in {"1", "01", "vencedor", "vencedora", "homologado", "vencedor(a)"}:
        return 1
    m = re.search(r"\d+", s)
    if m:
        try:
            return int(m.group(0))
        except ValueError:
            pass
    return 999


def pick_best_propostas(propostas: List[Dict[str, Any]]) -> Dict[tuple[str, str], Dict[str, Any]]:
    """Escolhe melhor proposta por (licitacao_id, numero_item) — vencedor ou menor classificação."""
    best: Dict[tuple[str, str], Dict[str, Any]] = {}
    for prop in propostas:
        key = (prop["licitacao_id"], prop["numero_item"])
        prev = best.get(key)
        if prev is None:
            best[key] = prop
            continue
        rank_new = _classificacao_rank(prop.get("classificacao"))
        rank_old = _classificacao_rank(prev.get("classificacao"))
        if rank_new < rank_old:
            best[key] = prop
            continue
        if rank_new == rank_old:
            v_new = float(prop.get("valor_unitario_homologado") or prop.get("valor_unitario") or 0)
            v_old = float(prev.get("valor_unitario_homologado") or prev.get("valor_unitario") or 0)
            if v_new > v_old:
                best[key] = prop
    return best
