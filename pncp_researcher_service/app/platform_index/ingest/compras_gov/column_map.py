"""
Mapeamento canônico CSV Dados Abertos Compras.gov → campos platform_index.

Views:
  VW_FT_PNCP_COMPRA       — cabeçalho do processo
  VW_FT_PNCP_COMPRA_ITEM  — item + preço/fornecedor

Join preferencial: cod_compra (também numero_controle_PNCP ↔ numero_controle_PNCP_compra).

A materialização de itens fica desligada até a alimentação anual explícita.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

# Cabeçalhos obrigatórios (após normalize_header) para validar a estrutura do CSV.
# Cada grupo é OR: basta um alias (schema legado vs mensal 2025+ do repositório SEGES).
REQUIRED_COMPRA_HEADER_GROUPS: Tuple[Tuple[str, ...], ...] = (
    ("cod_compra",),
    ("numero_controle_pncp",),
    ("orgao_entidade_razao_social",),
    ("unidade_orgao_uf_sigla",),
    ("unidade_orgao_municipio_nome",),
    ("modalidade_nome",),
)

REQUIRED_ITEM_HEADER_GROUPS: Tuple[Tuple[str, ...], ...] = (
    ("cod_compra",),
    ("numero_item_pncp", "numero_item", "numero_item_compra", "cod_item_compra"),
    ("numero_controle_pncp_compra", "id_contratacao_pncp"),
    ("descricao_resumida", "descricao_detalhada", "descricao"),
    ("unidade_medida",),
    ("quantidade",),
    ("valor_unitario_estimado", "valor_unitario_resultado"),
)

# Nomes canônicos (primeiro de cada grupo) — docs / column_map_spec / testes.
REQUIRED_COMPRA_HEADERS: Tuple[str, ...] = tuple(g[0] for g in REQUIRED_COMPRA_HEADER_GROUPS)
REQUIRED_ITEM_HEADERS: Tuple[str, ...] = tuple(g[0] for g in REQUIRED_ITEM_HEADER_GROUPS)

# Opcionais mas usados no map (preço homologado / fornecedor / join).
OPTIONAL_COMPRA_HEADERS: Tuple[str, ...] = (
    "id_compra",
    "link_sistema_origem",
    "data_publicacao_pncp",
    "ano_compra_pncp",
    "sequencial_compra_pncp",
    "orgao_entidade_cnpj",
    "existe_resultado",
    "objeto_compra",
)

OPTIONAL_ITEM_HEADERS: Tuple[str, ...] = (
    "cod_item_compra",
    "id_compra",
    "id_compra_item",
    "descricao_detalhada",
    "material_ou_servico_nome",
    "valor_unitario_resultado",
    "valor_total_resultado",
    "nome_fornecedor",
    "cod_fornecedor",
    "tem_resultado",
    "ano_compra",
    "sequencial_compra",
    "orgao_entidade_cnpj",
    "id_contratacao_pncp",
)


def normalize_header(name: str) -> str:
    s = unicodedata.normalize("NFKD", str(name or ""))
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s


def normalize_row_keys(row: Dict[str, Any]) -> Dict[str, Any]:
    return {normalize_header(k): v for k, v in (row or {}).items()}


def _pick(row: Dict[str, Any], aliases: Iterable[str]) -> Optional[str]:
    for alias in aliases:
        key = normalize_header(alias)
        val = row.get(key)
        if val is None:
            continue
        s = str(val).strip()
        if s and s.lower() not in {"null", "none", "nan"}:
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


def _truthy(raw: Optional[str]) -> bool:
    if raw is None:
        return False
    s = str(raw).strip().lower()
    return s in {"1", "true", "t", "yes", "y", "sim", "s"}


def _cnpj_digits(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    digits = "".join(ch for ch in str(v) if ch.isdigit())
    return digits or None


def missing_required_headers(headers: Sequence[str], required: Sequence[str]) -> List[str]:
    """Compat: lista plana de nomes canônicos (cada um obrigatório)."""
    have: Set[str] = {normalize_header(h) for h in headers}
    return [h for h in required if h not in have]


def missing_required_header_groups(
    headers: Sequence[str],
    groups: Sequence[Sequence[str]],
) -> List[str]:
    """Retorna o nome canônico (primeiro alias) de cada grupo sem nenhum match."""
    have: Set[str] = {normalize_header(h) for h in headers}
    missing: List[str] = []
    for group in groups:
        aliases = [normalize_header(a) for a in group]
        if not any(a in have for a in aliases):
            missing.append(group[0])
    return missing


def validate_compra_headers(headers: Sequence[str]) -> Dict[str, Any]:
    missing = missing_required_header_groups(headers, REQUIRED_COMPRA_HEADER_GROUPS)
    return {
        "ok": not missing,
        "view": "VW_FT_PNCP_COMPRA",
        "missing_required": missing,
        "headers_normalized": sorted({normalize_header(h) for h in headers}),
    }


def validate_item_headers(headers: Sequence[str]) -> Dict[str, Any]:
    missing = missing_required_header_groups(headers, REQUIRED_ITEM_HEADER_GROUPS)
    return {
        "ok": not missing,
        "view": "VW_FT_PNCP_COMPRA_ITEM",
        "missing_required": missing,
        "headers_normalized": sorted({normalize_header(h) for h in headers}),
    }


def build_processo_id(cod_compra: str) -> str:
    return f"compras_gov:{cod_compra}"


def build_plataforma_item_id(cod_compra: str, numero_item: str) -> str:
    return f"compras_gov:{cod_compra}:{numero_item}"


def map_compra_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Linha COMPRA → dict de processo (platform_processos + enrich no item).
    Retorna None se faltar chave de join.
    """
    r = normalize_row_keys(row)
    cod = _pick(r, ("cod_compra",))
    if not cod:
        return None
    numero_pncp = _pick(r, ("numero_controle_pncp", "numero_controle_PNCP"))
    return {
        "cod_compra": cod,
        "id_compra": _pick(r, ("id_compra",)),
        "processo_id": build_processo_id(cod),
        "numero_pncp": numero_pncp,
        "numero_processo": numero_pncp or cod,
        "orgao": _pick(r, ("orgao_entidade_razao_social",)),
        "orgao_cnpj": _cnpj_digits(_pick(r, ("orgao_entidade_cnpj",))),
        "municipio": _pick(r, ("unidade_orgao_municipio_nome",)),
        "uf": (_pick(r, ("unidade_orgao_uf_sigla",)) or "").upper() or None,
        "modalidade": _pick(r, ("modalidade_nome",)),
        "objeto": _pick(r, ("objeto_compra",)),
        "url_origem": _pick(r, ("link_sistema_origem",)),
        "data_publicacao": _pick(r, ("data_publicacao_pncp",)),
        "ano_compra": _pick(r, ("ano_compra_pncp", "ano_compra")),
        "sequencial_compra": _pick(r, ("sequencial_compra_pncp", "sequencial_compra")),
        "existe_resultado": _truthy(_pick(r, ("existe_resultado",))),
        "inciso_classificacao": "inciso_i",
        "esfera": "federal",
    }


def map_item_row(row: Dict[str, Any], *, compra: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Linha ITEM (+ COMPRA opcional) → dict pronto para materialize (futuro).

    Preço: valor_unitario_resultado (homologado) tem prioridade;
    valor_unitario_estimado fica como fallback em valor_unitario.
    """
    r = normalize_row_keys(row)
    cod = _pick(r, ("cod_compra",))
    # Mensal SEGES 2025+: numero_item / descricao; legado: numero_item_pncp / descricao_resumida.
    numero_item = _pick(
        r,
        ("numero_item_pncp", "numero_item", "numero_item_compra", "cod_item_compra"),
    )
    if not cod or not numero_item:
        return None

    compra = compra or {}
    hom = _pick_float(r, ("valor_unitario_resultado",))
    est = _pick_float(r, ("valor_unitario_estimado",))
    tem_resultado = _truthy(_pick(r, ("tem_resultado",))) or (hom is not None and hom > 0)

    descricao = _pick(r, ("descricao_resumida", "descricao_detalhada", "descricao")) or ""
    numero_pncp = (
        _pick(r, ("numero_controle_pncp_compra", "id_contratacao_pncp"))
        or compra.get("numero_pncp")
    )

    return {
        "cod_compra": cod,
        "processo_id": build_processo_id(cod),
        "plataforma_item_id": build_plataforma_item_id(cod, numero_item),
        "numero_item": numero_item,
        "numero_pncp": numero_pncp,
        "numero_processo": numero_pncp or cod,
        "descricao": descricao,
        "material_servico": _pick(r, ("material_ou_servico_nome", "material_ou_servico")),
        "unidade_medida": _pick(r, ("unidade_medida",)),
        "quantidade": _pick_float(r, ("quantidade", "quantidade_resultado")),
        "valor_unitario": est if est and est > 0 else (hom if hom and hom > 0 else None),
        "valor_unitario_homologado": hom if hom and hom > 0 else None,
        "tem_resultado": tem_resultado,
        "fornecedor_nome": _pick(r, ("nome_fornecedor",)),
        "cnpj_fornecedor": _cnpj_digits(_pick(r, ("cod_fornecedor",))),
        "orgao": compra.get("orgao") or None,
        "municipio": compra.get("municipio") or None,
        "uf": compra.get("uf") or None,
        "modalidade": compra.get("modalidade") or None,
        "url_origem": compra.get("url_origem") or None,
        "data_referencia": compra.get("data_publicacao") or _pick(r, ("data_resultado", "data_atualizacao_pncp")),
        "ano_compra": _pick(r, ("ano_compra",)) or compra.get("ano_compra"),
        "sequencial_compra": _pick(r, ("sequencial_compra",)) or compra.get("sequencial_compra"),
        "inciso_classificacao": "inciso_i",
        "esfera": "federal",
        "plataforma": "compras_gov",
    }


def column_map_spec() -> Dict[str, Any]:
    """Metadados da estrutura para status/docs/UI operacional."""
    return {
        "platform_id": "compras_gov",
        "views": {
            "compra": "VW_FT_PNCP_COMPRA",
            "compra_item": "VW_FT_PNCP_COMPRA_ITEM",
        },
        "join_keys": ["cod_compra", "numero_controle_PNCP ↔ numero_controle_PNCP_compra"],
        "required_compra_headers": list(REQUIRED_COMPRA_HEADERS),
        "required_item_headers": list(REQUIRED_ITEM_HEADERS),
        "optional_compra_headers": list(OPTIONAL_COMPRA_HEADERS),
        "optional_item_headers": list(OPTIONAL_ITEM_HEADERS),
        "price_priority": ["valor_unitario_resultado", "valor_unitario_estimado"],
        "description_priority": ["descricao_resumida", "descricao_detalhada"],
        "defaults": {"inciso_classificacao": "inciso_i", "esfera": "federal"},
        "item_materialize_enabled": True,
    }
