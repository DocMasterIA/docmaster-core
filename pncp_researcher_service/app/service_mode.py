from __future__ import annotations

"""
Modos de processo do stack de preços.

SERVICE_MODE:
  feed       — escrita de índices (uma plataforma por processo via FEED_PLATFORM)
  researcher — leitura federada + Camada B (não roda ingest PNCP/TCE)
  all        — monolito local (dev); evita em produção

FEED_PLATFORM (só em SERVICE_MODE=feed|all):
  pncp        — índice legacy PNCP + worker 24/7
  tce_rs      — ingest LicitaCon → platform_index
  compras_gov — ingest CSV Dados Abertos → platform_index
  notas_fiscais — ingest CSV Portal da Transparência → platform_index
  *           — futuro: id registrado no platform_index.registry
  (vazio / all) — monolito feed: PNCP + rotas de todas as plataformas (legado)
"""

import os
from typing import FrozenSet

SERVICE_MODE: str = (os.getenv("SERVICE_MODE", "all") or "all").strip().lower()
FEED_PLATFORM: str = (os.getenv("FEED_PLATFORM", "") or "").strip().lower()

# Plataformas batch cujo feed não usa o worker PNCP.
_NON_PNCP_FEED_PLATFORMS: FrozenSet[str] = frozenset(
    {"tce_rs", "compras_gov", "notas_fiscais"}
)


def is_feed_mode() -> bool:
    return SERVICE_MODE in {"all", "feed"}


def is_researcher_mode() -> bool:
    return SERVICE_MODE in {"all", "researcher"}


def feed_platform() -> str:
    """Plataforma deste processo feed. Vazio = feed monolito (legado)."""
    if FEED_PLATFORM in {"", "all", "*"}:
        return ""
    return FEED_PLATFORM


def is_pncp_feed() -> bool:
    """Este processo alimenta o índice PNCP (worker / local-index)."""
    if not is_feed_mode():
        return False
    plat = feed_platform()
    return plat in {"", "pncp"}


def is_platform_feed(platform_id: str) -> bool:
    """Este processo alimenta a plataforma batch indicada (ex.: tce_rs)."""
    if not is_feed_mode():
        return False
    plat = feed_platform()
    key = str(platform_id or "").strip().lower()
    if not plat:
        return True  # monolito feed: todas
    return plat == key


def pncp_ingest_worker_allowed() -> bool:
    """Worker 24/7 PNCP só no feed PNCP (não no feed TCE-RS)."""
    return is_pncp_feed()


def service_name() -> str:
    if SERVICE_MODE == "researcher":
        return "price_researcher_service"
    if SERVICE_MODE == "feed":
        plat = feed_platform()
        if plat == "pncp":
            return "price_index_feed_pncp"
        if plat:
            return f"price_index_feed_{plat}"
        return "price_index_feed_service"
    return "pncp_researcher_service"


def service_title() -> str:
    if SERVICE_MODE == "researcher":
        return "Price Researcher Service"
    if SERVICE_MODE == "feed":
        plat = feed_platform()
        if plat == "pncp":
            return "Price Index Feed — PNCP"
        if plat == "tce_rs":
            return "Price Index Feed — TCE-RS"
        if plat == "compras_gov":
            return "Price Index Feed — Compras.gov"
        if plat == "notas_fiscais":
            return "Price Index Feed — Notas Fiscais"
        if plat:
            return f"Price Index Feed — {plat}"
        return "Price Index Feed Service (legacy all-platforms)"
    return "PNCP Researcher Service (all)"
