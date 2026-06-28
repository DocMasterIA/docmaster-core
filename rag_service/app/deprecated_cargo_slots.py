"""Campos de cargo/função removidos do produto — não devem ir para TR/DFD/Ofício."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Optional

from .tr_template import TRTemplateSlots

DEPRECATED_CARGO_OVERRIDE_KEYS = (
    "sol_oficio_destinatario_cargo",
    "sol_oficio_responsavel_cargo",
    "dfd_assinatura_cargo",
    "senhor_senhora_genero",
    "cargo_assinante_termo",
    "secretaria_usuario",
    "solicitacao_destinatario_cargo",
    "solicitacao_responsavel_cargo",
    "solicitacao_tratamento_cargo",
    "tr_cargo_assinante",
    "tr_termo_responsavel_cargo",
)

CARGO_SLOT_FIELDS_ON_TR_TEMPLATE = (
    "secretaria_usuario",
    "cargo_assinante_termo",
    "sol_oficio_destinatario_cargo",
    "sol_oficio_responsavel_cargo",
    "senhor_senhora_genero",
    "dfd_assinatura_cargo",
)


def strip_deprecated_cargo_override(override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not override:
        return {}
    out = dict(override)
    for key in DEPRECATED_CARGO_OVERRIDE_KEYS:
        out.pop(key, None)
    return out


def clear_deprecated_cargo_fields(slots: TRTemplateSlots) -> TRTemplateSlots:
    """Zera cargos no objeto final — evita fantasmas de preset/IA/contexto do usuário."""
    return replace(slots, **{field: "" for field in CARGO_SLOT_FIELDS_ON_TR_TEMPLATE})
