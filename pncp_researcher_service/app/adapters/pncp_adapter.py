from __future__ import annotations

from typing import Any, Dict, List

from ..config import PNCP_FEDERATED_PLATFORM_SEARCH_LIMIT
from .base import PriceSourceAdapter
from .contracts import FederatedSearchQuery, MarketPriceHit
from .mapping import pncp_row_to_hit


class PncpAdapter(PriceSourceAdapter):
    """Adapter PNCP — no multi-fonte contribui pool local (união justa com TCE/Compras)."""

    id = "pncp"
    label = "PNCP"

    async def health(self) -> bool:
        return True

    async def search(self, query: FederatedSearchQuery) -> List[MarketPriceHit]:
        """
        Multi-fonte: devolve candidatos do índice local PNCP (não o top-3 inteligente).

        Assim PNCP, TCE-RS e Compras.gov entram no mesmo Camada B com pools
        comparáveis. O caminho só-PNCP continua em ``search_raw`` / intelligent.
        """
        from ..local_index import local_item_search

        limit = max(50, min(1000, int(PNCP_FEDERATED_PLATFORM_SEARCH_LIMIT)))
        raw = local_item_search(
            query.termo_busca,
            uf=query.uf,
            municipio=query.municipio,
            recortes_geograficos=query.recortes_geograficos,
            codigo_modalidade=query.codigo_modalidade,
            limit=limit,
            somente_homologados=query.somente_homologados,
        )
        itens = list((raw or {}).get("itens") or [])
        hits: List[MarketPriceHit] = []
        for row in itens:
            if not isinstance(row, dict):
                continue
            row = dict(row)
            row.setdefault("plataforma", "pncp")
            hits.append(pncp_row_to_hit(row))
        return hits

    async def search_raw(self, query: FederatedSearchQuery) -> Dict[str, Any]:
        """Retorno completo do pipeline PNCP (paridade com /market-search/intelligent)."""
        from ..service import market_search_intelligent

        payload = query.to_market_request()
        return await market_search_intelligent(payload)
