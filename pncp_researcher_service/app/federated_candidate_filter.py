"""
Pós-filtro de qualidade para hits de plataformas indexadas (TCE / Compras / NF).

Reutiliza o mesmo esquema do PNCP local: build_search_query_tiers +
_match_row_search_tiers em descricao+material_servico, mais category/spec.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .config import PNCP_SEARCH_QUALITY_FIRST
from .product_category_match import product_category_strict_reject
from .product_spec_match import product_spec_strict_reject


def item_title_blob(item: Optional[Dict[str, Any]] = None, *, descricao: str = "", material_servico: str = "") -> str:
    """Mesmo texto de título do PNCP local: descricao + material_servico."""
    if item and isinstance(item, dict):
        desc = str(item.get("descricao_item") or item.get("descricao") or "").strip()
        mat = str(item.get("material_servico") or "").strip()
        return f"{desc} {mat}".strip()
    return f"{(descricao or '').strip()} {(material_servico or '').strip()}".strip()


def match_search_title_tier(
    termo: str,
    descricao: str,
    *,
    material_servico: str = "",
    quality_first: Optional[bool] = None,
) -> Optional[str]:
    """
    Mesmo matcher de título do índice PNCP local.

    Retorna label do tier (strict/core/flex/anchor) ou None se não casa.
    Com quality_first (default = PNCP_SEARCH_QUALITY_FIRST), só aceita strict/core.
    """
    from .local_index import build_search_query_tiers, _match_row_search_tiers

    qf = PNCP_SEARCH_QUALITY_FIRST if quality_first is None else bool(quality_first)
    tiers = build_search_query_tiers(termo or "")
    if not tiers:
        return None
    texto = item_title_blob(descricao=descricao, material_servico=material_servico)
    matched = _match_row_search_tiers(texto, tiers)
    if matched is None:
        return None
    label = str(matched.label or "").strip().lower()
    if qf and label not in ("strict", "core"):
        return None
    return label or None


def evaluate_platform_candidate(
    termo: str,
    descricao: str,
    *,
    material_servico: str = "",
    quality_first: Optional[bool] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Retorna (aceitar, search_tier) com o mesmo critério do PNCP local.
    """
    item = {
        "descricao_item": descricao or "",
        "material_servico": material_servico or "",
    }
    if product_category_strict_reject(termo, item):
        return False, None
    if product_spec_strict_reject(termo, item):
        return False, None
    tier = match_search_title_tier(
        termo,
        descricao,
        material_servico=material_servico,
        quality_first=quality_first,
    )
    if not tier:
        return False, None
    return True, tier


def filter_platform_search_rows(
    termo: str,
    rows: List[Dict[str, Any]],
    *,
    quality_first: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    """Filtra rows do platform_item_search e anexa search_tier PNCP real."""
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        desc = str(row.get("descricao") or row.get("descricao_item") or "").strip()
        mat = str(row.get("material_servico") or "").strip()
        ok, tier = evaluate_platform_candidate(
            termo,
            desc,
            material_servico=mat,
            quality_first=quality_first,
        )
        if not ok:
            continue
        enriched = dict(row)
        if tier:
            enriched["search_tier"] = tier
        out.append(enriched)
    return out
