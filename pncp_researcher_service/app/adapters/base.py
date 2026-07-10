from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from .contracts import FederatedSearchQuery, MarketPriceHit


class PriceSourceAdapter(ABC):
    """Interface de conector para uma plataforma de preços."""

    id: str
    label: str

    @abstractmethod
    async def health(self) -> bool:
        """True se a fonte estiver operacional."""

    @abstractmethod
    async def search(self, query: FederatedSearchQuery) -> List[MarketPriceHit]:
        """Busca normalizada na plataforma."""

    def capabilities(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "supports_bulk": True,
            "supports_homolog_filter": True,
        }
