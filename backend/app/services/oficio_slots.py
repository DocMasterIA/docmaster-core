"""Normalização de slots do Ofício (preset → override canônico)."""

from __future__ import annotations

from typing import Any, Dict, Optional


def normalize_oficio_slots_override(override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
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

    return o
