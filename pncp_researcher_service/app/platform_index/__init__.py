"""Índices SQLite por plataforma (TCE, PCP, …) + cruzamento cross-platform."""

from .registry import PlatformIndexSpec, get_platform_spec, list_platform_specs
from .schema import ensure_platform_index

__all__ = [
    "PlatformIndexSpec",
    "ensure_platform_index",
    "get_platform_spec",
    "list_platform_specs",
]
