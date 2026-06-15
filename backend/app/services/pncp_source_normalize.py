"""Normalização de campos PNCP no payload antes de persistir (geo, etc.)."""
from __future__ import annotations

from typing import Any, Dict


def normalize_pncp_geo_in_payload(it: Dict[str, Any]) -> bool:
    """
    Promove município/UF do JSON PNCP (unidadeOrgao) para o topo do dict.
    Usado no save da cotação e no PDF — sem inferir do nome do órgão.
    """
    if not isinstance(it, dict):
        return False
    changed = False
    mun = str(it.get("municipio") or it.get("municipioNome") or "").strip()
    uf = str(it.get("uf") or it.get("ufSigla") or "").strip().upper()[:2]

    uo = it.get("unidadeOrgao") or it.get("unidade_orgao")
    if isinstance(uo, dict):
        if not mun:
            mun = str(uo.get("municipioNome") or uo.get("municipio") or "").strip()
        if not uf:
            uf = str(uo.get("ufSigla") or uo.get("uf") or "").strip().upper()[:2]

    if mun and mun != str(it.get("municipio") or "").strip():
        it["municipio"] = mun
        changed = True
    elif mun and not str(it.get("municipio") or "").strip():
        it["municipio"] = mun
        changed = True

    if uf and uf != str(it.get("uf") or "").strip().upper()[:2]:
        it["uf"] = uf
        changed = True
    elif uf and not str(it.get("uf") or "").strip():
        it["uf"] = uf
        changed = True
    return changed
