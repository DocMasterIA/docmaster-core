"""Normalização de slots do Ofício (preset do frontend → chaves do template)."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

_LEI_14133_SUFFIX_RE = re.compile(
    r",?\s*da\s+Lei\s+n[oº°.]?\s*\.?\s*14[\./]?133(?:/\d{4})?\s*$",
    re.IGNORECASE,
)


def normalize_sol_oficio_artigo_inciso(value: Any) -> str:
    """
    Slot (SOL_OFICIO_ARTIGO_INCISO): só artigo + inciso.
    Remove sufixo «, da Lei nº 14.133/2021» (o ofício já cita a lei no corpo).
    """
    text = str(value or "").strip()
    if not text:
        return ""
    text = _LEI_14133_SUFFIX_RE.sub("", text).strip()
    return text.rstrip(",").strip()


def normalize_oficio_slots_override(override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Garante chaves canônicas do Ofício a partir de aliases do preset/dados fixos.
    Idempotente — não sobrescreve valores já preenchidos no override.
    """
    if not isinstance(override, dict):
        return {}
    o = dict(override)

    if not str(o.get("ao_senhor_genero") or "").strip():
        v = str(o.get("solicitacao_tratamento_nome") or "").strip()
        if v:
            o["ao_senhor_genero"] = v

    if not str(o.get("senhor_senhora_genero") or "").strip():
        for key in (
            "senhor_senhora_genero",
            "solicitacao_destinatario_tratamento_cargo",
            "solicitacao_tratamento_cargo",
        ):
            v = str(o.get(key) or "").strip()
            if v:
                o["senhor_senhora_genero"] = v
                break

    if not str(o.get("sol_oficio_destinatario_nome") or "").strip():
        v = str(o.get("solicitacao_destinatario_nome") or "").strip()
        if v:
            o["sol_oficio_destinatario_nome"] = v

    if not str(o.get("sol_oficio_destinatario_cargo") or "").strip():
        v = str(o.get("solicitacao_destinatario_cargo") or "").strip()
        if v:
            o["sol_oficio_destinatario_cargo"] = v

    if o.get("sol_oficio_artigo_inciso") is not None:
        o["sol_oficio_artigo_inciso"] = normalize_sol_oficio_artigo_inciso(
            o.get("sol_oficio_artigo_inciso")
        )

    return o
