from __future__ import annotations

from typing import Any, Dict, List

from .base import PriceSourceAdapter
from .contracts import FederatedSearchQuery, MarketPriceHit
from .mapping import pncp_row_to_hit


class PncpAdapter(PriceSourceAdapter):
    """Adapter #1 — envolve market_search_intelligent existente."""

    id = "pncp"
    label = "PNCP"

    async def health(self) -> bool:
        return True

    async def search(self, query: FederatedSearchQuery) -> List[MarketPriceHit]:
        from ..service import market_search_intelligent

        payload = query.to_market_request()
        data = await market_search_intelligent(payload)
        itens = list(data.get("itens") or [])
        return [pncp_row_to_hit(row) for row in itens if isinstance(row, dict)]

    async def search_raw(self, query: FederatedSearchQuery) -> Dict[str, Any]:
        """Retorno completo do pipeline PNCP (paridade com /market-search/intelligent)."""
        from ..service import market_search_intelligent

        payload = query.to_market_request()
        return await market_search_intelligent(payload)
