"""Campos de cargo/função removidos do drawer — limpar antes de enviar ao rag_service."""

from __future__ import annotations

from typing import Any, Dict, Optional

DEPRECATED_CARGO_OVERRIDE_KEYS = (
    "sol_oficio_responsavel_cargo",
    "dfd_assinatura_cargo",
    "cargo_assinante_termo",
    "secretaria_usuario",
    "solicitacao_responsavel_cargo",
    "solicitacao_tratamento_cargo",
    "tr_cargo_assinante",
    "tr_termo_responsavel_cargo",
)


def strip_deprecated_cargo_override(override: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(override, dict):
        return override
    out = dict(override)
    for key in DEPRECATED_CARGO_OVERRIDE_KEYS:
        out.pop(key, None)
    return out or None
