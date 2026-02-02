"""
Interface padronizada para chamadas do tipo planner.

Invoca o adapter com o payload adequado ao fluxo planner.
Contrato de entrada/saída pode ser refinado conforme o servidor de IA.
"""
from __future__ import annotations

from typing import Any

from app.adapter import planner


async def call_planner(payload: dict[str, Any]) -> dict[str, Any] | str:
    """
    Chama o servidor de IA no modo planner.

    payload: dict com os campos esperados pelo endpoint planner
             (ex.: prompt, context, options). Definir conforme contrato.
    Retorna resposta bruta do servidor (dict ou str).
    """
    return await planner(payload)
