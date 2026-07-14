from __future__ import annotations

import csv
import glob
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

from .column_map import (
    map_item_row,
    map_licitacao_row,
    map_pessoa_row,
    map_proposta_row,
    uniquify_fieldnames,
)
from .config import (
    TCE_RS_FILE_ITEM,
    TCE_RS_FILE_ITEM_ALIASES,
    TCE_RS_FILE_ITEM_PROP,
    TCE_RS_FILE_LICITACAO,
    TCE_RS_FILE_PESSOAS,
    TCE_RS_FILE_PROPOSTA,
)


def find_csv_file(data_dir: Path, stem: str) -> Optional[Path]:
    """Localiza CSV por stem (ex.: licitacao → licitacao.csv / *LICITACAO*.csv)."""
    if not data_dir.is_dir():
        return None
    patterns = [
        str(data_dir / f"{stem}.csv"),
        str(data_dir / f"{stem.lower()}.csv"),
        str(data_dir / f"{stem.upper()}.csv"),
        str(data_dir / f"*{stem}*.csv"),
        str(data_dir / f"*{stem.lower()}*.csv"),
        str(data_dir / f"*{stem.upper()}*.csv"),
    ]
    seen: set[str] = set()
    stem_l = stem.lower()
    for pattern in patterns:
        for match in sorted(glob.glob(pattern)):
            p = Path(match)
            if not p.is_file() or str(p) in seen:
                continue
            name = p.stem.lower()
            if stem_l == "item" and "prop" in name:
                continue
            seen.add(str(p))
            return p
    return None


def find_item_csv(data_dir: Path) -> Optional[Path]:
    """Preferência: item.csv → itemw.csv → *item* (exceto item_prop)."""
    for stem in TCE_RS_FILE_ITEM_ALIASES:
        exact = data_dir / f"{stem}.csv"
        if exact.is_file():
            return exact
    for p in sorted(data_dir.glob("*.csv")):
        name = p.stem.lower()
        if name in {"item", "itemw"} or (name.startswith("item") and "prop" not in name):
            return p
    return find_csv_file(data_dir, TCE_RS_FILE_ITEM)


def find_proposta_csv(data_dir: Path) -> Optional[Path]:
    """Preferência: item_prop.csv (preço por item) → proposta.csv."""
    for stem in (TCE_RS_FILE_ITEM_PROP, TCE_RS_FILE_PROPOSTA, "PROPOSTA", "ITEM_PROP"):
        exact = data_dir / f"{stem}.csv"
        if exact.is_file():
            return exact
        found = find_csv_file(data_dir, stem)
        if found:
            return found
    return None


def _read_csv_rows(path: Path, *, max_rows: Optional[int] = None) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        sample = fh.read(8192)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,|\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(fh, dialect=dialect)
        try:
            header = next(reader)
        except StopIteration:
            return
        fieldnames = uniquify_fieldnames(header)
        count = 0
        for values in reader:
            if not values or all(not str(v or "").strip() for v in values):
                continue
            raw = {
                fieldnames[i]: (values[i].strip() if i < len(values) and isinstance(values[i], str) else (values[i] if i < len(values) else ""))
                for i in range(len(fieldnames))
            }
            yield raw
            count += 1
            if max_rows is not None and count >= max_rows:
                break


def parse_licitacao_csv(path: Optional[Path], *, max_rows: Optional[int] = None) -> List[Dict[str, Any]]:
    if path is None or not path.is_file():
        return []
    out: List[Dict[str, Any]] = []
    for raw in _read_csv_rows(path, max_rows=max_rows):
        mapped = map_licitacao_row(raw)
        if mapped:
            out.append(mapped)
    return out


def parse_item_csv(path: Optional[Path], *, max_rows: Optional[int] = None) -> List[Dict[str, Any]]:
    if path is None or not path.is_file():
        return []
    out: List[Dict[str, Any]] = []
    for raw in _read_csv_rows(path, max_rows=max_rows):
        mapped = map_item_row(raw)
        if mapped:
            out.append(mapped)
    return out


def parse_proposta_csv(path: Optional[Path], *, max_rows: Optional[int] = None) -> List[Dict[str, Any]]:
    if path is None or not path.is_file():
        return []
    out: List[Dict[str, Any]] = []
    for raw in _read_csv_rows(path, max_rows=max_rows):
        mapped = map_proposta_row(raw)
        if mapped:
            out.append(mapped)
    return out


def parse_pessoas_csv(path: Optional[Path], *, max_rows: Optional[int] = None) -> List[Dict[str, Any]]:
    if path is None or not path.is_file():
        return []
    out: List[Dict[str, Any]] = []
    for raw in _read_csv_rows(path, max_rows=max_rows):
        mapped = map_pessoa_row(raw)
        if mapped:
            out.append(mapped)
    return out


def _resultado_proposta_rank(prop: Dict[str, Any]) -> int:
    """Menor = melhor. C (classificada/vencedora) tem prioridade."""
    raw = prop.get("tp_resultado_proposta") or prop.get("classificacao") or ""
    s = str(raw).strip().upper()
    if s in {"C", "V", "VENCEDOR", "VENCEDORA", "HOMOLOGADO", "1", "01"}:
        return 0
    if s in {"H"}:
        return 5
    if s in {"D", "N", "R", "F"}:
        return 80
    m = re.search(r"\d+", s)
    if m:
        try:
            return 10 + int(m.group(0))
        except ValueError:
            pass
    if not s:
        return 50
    return 40


def _proposta_unit_price(prop: Dict[str, Any]) -> float:
    try:
        return float(prop.get("valor_unitario_homologado") or prop.get("valor_unitario") or 0)
    except (TypeError, ValueError):
        return 0.0


def _keep_better_proposta(prev: Optional[Dict[str, Any]], prop: Dict[str, Any]) -> Dict[str, Any]:
    if prev is None:
        return prop
    rank_new = _resultado_proposta_rank(prop)
    rank_old = _resultado_proposta_rank(prev)
    if rank_new < rank_old:
        return prop
    if rank_new > rank_old:
        return prev
    v_new = _proposta_unit_price(prop)
    v_old = _proposta_unit_price(prev)
    if v_old <= 0 < v_new:
        return prop
    return prev


def pick_best_propostas(propostas: List[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """Escolhe melhor proposta por (licitacao_id, numero_item)."""
    best: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for prop in propostas:
        key = (prop["licitacao_id"], prop["numero_item"])
        best[key] = _keep_better_proposta(best.get(key), prop)
    return best


def resolve_item_price(
    item: Dict[str, Any],
    prop: Optional[Dict[str, Any]],
) -> Tuple[Optional[float], Optional[float], str]:
    """
    Retorna (valor_unitario, valor_homologado, origem).
    Prioridade: item.homologado → prop.unitário (vencedora) → item.estimado.
    """
    prop = prop or {}
    item_hom = item.get("valor_unitario_homologado")
    if item_hom is not None and float(item_hom) > 0:
        return float(item_hom), float(item_hom), "item_homologado"
    prop_hom = prop.get("valor_unitario_homologado")
    if prop_hom is not None and float(prop_hom) > 0:
        return float(prop_hom), float(prop_hom), "proposta_homologada"
    prop_val = prop.get("valor_unitario")
    if prop_val is not None and float(prop_val) > 0:
        return float(prop_val), None, "proposta"
    est = item.get("valor_unitario_estimado")
    if est is not None and float(est) > 0:
        return float(est), None, "item_estimado"
    return None, None, "sem_preco"


def _add_doc_key(out: Set[str], value: Any) -> None:
    if value:
        out.add(str(value))


def collect_supplier_doc_keys(
    *,
    licitacoes: List[Dict[str, Any]],
    itens: List[Dict[str, Any]],
    propostas: List[Dict[str, Any]],
) -> Set[str]:
    """Documentos candidatos do waterfall de fornecedor."""
    needed: Set[str] = set()
    for prop in propostas:
        _add_doc_key(needed, prop.get("doc_key"))
    for item in itens:
        _add_doc_key(needed, item.get("doc_key"))
        _add_doc_key(needed, item.get("doc_key_2"))
    for lic in licitacoes:
        _add_doc_key(needed, lic.get("doc_key_vencedor"))
        _add_doc_key(needed, lic.get("doc_key_fornecedor"))
    return needed


def parse_tce_rs_directory(
    data_dir: Path,
    *,
    max_rows: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Lê CSVs LicitaCon e monta estruturas joináveis.

    - licitacao: carrega completo (necessário ao join)
    - item: limitado por max_rows quando informado
    - item_prop: só chaves presentes nos itens carregados
    - pessoas: só documentos candidatos do waterfall de fornecedor
    """
    lic_path = find_csv_file(data_dir, TCE_RS_FILE_LICITACAO) or find_csv_file(data_dir, "LICITACAO")
    item_path = find_item_csv(data_dir)
    prop_path = find_proposta_csv(data_dir)
    pessoas_path = find_csv_file(data_dir, TCE_RS_FILE_PESSOAS) or find_csv_file(data_dir, "PESSOAS")

    licitacoes = parse_licitacao_csv(lic_path)
    lic_ids = {row["licitacao_id"] for row in licitacoes}

    itens: List[Dict[str, Any]] = []
    if item_path and item_path.is_file():
        for raw in _read_csv_rows(item_path):
            mapped = map_item_row(raw)
            if not mapped:
                continue
            if lic_ids and mapped["licitacao_id"] not in lic_ids:
                continue
            itens.append(mapped)
            if max_rows is not None and len(itens) >= max_rows:
                break

    item_keys: Set[Tuple[str, str]] = {(i["licitacao_id"], i["numero_item"]) for i in itens}

    propostas_best: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if prop_path and prop_path.is_file() and item_keys:
        for raw in _read_csv_rows(prop_path):
            mapped = map_proposta_row(raw)
            if not mapped:
                continue
            key = (mapped["licitacao_id"], mapped["numero_item"])
            if key not in item_keys:
                continue
            propostas_best[key] = _keep_better_proposta(propostas_best.get(key), mapped)
            # Atalho em amostragem: todos os itens já têm proposta vencedora (C).
            if (
                max_rows is not None
                and len(propostas_best) >= len(item_keys)
                and all(_resultado_proposta_rank(p) == 0 for p in propostas_best.values())
            ):
                break

    propostas = list(propostas_best.values())
    needed_docs = collect_supplier_doc_keys(
        licitacoes=licitacoes,
        itens=itens,
        propostas=propostas,
    )

    pessoas_by_doc: Dict[str, Dict[str, Any]] = {}
    if pessoas_path and pessoas_path.is_file() and needed_docs:
        for raw in _read_csv_rows(pessoas_path):
            mapped = map_pessoa_row(raw)
            if not mapped:
                continue
            dk = mapped["doc_key"]
            if dk in needed_docs and dk not in pessoas_by_doc:
                pessoas_by_doc[dk] = mapped
            if len(pessoas_by_doc) >= len(needed_docs):
                break

    for prop in propostas:
        if prop.get("fornecedor_nome"):
            continue
        person = pessoas_by_doc.get(prop.get("doc_key") or "")
        if person:
            prop["fornecedor_nome"] = person.get("fornecedor_nome")
            prop["fornecedor_uf"] = person.get("uf")
            prop["fornecedor_municipio_ibge"] = person.get("municipio_ibge")

    return {
        "data_dir": str(data_dir),
        "files": {
            "licitacao": str(lic_path) if lic_path else None,
            "item": str(item_path) if item_path else None,
            "proposta": str(prop_path) if prop_path else None,
            "pessoas": str(pessoas_path) if pessoas_path else None,
        },
        "licitacoes": licitacoes,
        "itens": itens,
        "propostas": propostas,
        "pessoas": list(pessoas_by_doc.values()),
        "pessoas_by_doc": pessoas_by_doc,
    }
