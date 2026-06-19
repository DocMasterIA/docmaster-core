"""Resolução de slot_package_key (payload + Referer) — partilhado por api e llm_proxy."""
from __future__ import annotations

from urllib.parse import urlparse

# Caminho do frontend (prefixo) → chave Prometheus / rag_service.
ROUTE_TO_SLOT_PACKAGE: dict[str, str] = {
    "/geracao/dispensa-art-75-i/manutencao-veiculos": "dispensa_75_i_manutencao_veiculos",
    "/geracao/dispensa-art-75-i/obras-servicos-engenharia": "dispensa_75_i_obras_engenharia",
    "/geracao/dispensa-art-75-ii/compras": "dispensa_75_ii_compras",
    "/geracao/dispensa-art-75-ii/servicos": "dispensa_75_ii_servicos",
    "/geracao/dispensa-art-75-ii/compras-servicos-inclusos": "dispensa_75_ii_compras_servicos_inclusos",
    "/geracao/dispensa-rapida/art-75-i/manutencao-veiculos": "dispensa_rapida_75_i_manutencao_veiculos",
    "/geracao/dispensa-rapida/art-75-i/obras-servicos-engenharia": "dispensa_rapida_75_i_obras_engenharia",
    "/geracao/dispensa-rapida/art-75-ii/compras": "dispensa_rapida_75_ii_compras",
    "/geracao/dispensa-rapida/art-75-ii/servicos": "dispensa_rapida_75_ii_servicos",
    "/geracao/dispensa-rapida/art-75-ii/compras-servicos-inclusos": "dispensa_rapida_75_ii_compras_servicos_inclusos",
    "/geracao/inexigibilidade-art-74-i/show-artistico": "inexigibilidade_74_i_manutencao_veiculos",
    "/geracao/inexigibilidade-art-74-i/manutencao-veiculos": "inexigibilidade_74_i_manutencao_veiculos",
    "/geracao/inexigibilidade-art-74-i/fornecedor-exclusivo": "inexigibilidade_74_i_fornecedor_exclusivo",
    "/geracao/inexigibilidade-art-74-i/manutencao-veiculos-preview": "inexigibilidade_74_i_manutencao_veiculos",
    "/geracao/inexigibilidade-art-74-i/fornecedor-exclusivo-preview": "inexigibilidade_74_i_fornecedor_exclusivo",
}


def resolve_slot_package_key(payload: dict | None, request) -> str:
    """Chave explícita no JSON, header ou inferida pelo Referer do browser."""
    p = payload or {}
    explicit = str(p.get("slot_package_key") or p.get("package") or "").strip().lower()
    if not explicit:
        meta = getattr(request, "META", None) or {}
        explicit = str(meta.get("HTTP_X_DOCMASTER_PACKAGE") or "").strip().lower()
    if explicit:
        return explicit
    referer = str(getattr(request, "META", {}).get("HTTP_REFERER") or "").strip()
    if not referer:
        return ""
    path = (urlparse(referer).path or "").lower()
    for route_path, package_key in ROUTE_TO_SLOT_PACKAGE.items():
        if path.startswith(route_path):
            return package_key
    return ""


def is_clausulas_objeto_justificativa_package(slot_package_key: str | None) -> bool:
    """Dispensa/inexigibilidade — objeto/justificativa podem usar gateway externo (Qwen)."""
    key = str(slot_package_key or "").strip().lower()
    return key.startswith("dispensa_") or key.startswith("inexigibilidade_")
