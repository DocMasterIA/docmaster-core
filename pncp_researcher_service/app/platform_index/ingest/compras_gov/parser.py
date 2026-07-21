"""
Parser Compras.gov — validação de estrutura + parse completo para ingest.
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Tuple

from .column_map import (
    column_map_spec,
    map_compra_row,
    map_item_row,
    validate_compra_headers,
    validate_item_headers,
)
from .config import PLATFORM_ID
from .files import find_compra_csv, find_compra_item_csv


@dataclass
class ComprasGovStructureReport:
    platform_id: str = PLATFORM_ID
    ok: bool = False
    data_dir: str = ""
    compra_csv: Optional[str] = None
    item_csv: Optional[str] = None
    compra_headers: Dict[str, Any] = field(default_factory=dict)
    item_headers: Dict[str, Any] = field(default_factory=dict)
    sample_compra_mapped: Optional[Dict[str, Any]] = None
    sample_item_mapped: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    column_map: Dict[str, Any] = field(default_factory=column_map_spec)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _sniff_dialect(sample: str) -> csv.Dialect:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;")
    except csv.Error:

        class _Comma(csv.Dialect):
            delimiter = ","
            quotechar = '"'
            doublequote = True
            skipinitialspace = False
            lineterminator = "\n"
            quoting = csv.QUOTE_MINIMAL

        return _Comma()


def _open_csv(path: Path) -> Tuple[TextIO, csv.DictReader]:
    fh = path.open("r", encoding="utf-8-sig", errors="replace", newline="")
    sample = fh.read(8192)
    fh.seek(0)
    dialect = _sniff_dialect(sample)
    reader = csv.DictReader(fh, dialect=dialect)
    return fh, reader


def _read_headers(path: Path) -> List[str]:
    fh, reader = _open_csv(path)
    try:
        return list(reader.fieldnames or [])
    finally:
        fh.close()


def _first_mapped_compra(path: Path) -> Optional[Dict[str, Any]]:
    fh, reader = _open_csv(path)
    try:
        for row in reader:
            mapped = map_compra_row(row)
            if mapped:
                return mapped
        return None
    finally:
        fh.close()


def _first_mapped_item(
    path: Path,
    *,
    compra: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    fh, reader = _open_csv(path)
    try:
        for row in reader:
            mapped = map_item_row(row, compra=compra)
            if mapped and (mapped.get("descricao") or "").strip():
                return mapped
        return None
    finally:
        fh.close()


def validate_bundle_structure(data_dir: str | Path) -> ComprasGovStructureReport:
    directory = Path(data_dir).expanduser().resolve()
    report = ComprasGovStructureReport(data_dir=str(directory))
    report.notes.append("Validate-structure: não grava no índice.")

    if not directory.is_dir():
        report.errors.append(f"Diretório inexistente: {directory}")
        return report

    compra_path = find_compra_csv(directory)
    item_path = find_compra_item_csv(directory)
    report.compra_csv = str(compra_path) if compra_path else None
    report.item_csv = str(item_path) if item_path else None

    if item_path is None:
        report.errors.append(
            "CSV de ITEM ausente (*VW_FT_PNCP_COMPRA_ITEM*). "
            "É o arquivo essencial para a alimentação."
        )
        return report

    try:
        item_headers = _read_headers(item_path)
        report.item_headers = validate_item_headers(item_headers)
        if not report.item_headers.get("ok"):
            report.errors.append(
                "Cabeçalhos ITEM incompletos: "
                + ", ".join(report.item_headers.get("missing_required") or [])
            )
    except OSError as exc:
        report.errors.append(f"Falha ao ler ITEM: {exc}")
        return report

    if compra_path is not None:
        try:
            compra_headers = _read_headers(compra_path)
            report.compra_headers = validate_compra_headers(compra_headers)
            if not report.compra_headers.get("ok"):
                report.errors.append(
                    "Cabeçalhos COMPRA incompletos: "
                    + ", ".join(report.compra_headers.get("missing_required") or [])
                )
            else:
                report.sample_compra_mapped = _first_mapped_compra(compra_path)
        except OSError as exc:
            report.errors.append(f"Falha ao ler COMPRA: {exc}")
    else:
        report.notes.append(
            "COMPRA ausente: join de órgão/UF/modalidade/link ficará limitado "
            "aos campos do próprio ITEM."
        )
        report.compra_headers = {"ok": True, "skipped": True}

    if report.item_headers.get("ok"):
        report.sample_item_mapped = _first_mapped_item(
            item_path,
            compra=report.sample_compra_mapped,
        )
        if report.sample_item_mapped is None:
            report.errors.append("Não foi possível mapear nenhuma linha de ITEM de amostra.")

    report.ok = not report.errors and bool(report.item_headers.get("ok"))
    return report


def parse_compras_gov_directory(
    data_dir: str | Path,
    *,
    max_rows: Optional[int] = None,
) -> Dict[str, Any]:
    """Lê COMPRA (+ ITEM) e devolve dicts mapeados para materialize."""
    directory = Path(data_dir).expanduser().resolve()
    if not directory.is_dir():
        raise FileNotFoundError(f"Diretório Compras.gov não encontrado: {directory}")

    compra_path = find_compra_csv(directory)
    item_path = find_compra_item_csv(directory)
    if item_path is None:
        raise FileNotFoundError(
            f"CSV ITEM ausente em {directory} (*VW_FT_PNCP_COMPRA_ITEM*)"
        )

    item_headers = validate_item_headers(_read_headers(item_path))
    if not item_headers.get("ok"):
        raise ValueError(
            "Cabeçalhos ITEM incompletos: "
            + ", ".join(item_headers.get("missing_required") or [])
        )

    compras: List[Dict[str, Any]] = []
    compra_by_cod: Dict[str, Dict[str, Any]] = {}
    if compra_path is not None:
        compra_headers = validate_compra_headers(_read_headers(compra_path))
        if not compra_headers.get("ok"):
            raise ValueError(
                "Cabeçalhos COMPRA incompletos: "
                + ", ".join(compra_headers.get("missing_required") or [])
            )
        fh, reader = _open_csv(compra_path)
        try:
            for row in reader:
                mapped = map_compra_row(row)
                if not mapped:
                    continue
                compras.append(mapped)
                compra_by_cod[str(mapped["cod_compra"])] = mapped
        finally:
            fh.close()

    itens: List[Dict[str, Any]] = []
    fh, reader = _open_csv(item_path)
    try:
        for row in reader:
            if max_rows is not None and len(itens) >= int(max_rows):
                break
            cod = str(row.get("cod_compra") or row.get("COD_COMPRA") or "").strip()
            # DictReader keys are original headers; normalize via map_item_row
            compra = None
            # try raw then normalized
            from .column_map import normalize_row_keys

            nr = normalize_row_keys(row)
            cod = str(nr.get("cod_compra") or "").strip() or cod
            compra = compra_by_cod.get(cod)
            mapped = map_item_row(row, compra=compra)
            if not mapped:
                continue
            if not (mapped.get("descricao") or "").strip():
                continue
            itens.append(mapped)
    finally:
        fh.close()

    return {
        "ok": True,
        "platform_id": PLATFORM_ID,
        "data_dir": str(directory),
        "files": {
            "compra": str(compra_path) if compra_path else None,
            "compra_item": str(item_path),
        },
        "compras": compras,
        "itens": itens,
        "stats": {
            "compras": len(compras),
            "itens": len(itens),
            "max_rows": max_rows,
        },
    }
