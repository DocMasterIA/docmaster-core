"""Conectores e orquestração federada para pesquisa de preços multi-fonte."""

from .contracts import FederatedSearchQuery, MarketPriceHit
from .federated import federated_search

__all__ = [
    "FederatedSearchQuery",
    "MarketPriceHit",
    "federated_search",
]
