from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, Optional


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


# Aliases prováveis no LicitaCon — revisar quando 1-TCE-DIS confirmar layout.
LICITACAO_ID_ALIASES = (
    "id_licitacao",
    "codigo_licitacao",
    "cod_licitacao",
    "numero_licitacao",
    "id",
    "licitacao_id",
)
LICITACAO_PROCESSO_ALIASES = ("numero_processo", "num_processo", "processo", "numero")
LICITACAO_ORGAO_ALIASES = ("orgao", "nome_orgao", "unidade_gestora", "ug", "entidade")
LICITACAO_MUNICIPIO_ALIASES = ("municipio", "nome_municipio", "cidade")
LICITACAO_OBJETO_ALIASES = ("objeto", "objeto_licitacao", "descricao_objeto")
LICITACAO_DATA_ALIASES = ("data_publicacao", "data_abertura", "data", "dt_publicacao")
LICITACAO_PNCP_ALIASES = ("numero_pncp", "pncp", "numero_controle_pncp")

ITEM_LICITACAO_ALIASES = LICITACAO_ID_ALIASES
ITEM_NUMERO_ALIASES = ("numero_item", "id_item", "item", "seq_item", "sequencial_item")
ITEM_DESC_ALIASES = ("descricao", "descricao_item", "especificacao", "objeto_item")
ITEM_QTD_ALIASES = ("quantidade", "qtd", "qtde")
ITEM_UNIDADE_ALIASES = ("unidade", "unidade_medida", "und")

PROPOSTA_LICITACAO_ALIASES = LICITACAO_ID_ALIASES
PROPOSTA_ITEM_ALIASES = ITEM_NUMERO_ALIASES
PROPOSTA_VALOR_ALIASES = (
    "valor_unitario",
    "valor",
    "preco_unitario",
    "vl_unitario",
    "valor_proposta",
)
PROPOSTA_HOMOLOG_ALIASES = (
    "valor_unitario_homologado",
    "valor_homologado",
    "vl_homologado",
    "valor_vencedor",
)
PROPOSTA_FORNECEDOR_ALIASES = ("fornecedor", "nome_fornecedor", "razao_social", "licitante")
PROPOSTA_CNPJ_ALIASES = ("cnpj", "cnpj_fornecedor", "cnpj_cpf", "documento")
PROPOSTA_CLASS_ALIASES = ("classificacao", "colocacao", "ranking", "posicao")


def map_licitacao_row(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    lic_id = _pick(raw, LICITACAO_ID_ALIASES)
    if not lic_id:
        return None
    return {
        "licitacao_id": lic_id,
        "numero_processo": _pick(raw, LICITACAO_PROCESSO_ALIASES),
        "orgao": _pick(raw, LICITACAO_ORGAO_ALIASES),
        "municipio": _pick(raw, LICITACAO_MUNICIPIO_ALIASES),
        "objeto": _pick(raw, LICITACAO_OBJETO_ALIASES),
        "data_publicacao": _pick(raw, LICITACAO_DATA_ALIASES),
        "numero_pncp": _pick(raw, LICITACAO_PNCP_ALIASES),
        "raw": dict(raw),
    }


def map_item_row(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    lic_id = _pick(raw, ITEM_LICITACAO_ALIASES)
    num_item = _pick(raw, ITEM_NUMERO_ALIASES)
    desc = _pick(raw, ITEM_DESC_ALIASES)
    if not lic_id or not num_item or not desc:
        return None
    return {
        "licitacao_id": lic_id,
        "numero_item": num_item,
        "descricao": desc,
        "quantidade": _pick_float(raw, ITEM_QTD_ALIASES),
        "unidade_medida": _pick(raw, ITEM_UNIDADE_ALIASES),
        "raw": dict(raw),
    }


def map_proposta_row(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    lic_id = _pick(raw, PROPOSTA_LICITACAO_ALIASES)
    num_item = _pick(raw, PROPOSTA_ITEM_ALIASES)
    if not lic_id or not num_item:
        return None
    valor = _pick_float(raw, PROPOSTA_VALOR_ALIASES)
    homolog = _pick_float(raw, PROPOSTA_HOMOLOG_ALIASES)
    classif = _pick(raw, PROPOSTA_CLASS_ALIASES)
    return {
        "licitacao_id": lic_id,
        "numero_item": num_item,
        "valor_unitario": valor,
        "valor_unitario_homologado": homolog,
        "fornecedor_nome": _pick(raw, PROPOSTA_FORNECEDOR_ALIASES),
        "cnpj_fornecedor": _pick(raw, PROPOSTA_CNPJ_ALIASES),
        "classificacao": classif,
        "raw": dict(raw),
    }


def normalize_csv_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {normalize_header(k): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
