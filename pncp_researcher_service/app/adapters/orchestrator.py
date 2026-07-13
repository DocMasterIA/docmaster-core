"""
Camada B — orquestração unificada de hits multi-plataforma.

Após merge/crosslink/dedup na Camada A, todos os candidatos passam pelo mesmo
pipeline (faixa regional, scoring, rerank, top 3) via service.orchestrate_merged_candidate_pool.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .contracts import FederatedSearchQuery, MarketPriceHit
from .mapping import hits_to_pncp_rows


def prepare_federated_candidate_rows(hits: List[MarketPriceHit]) -> List[Dict[str, Any]]:
    """Converte MarketPriceHit → dict rows compatíveis com o pipeline de scoring."""
    rows = hits_to_pncp_rows(hits)
    for row in rows:
        plat = str(row.get("plataforma") or "unknown").strip().lower()
        row.setdefault("plataforma", plat)
        if not str(row.get("origem") or "").strip():
            row["origem"] = f"federated_{plat}"
    return rows


async def orchestrate_federated_hits(
    query: FederatedSearchQuery,
    hits: List[MarketPriceHit],
    *,
    source_stats: Dict[str, Any],
    total_hits: int,
    total_after_dedup: int,
) -> Dict[str, Any]:
    """
    Aplica faixa, scoring, rerank e top 3 sobre hits já deduplicados de N fontes.
    """
    from ..service import orchestrate_merged_candidate_pool

    payload = query.to_market_request()
    rows = prepare_federated_candidate_rows(hits)
    base_stats: Dict[str, Any] = {
        "federated": True,
        "fontes": dict(source_stats),
        "total_hits": int(total_hits),
        "total_apos_dedup": int(total_after_dedup),
        "crosslink_aplicado": True,
    }
    funil_seed: Dict[str, Any] = {
        "federated": True,
        "fontes": dict(source_stats),
        "total_hits": int(total_hits),
        "total_apos_dedup": int(total_after_dedup),
    }
    return await orchestrate_merged_candidate_pool(
        payload,
        rows,
        base_stats=base_stats,
        funil=funil_seed,
        source_label="federated_merged",
        federated_source_stats=source_stats,
        fontes_habilitadas=list(query.fontes_habilitadas or []),
    )
