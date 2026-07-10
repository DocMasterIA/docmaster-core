from __future__ import annotations

from typing import Dict, List, Optional

from ..platform_index.registry import get_platform_spec, list_platform_specs
from ..platform_index.schema import platform_spec_with_stats
from .base import PriceSourceAdapter
from .indexed_platform_adapter import TceRsAdapter
from .pncp_adapter import PncpAdapter

_REGISTRY: Dict[str, PriceSourceAdapter] = {
    PncpAdapter.id: PncpAdapter(),
    TceRsAdapter.id: TceRsAdapter(),
}


def register_adapter(adapter: PriceSourceAdapter) -> None:
    _REGISTRY[adapter.id] = adapter


def list_adapter_ids() -> List[str]:
    return list(_REGISTRY.keys())


def get_adapters(source_ids: List[str]) -> List[PriceSourceAdapter]:
    out: List[PriceSourceAdapter] = []
    for sid in source_ids:
        key = str(sid or "").strip().lower()
        adapter = _REGISTRY.get(key)
        if adapter is not None:
            out.append(adapter)
    return out


def get_adapter(source_id: str) -> Optional[PriceSourceAdapter]:
    return _REGISTRY.get(str(source_id or "").strip().lower())


def list_platform_index_catalog() -> List[dict]:
    """Catálogo de plataformas cadastradas com metadados de .db e cruzamento."""
    items: List[dict] = []
    for spec in list_platform_specs(include_disabled=True):
        entry = platform_spec_with_stats(spec)
        adapter = get_adapter(spec.id)
        if adapter is not None:
            entry["adapter"] = adapter.capabilities()
        items.append(entry)
    return items
