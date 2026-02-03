"""
Interface padronizada para chamadas de análise de documento (ex.: análise de editais).

Invoca o adapter com o payload adequado ao fluxo de avaliação.
Contrato de entrada/saída pode ser refinado conforme o servidor de IA.
"""
from __future__ import annotations

from typing import Any

from app.adapter import analysis as analysis_adapter


async def call_analysis(payload: dict[str, Any]) -> dict[str, Any] | str:
    """
    Chama o servidor de IA no modo análise (avaliação de documento).

    Não gera nem modifica documento; retorna avaliação (parecer, riscos,
    conformidade, etc.). Payload típico: document (texto), context, options.
    """
    return await analysis_adapter(payload)
