"""Totais de itens indexados em todas as fontes (PNCP + platform_index)."""
from __future__ import annotations

from typing import Any, Dict, List

from .registry import list_platform_specs
from .schema import platform_index_stats


def attach_federated_item_totals(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enriquece o payload de local-index/stats com totais por plataforma.

    Mantém `total_itens` = PNCP (compatível com backfill / cobertura fornecedor).
    Expõe `total_itens_todas_fontes` = PNCP + TCE-RS + futuras platforms
    (mesmo critério do front: volume bruto indexado, não só o subconjunto
    filtrado por homologação na busca).
    """
    out = dict(stats or {})
    pncp_n = int(out.get("total_itens") or 0)
    por: List[Dict[str, Any]] = [
        {
            "id": "pncp",
            "label": "PNCP",
            "total_itens": pncp_n,
            "schema_kind": "legacy_pncp",
            "search_ready": pncp_n > 0,
            "db_exists": pncp_n > 0,
        }
    ]
    outras = 0
    for spec in list_platform_specs(include_disabled=False):
        if spec.id == "pncp" or spec.schema_kind != "platform_index":
            continue
        st = platform_index_stats(spec.db_path) if spec.db_path else {}
        n = int(st.get("itens_leitura") or 0)
        outras += n
        por.append(
            {
                "id": spec.id,
                "label": spec.label,
                "total_itens": n,
                "schema_kind": spec.schema_kind,
                "search_ready": bool(st.get("search_ready")),
                "db_exists": bool(st.get("db_exists")),
            }
        )

    total_todas = pncp_n + outras
    out["total_itens_pncp"] = pncp_n
    out["total_itens_outras_plataformas"] = outras
    out["total_itens_todas_fontes"] = total_todas
    out["por_plataforma"] = por
    return out
