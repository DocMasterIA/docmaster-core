"""Sanitização de slots do DFD — evita vazamento de rótulos de formulário ou prompt de cláusulas."""

from __future__ import annotations

_INVALID_DFD_SETOR_MARKERS = (
    "qual setor/secretaria",
    "qual setor",
    "setor/secretaria atendido",
    "setor/secretaria será atendido",
    "setor requisitante (unidade",
)


def sanitize_dfd_setor_requisitante(value: str) -> str:
    """Remove valores que parecem rótulo de campo ou texto do prompt de cláusulas."""
    v = (value or "").strip()
    if not v:
        return ""
    low = v.lower()
    if any(marker in low for marker in _INVALID_DFD_SETOR_MARKERS):
        return ""
    return v
