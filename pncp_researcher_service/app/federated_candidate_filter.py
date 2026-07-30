"""
Pós-filtro de qualidade para hits de plataformas indexadas (TCE / Compras / NF).

Aplica as mesmas rejeições category/spec do PNCP local e exige sobreposição de
tokens significativos além do 1º token do FTS (quando o termo tiver ≥2).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .product_category_match import product_category_strict_reject
from .product_spec_match import product_spec_strict_reject
from .search_text_clean import normalize_for_search

_SKIP_TOKENS = frozenset(
    {
        "de",
        "da",
        "do",
        "das",
        "dos",
        "com",
        "para",
        "em",
        "por",
        "a",
        "o",
        "e",
        "ou",
        "um",
        "uma",
        "tipo",
        "marca",
        "modelo",
        "unidade",
        "unidades",
        "caixa",
        "caixas",
        "pacote",
        "pacotes",
        "esteril",
        "estéril",
        "cloridrato",
        "sodica",
        "sodico",
    }
)


def _significant_tokens(termo: str) -> List[str]:
    norm = normalize_for_search(termo or "")
    out: List[str] = []
    for tok in norm.split():
        if len(tok) < 4:
            continue
        if tok in _SKIP_TOKENS:
            continue
        if re.fullmatch(r"\d+([.,]\d+)?%?", tok):
            # Mantém % / números relevantes do pedido (ex.: 0,3% → token normalizado).
            out.append(tok)
            continue
        if re.match(r"^\d", tok):
            out.append(tok)
            continue
        out.append(tok)
    return out


def _secondary_token_overlap(termo: str, descricao: str) -> bool:
    """
    Se o termo tem ≥2 tokens significativos, exige que pelo menos um além do
    primeiro apareça na descrição (evita colírio←comprimido só pelo princípio ativo).
    """
    sig = _significant_tokens(termo)
    if len(sig) < 2:
        return True
    desc_n = normalize_for_search(descricao or "")
    if not desc_n:
        return False
    for tok in sig[1:]:
        if len(tok) >= 2 and tok in desc_n:
            return True
    return False


def evaluate_platform_candidate(termo: str, descricao: str) -> Tuple[bool, Optional[str]]:
    """
    Retorna (aceitar, search_tier).
    tier aproximado: strict se vários tokens batem; core se só âncora+1; flex senão.
    """
    item = {"descricao_item": descricao or ""}
    if product_category_strict_reject(termo, item):
        return False, None
    if product_spec_strict_reject(termo, item):
        return False, None
    if not _secondary_token_overlap(termo, descricao):
        return False, None

    sig = _significant_tokens(termo)
    desc_n = normalize_for_search(descricao or "")
    hits = sum(1 for t in sig if t in desc_n)
    if len(sig) >= 2 and hits >= len(sig):
        return True, "strict"
    if len(sig) >= 2 and hits >= 2:
        return True, "core"
    if hits >= 1:
        return True, "flex"
    return True, "flex"


def filter_platform_search_rows(termo: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filtra rows do platform_item_search e anexa search_tier quando aceitos."""
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        desc = str(row.get("descricao") or row.get("descricao_item") or "").strip()
        ok, tier = evaluate_platform_candidate(termo, desc)
        if not ok:
            continue
        enriched = dict(row)
        if tier:
            enriched["search_tier"] = tier
        out.append(enriched)
    return out
