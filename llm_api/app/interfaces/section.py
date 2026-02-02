"""
Interface padronizada para chamadas do tipo section.

Invoca o adapter com o payload adequado ao fluxo section.
Contrato de entrada/saída pode ser refinado conforme o servidor de IA.
"""
from __future__ import annotations

from typing import Any

from app.adapter import section


async def call_section(payload: dict[str, Any]) -> dict[str, Any] | str:
    """
    Chama o servidor de IA no modo section.

    payload: dict com os campos esperados pelo endpoint section
             (ex.: prompt, section_id, context). Definir conforme contrato.
    Retorna resposta bruta do servidor (dict ou str).
    """
    return await section(payload)
