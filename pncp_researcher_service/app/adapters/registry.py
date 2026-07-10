from __future__ import annotations

from typing import Dict, List

from .base import PriceSourceAdapter
from .pncp_adapter import PncpAdapter

_REGISTRY: Dict[str, PriceSourceAdapter] = {
    PncpAdapter.id: PncpAdapter(),
}


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
