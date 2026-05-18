"""Contexto da requisição HTTP (prefeitura para métricas)."""
from __future__ import annotations

from contextvars import ContextVar

_prefeitura: ContextVar[str] = ContextVar("prefeitura", default="Não identificado")


def set_prefeitura(value: str | None) -> None:
    from app.metrics import normalize_prefeitura

    _prefeitura.set(normalize_prefeitura(value))


def get_prefeitura() -> str:
    return _prefeitura.get()
