"""
Parser Notas Fiscais — cp1252 + ';' + validação + parse para ingest.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Tuple

from .column_map import (
    column_map_spec,
    map_item_row,
    map_nota_row,
    validate_item_headers,
    validate_nota_headers,
)
from .config import PLATFORM_ID
from .files import find_item_csv, find_nota_csv


def _detect_encoding(path: Path) -> str:
    """Portal usa cp1252; fixtures/dev podem ser UTF-8."""
    sample = path.read_bytes()[:16384]
    try:
        sample.decode("utf-8")
        return "utf-8-sig"
    except UnicodeDecodeError:
        return "cp1252"


def _open_csv(path: Path) -> Tuple[TextIO, csv.DictReader]:
    enc = _detect_encoding(path)
    fh = path.open("r", encoding=enc, errors="replace", newline="")
    reader = csv.DictReader(fh, delimiter=";")
    return fh, reader


def _read_headers(path: Path) -> List[str]:
    fh, reader = _open_csv(path)
    try:
        return list(reader.fieldnames or [])
    finally:
        fh.close()


def validate_bundle_structure(data_dir: str | Path) -> Dict[str, Any]:
    directory = Path(data_dir).expanduser().resolve()
    out: Dict[str, Any] = {
        "ok": False,
        "platform_id": PLATFORM_ID,
        "data_dir": str(directory),
        "nota_csv": None,
        "item_csv": None,
        "errors": [],
        "notes": ["Validate-structure: não grava no índice."],
        "column_map": column_map_spec(),
    }
    if not directory.is_dir():
        out["errors"].append(f"Diretório inexistente: {directory}")
        return out

    item_path = find_item_csv(directory)
    nota_path = find_nota_csv(directory)
    out["item_csv"] = str(item_path) if item_path else None
    out["nota_csv"] = str(nota_path) if nota_path else None

    if item_path is None:
        out["errors"].append("CSV de ITEM ausente (*NotaFiscalItem*).")
        return out

    item_headers = validate_item_headers(_read_headers(item_path))
    out["item_headers"] = item_headers
    if not item_headers.get("ok"):
        out["errors"].append(
            "Cabeçalhos ITEM incompletos: "
            + ", ".join(item_headers.get("missing_required") or [])
        )

    if nota_path is not None:
        nota_headers = validate_nota_headers(_read_headers(nota_path))
        out["nota_headers"] = nota_headers
        if not nota_headers.get("ok"):
            out["errors"].append(
                "Cabeçalhos NOTA incompletos: "
                + ", ".join(nota_headers.get("missing_required") or [])
            )
    else:
        out["notes"].append(
            "NotaFiscal ausente: filtro de evento e órgão dependerão só do Item."
        )

    out["ok"] = not out["errors"]
    return out


def parse_notas_fiscais_directory(
    data_dir: str | Path,
    *,
    max_rows: Optional[int] = None,
) -> Dict[str, Any]:
    """Lê Nota (+ Item) e devolve dicts mapeados para materialize."""
    directory = Path(data_dir).expanduser().resolve()
    if not directory.is_dir():
        raise FileNotFoundError(f"Diretório Notas Fiscais não encontrado: {directory}")

    item_path = find_item_csv(directory)
    nota_path = find_nota_csv(directory)
    if item_path is None:
        raise FileNotFoundError(
            f"CSV ITEM ausente em {directory} (*NotaFiscalItem*)"
        )

    item_headers = validate_item_headers(_read_headers(item_path))
    if not item_headers.get("ok"):
        raise ValueError(
            "Cabeçalhos ITEM incompletos: "
            + ", ".join(item_headers.get("missing_required") or [])
        )

    notas: List[Dict[str, Any]] = []
    nota_by_chave: Dict[str, Dict[str, Any]] = {}
    notas_rejeitadas = 0
    if nota_path is not None:
        nota_headers = validate_nota_headers(_read_headers(nota_path))
        if not nota_headers.get("ok"):
            raise ValueError(
                "Cabeçalhos NOTA incompletos: "
                + ", ".join(nota_headers.get("missing_required") or [])
            )
        fh, reader = _open_csv(nota_path)
        try:
            for row in reader:
                mapped = map_nota_row(row)
                if not mapped:
                    continue
                if not mapped.get("evento_ok"):
                    notas_rejeitadas += 1
                    continue
                notas.append(mapped)
                nota_by_chave[str(mapped["chave"])] = mapped
        finally:
            fh.close()

    itens: List[Dict[str, Any]] = []
    skipped_no_nota = 0
    skipped_map = 0
    fh, reader = _open_csv(item_path)
    try:
        for row in reader:
            if max_rows is not None and len(itens) >= int(max_rows):
                break
            from .column_map import normalize_row_keys

            nr = normalize_row_keys(row)
            chave = str(nr.get("chave_de_acesso") or "").strip()
            nota = nota_by_chave.get(chave) if chave else None
            # Se há arquivo Nota, exige join autorizado (evita itens de NF cancelada).
            if nota_path is not None and nota is None:
                skipped_no_nota += 1
                continue
            mapped = map_item_row(row, nota=nota)
            if not mapped:
                skipped_map += 1
                continue
            itens.append(mapped)
    finally:
        fh.close()

    return {
        "ok": True,
        "platform_id": PLATFORM_ID,
        "data_dir": str(directory),
        "files": {
            "nota": str(nota_path) if nota_path else None,
            "item": str(item_path),
        },
        "notas": notas,
        "itens": itens,
        "stats": {
            "notas": len(notas),
            "notas_rejeitadas_evento": notas_rejeitadas,
            "itens": len(itens),
            "itens_skipped_sem_nota": skipped_no_nota,
            "itens_skipped_map": skipped_map,
            "max_rows": max_rows,
        },
    }
