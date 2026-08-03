from __future__ import annotations

from typing import Any, Dict, List

from ..config import PNCP_FEDERATED_PLATFORM_SEARCH_LIMIT
from ..platform_index.registry import get_platform_spec
from ..platform_index.schema import platform_index_stats
from ..platform_index.search import platform_item_search
from .base import PriceSourceAdapter
from .contracts import FederatedSearchQuery, MarketPriceHit
from .mapping import platform_row_to_hit


class IndexedPlatformAdapter(PriceSourceAdapter):
    """Adapter base para plataformas com índice SQLite platform_index."""

    id: str
    label: str
    inciso_default: str = "inciso_ii"
    esfera_default: str = "estadual"

    async def health(self) -> bool:
        spec = get_platform_spec(self.id)
        if spec is None or not spec.db_path:
            return False
        if not spec.db_exists():
            return False
        stats = platform_index_stats(spec.db_path)
        return bool(stats.get("search_ready"))

    async def search(self, query: FederatedSearchQuery) -> List[MarketPriceHit]:
        spec = get_platform_spec(self.id)
        if spec is None or spec.schema_kind != "platform_index":
            return []
        uf = query.uf or spec.uf_scope
        # Respeita tamanho_pagina do request, com teto configurável (default 200).
        requested = max(10, int(query.tamanho_pagina or PNCP_FEDERATED_PLATFORM_SEARCH_LIMIT))
        limit = min(int(PNCP_FEDERATED_PLATFORM_SEARCH_LIMIT), requested)
        rows = platform_item_search(
            spec,
            termo=query.termo_busca,
            uf=uf,
            limit=limit,
        )
        from ..federated_candidate_filter import filter_platform_search_rows

        # Paridade com local_item_search: anota todos os tiers (incl. flex);
        # QUALITY_FIRST aplica-se na Camada B / ensure_top3 / bulk.
        rows = filter_platform_search_rows(
            query.termo_busca or "",
            rows,
            quality_first=False,
        )
        defaults = {
            "inciso_default": spec.inciso_default,
            "esfera_default": spec.esfera_default,
        }
        return [platform_row_to_hit(r, plataforma=self.id, spec_defaults=defaults) for r in rows]

    def capabilities(self) -> Dict[str, Any]:
        spec = get_platform_spec(self.id)
        base = super().capabilities()
        base.update(
            {
                "index_kind": "platform_index",
                "uf_scope": spec.uf_scope if spec else None,
                "db_path": spec.db_path if spec else None,
                "search_ready": spec.search_ready if spec else False,
            }
        )
        return base


class TceRsAdapter(IndexedPlatformAdapter):
    id = "tce_rs"
    label = "TCE-RS (LicitaCon)"
    inciso_default = "inciso_ii"
    esfera_default = "estadual"


class ComprasGovAdapter(IndexedPlatformAdapter):
    """Leitura do índice SQLite alimentado por CSV Dados Abertos Compras.gov.

    Sem ingest (ainda): health=False e search=[]. Mesmo contrato que TCE-RS.
    """

    id = "compras_gov"
    label = "Compras.gov (Dados Abertos)"
    inciso_default = "inciso_i"
    esfera_default = "federal"


class NotasFiscaisAdapter(IndexedPlatformAdapter):
    """Leitura do índice SQLite alimentado por CSV Portal da Transparência (NFe).

    Scaffold Fase 1: sem ingest → health=False e search=[]. Inciso V.
    """

    id = "notas_fiscais"
    label = "Notas Fiscais (Portal da Transparência)"
    inciso_default = "inciso_v"
    esfera_default = "federal"
