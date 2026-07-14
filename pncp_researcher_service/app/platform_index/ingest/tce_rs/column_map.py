from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, Optional, Tuple


def normalize_header(name: str) -> str:
    s = unicodedata.normalize("NFKD", str(name or ""))
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s


def _pick(row: Dict[str, Any], aliases: Iterable[str]) -> Optional[str]:
    for alias in aliases:
        val = row.get(alias)
        if val is None:
            continue
        s = str(val).strip()
        if s:
            return s
    return None


def _pick_float(row: Dict[str, Any], aliases: Iterable[str]) -> Optional[float]:
    raw = _pick(row, aliases)
    if raw is None:
        return None
    cleaned = raw.replace("R$", "").replace(" ", "").strip()
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        n = float(cleaned)
        return n if n >= 0 else None
    except ValueError:
        return None


def process_key_parts(row: Dict[str, Any]) -> Optional[Tuple[str, str, str, str]]:
    org = _pick(row, ("cd_orgao", "codigo_orgao", "orgao_id"))
    nr = _pick(row, ("nr_licitacao", "numero_licitacao", "num_licitacao"))
    ano = _pick(row, ("ano_licitacao", "ano"))
    mod = _pick(row, ("cd_tipo_modalidade", "tipo_modalidade", "modalidade"))
    if org and nr and ano and mod:
        return (org, ano, nr, mod)
    return None


def build_licitacao_id(row: Dict[str, Any]) -> Optional[str]:
    """
    Identificador estável do processo no índice.
    Preferência: chave composta LicitaCon; fallback: id_licitacao das fixtures antigas.
    """
    parts = process_key_parts(row)
    if parts:
        org, ano, nr, mod = parts
        return f"{org}:{ano}:{nr}:{mod}"
    return _pick(
        row,
        (
            "id_licitacao",
            "codigo_licitacao",
            "cod_licitacao",
            "licitacao_id",
            "id",
        ),
    )


def build_numero_item(row: Dict[str, Any]) -> Optional[str]:
    lote = _pick(row, ("nr_lote", "numero_lote", "lote"))
    item = _pick(
        row,
        (
            "nr_item",
            "numero_item",
            "id_item",
            "item",
            "seq_item",
            "sequencial_item",
        ),
    )
    if lote and item:
        return f"{lote}:{item}"
    return item


def doc_key(tp: Optional[str], nr: Optional[str]) -> Optional[str]:
    if not nr:
        return None
    digits = re.sub(r"\D", "", str(nr))
    tp_n = (tp or "").strip().upper() or "J"
    if digits:
        return f"{tp_n}:{digits}"
    s = str(nr).strip()
    return f"{tp_n}:{s}" if s else None


# --- Aliases LicitaCon reais + fallback fixtures ---

LICITACAO_PROCESSO_ALIASES = (
    "nr_processo",
    "numero_processo",
    "num_processo",
    "processo",
    "numero",
)
LICITACAO_ORGAO_ALIASES = (
    "nm_orgao",
    "orgao",
    "nome_orgao",
    "unidade_gestora",
    "ug",
    "entidade",
)
LICITACAO_MUNICIPIO_ALIASES = ("municipio", "nome_municipio", "cidade")
LICITACAO_OBJETO_ALIASES = (
    "ds_objeto",
    "objeto",
    "objeto_licitacao",
    "descricao_objeto",
)
LICITACAO_DATA_ALIASES = (
    "dt_homologacao",
    "dt_adjudicacao",
    "dt_abertura",
    "data_publicacao",
    "data_abertura",
    "data",
    "dt_publicacao",
)
LICITACAO_URL_ALIASES = (
    "link_licitacon_cidadao",
    "url_origem",
    "link",
)
LICITACAO_PNCP_ALIASES = ("numero_pncp", "pncp", "numero_controle_pncp")

ITEM_DESC_ALIASES = (
    "ds_item",
    "descricao",
    "descricao_item",
    "especificacao",
    "objeto_item",
)
ITEM_QTD_ALIASES = ("qt_itens", "quantidade", "qtd", "qtde")
ITEM_UNIDADE_ALIASES = ("sg_unidade_medida", "unidade", "unidade_medida", "und")
ITEM_ESTIMADO_ALIASES = ("vl_unitario_estimado", "valor_unitario_estimado")
ITEM_HOMOLOG_ALIASES = ("vl_unitario_homologado", "valor_unitario_homologado")

PROPOSTA_VALOR_ALIASES = (
    "vl_unitario",
    "valor_unitario",
    "valor",
    "preco_unitario",
    "valor_proposta",
)
PROPOSTA_HOMOLOG_ALIASES = (
    "vl_unitario_homologado",
    "valor_unitario_homologado",
    "valor_homologado",
    "vl_homologado",
    "valor_vencedor",
)
PROPOSTA_FORNECEDOR_ALIASES = (
    "nm_pessoa",
    "fornecedor",
    "nome_fornecedor",
    "razao_social",
    "licitante",
)
PROPOSTA_CNPJ_ALIASES = (
    "nr_documento",
    "cnpj",
    "cnpj_fornecedor",
    "cnpj_cpf",
    "documento",
)
PROPOSTA_RESULT_ALIASES = (
    "tp_resultado_proposta",
    "resultado_proposta",
    "tp_resultado",
    "classificacao",
    "colocacao",
    "ranking",
    "posicao",
)
PROPOSTA_DATA_ALIASES = ("dt_homologacao", "data_homologacao")


def map_licitacao_row(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    lic_id = build_licitacao_id(raw)
    if not lic_id:
        return None
    nr_proc = _pick(raw, LICITACAO_PROCESSO_ALIASES)
    ano_proc = _pick(raw, ("ano_processo",))
    if nr_proc and ano_proc and "/" not in nr_proc:
        numero_processo = f"{nr_proc}/{ano_proc}"
    else:
        numero_processo = nr_proc
    return {
        "licitacao_id": lic_id,
        "numero_processo": numero_processo,
        "orgao": _pick(raw, LICITACAO_ORGAO_ALIASES),
        "municipio": _pick(raw, LICITACAO_MUNICIPIO_ALIASES),
        "objeto": _pick(raw, LICITACAO_OBJETO_ALIASES),
        "data_publicacao": _pick(raw, LICITACAO_DATA_ALIASES),
        "numero_pncp": _pick(raw, LICITACAO_PNCP_ALIASES),
        "url_origem": _pick(raw, LICITACAO_URL_ALIASES),
        "raw": dict(raw),
    }


def map_item_row(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    lic_id = build_licitacao_id(raw)
    num_item = build_numero_item(raw)
    desc = _pick(raw, ITEM_DESC_ALIASES)
    if not lic_id or not num_item or not desc:
        return None
    return {
        "licitacao_id": lic_id,
        "numero_item": num_item,
        "descricao": desc,
        "quantidade": _pick_float(raw, ITEM_QTD_ALIASES),
        "unidade_medida": _pick(raw, ITEM_UNIDADE_ALIASES),
        "valor_unitario_estimado": _pick_float(raw, ITEM_ESTIMADO_ALIASES),
        "valor_unitario_homologado": _pick_float(raw, ITEM_HOMOLOG_ALIASES),
        "tp_resultado_item": _pick(raw, ("tp_resultado_item", "resultado_item")),
        "tp_documento": _pick(raw, ("tp_documento",)),
        "nr_documento": _pick(raw, ("nr_documento",)),
        "raw": dict(raw),
    }


def map_proposta_row(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    lic_id = build_licitacao_id(raw)
    num_item = build_numero_item(raw)
    if not lic_id or not num_item:
        return None
    tp = _pick(raw, ("tp_documento",))
    nr = _pick(raw, PROPOSTA_CNPJ_ALIASES)
    return {
        "licitacao_id": lic_id,
        "numero_item": num_item,
        "valor_unitario": _pick_float(raw, PROPOSTA_VALOR_ALIASES),
        "valor_unitario_homologado": _pick_float(raw, PROPOSTA_HOMOLOG_ALIASES),
        "fornecedor_nome": _pick(raw, PROPOSTA_FORNECEDOR_ALIASES),
        "cnpj_fornecedor": nr,
        "tp_documento": tp,
        "doc_key": doc_key(tp, nr),
        "classificacao": _pick(raw, PROPOSTA_RESULT_ALIASES),
        "tp_resultado_proposta": _pick(raw, ("tp_resultado_proposta", "resultado_proposta")),
        "data_homologacao": _pick(raw, PROPOSTA_DATA_ALIASES),
        "raw": dict(raw),
    }


def map_pessoa_row(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tp = _pick(raw, ("tp_documento",))
    nr = _pick(raw, ("nr_documento", "cnpj", "cpf"))
    key = doc_key(tp, nr)
    nome = _pick(raw, ("nm_pessoa", "nome", "razao_social", "nome_pessoa"))
    if not key or not nome:
        return None
    return {
        "doc_key": key,
        "fornecedor_nome": nome,
        "uf": _pick(raw, ("sg_uf", "uf")),
        "municipio_ibge": _pick(raw, ("cd_municipio_ibge", "codigo_municipio_ibge")),
        "raw": dict(raw),
    }


def normalize_csv_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {normalize_header(k): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def uniquify_fieldnames(fieldnames: list[str]) -> list[str]:
    """Evita colisão de DictReader quando o CSV repete TP_DOCUMENTO/NR_DOCUMENTO."""
    seen: Dict[str, int] = {}
    out: list[str] = []
    for raw in fieldnames:
        base = normalize_header(raw) or "col"
        n = seen.get(base, 0)
        seen[base] = n + 1
        out.append(base if n == 0 else f"{base}__{n}")
    return out
