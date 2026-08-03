"""Rejeita itens de categoria diferente do núcleo do termo (ex.: fio → luva)."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from .search_text_clean import normalize_for_search

# Primeira palavra da descrição PNCP indica categoria do item, não material secundário.
_MISMATCH_PRIMARY_NOUNS = frozenset(
    {
        "luva",
        "luvas",
        "camiseta",
        "camisetas",
        "bermuda",
        "bermudas",
        "calca",
        "calcas",
        "calça",
        "calças",
        "jaqueta",
        "jaquetas",
        "cadeira",
        "cadeiras",
        "mesa",
        "mesas",
        "kit",
        "kits",
        "caixa",
        "caixas",
        "abracadeira",
        "abraçadeira",
        "abracadeiras",
        "estante",
        "estantes",
        "enxoval",
    }
)


def _query_head_noun(termo_busca: str) -> Optional[str]:
    norm = normalize_for_search(termo_busca or "")
    for tok in norm.split():
        if len(tok) >= 3:
            return tok
    return None


def _primary_noun(descricao: str) -> str:
    norm = normalize_for_search(descricao or "")
    for tok in norm.split():
        if len(tok) >= 3:
            return tok
    return ""


def product_category_strict_reject(termo_busca: str, item: Dict[str, Any]) -> bool:
    """
    True se o item é claramente de outra categoria que o termo pesquisado.
    Ex.: busca por FIO NYLON não deve aceitar LUVA ... fios de nylon.
    """
    head = _query_head_noun(termo_busca)
    if not head:
        return False
    desc = str(item.get("descricao_item") or item.get("descricao") or "").strip()
    if not desc:
        return False
    primary = _primary_noun(desc)
    if primary in _MISMATCH_PRIMARY_NOUNS and primary != head:
        return True
    if head == "fio":
        prefix = normalize_for_search(desc)[:160]
        if not re.search(r"\bfio(s)?\b", prefix):
            return True

    return False
