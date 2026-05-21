"""URLs absolutas para payloads de QR (download público, links externos)."""
from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest


def resolve_public_api_base_url(request: HttpRequest | None = None) -> str:
    """
    Base pública da API (sem barra final).

    Ordem: ``DOCMASTER_QR_PUBLIC_BASE_URL`` → ``request.build_absolute_uri('/')`` →
    ``SITE_URL`` do settings (se existir).
    """
    override = (getattr(settings, "DOCMASTER_QR_PUBLIC_BASE_URL", None) or "").strip()
    if override:
        return override.rstrip("/")
    if request is not None:
        return request.build_absolute_uri("/").rstrip("/")
    site = (getattr(settings, "SITE_URL", None) or "").strip()
    if site:
        return site.rstrip("/")
    return "https://api.docmasteria.com.br"


def build_public_absolute_url(base_url: str, path: str) -> str:
    """Junta base e path (path deve começar com ``/``)."""
    base = str(base_url).strip().rstrip("/") or resolve_public_api_base_url()
    p = path if path.startswith("/") else f"/{path}"
    return f"{base}{p}"
