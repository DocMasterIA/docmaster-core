from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from ..config import PNCP_FEDERATED_SEARCH_ENABLED, PNCP_FEDERATED_SOURCE_TIMEOUT_SECONDS
from .contracts import FederatedSearchQuery, MarketPriceHit
from .crosslink import assign_canonical_keys
from .dedup import dedupe_hits
from .mapping import hit_to_pncp_row
from .pncp_adapter import PncpAdapter
from .registry import get_adapters


async def _search_adapter_with_timeout(
    adapter_id: str,
    query: FederatedSearchQuery,
    *,
    timeout_s: float,
) -> tuple[str, List[MarketPriceHit], Optional[str]]:
    adapters = get_adapters([adapter_id])
    if not adapters:
        return adapter_id, [], f"fonte desconhecida: {adapter_id}"
    adapter = adapters[0]
    try:
        hits = await asyncio.wait_for(adapter.search(query), timeout=timeout_s)
        return adapter_id, hits, None
    except asyncio.TimeoutError:
        return adapter_id, [], "timeout"
    except Exception as exc:
        return adapter_id, [], str(exc)[:240]


async def federated_search(query: FederatedSearchQuery) -> Dict[str, Any]:
    """
    Orquestra busca em múltiplas fontes.
    Fast-path: sources=["pncp"] retorna resposta idêntica ao market_search_intelligent.
    """
    if not PNCP_FEDERATED_SEARCH_ENABLED:
        return {
            "ok": False,
            "filtros": {"fontes_habilitadas": query.fontes_habilitadas},
            "stats": {"erro": "federated_disabled"},
            "itens": [],
        }

    sources = [s for s in (query.fontes_habilitadas or ["pncp"]) if s]
    if not sources:
        sources = ["pncp"]

    # Paridade: uma fonte PNCP = pipeline atual sem round-trip.
    if sources == ["pncp"]:
        adapter = PncpAdapter()
        raw = await adapter.search_raw(query)
        stats = dict(raw.get("stats") or {})
        stats["fontes_consultadas"] = ["pncp"]
        stats["fontes_habilitadas"] = sources
        raw["stats"] = stats
        filtros = dict(raw.get("filtros") or {})
        filtros["fontes_habilitadas"] = sources
        raw["filtros"] = filtros
        itens = raw.get("itens") or []
        for row in itens:
            if isinstance(row, dict) and not row.get("plataforma"):
                row["plataforma"] = "pncp"
        return raw

    timeout_s = max(5.0, float(PNCP_FEDERATED_SOURCE_TIMEOUT_SECONDS or 20.0))
    tasks = [
        _search_adapter_with_timeout(source_id, query, timeout_s=timeout_s)
        for source_id in sources
    ]
    results = await asyncio.gather(*tasks)

    merged: List[MarketPriceHit] = []
    source_stats: Dict[str, Any] = {}
    for source_id, hits, err in results:
        source_stats[source_id] = {
            "hits": len(hits),
            "erro": err,
        }
        merged.extend(hits)

    linked = assign_canonical_keys(merged, persist=True)
    deduped = dedupe_hits(linked)
    deduped.sort(
        key=lambda h: float(h.valor_unitario_homologado or h.valor_unitario or 0),
        reverse=True,
    )
    top = deduped[:3]
    rows = [hit_to_pncp_row(h) for h in top]

    return {
        "ok": True,
        "filtros": {
            "termo_busca": query.termo_busca,
            "fontes_habilitadas": sources,
        },
        "stats": {
            "fontes_consultadas": sources,
            "fontes": source_stats,
            "total_hits": len(merged),
            "total_apos_dedup": len(deduped),
            "crosslink_aplicado": True,
        },
        "itens": rows,
    }
