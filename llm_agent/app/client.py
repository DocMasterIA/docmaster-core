"""
Cliente HTTP interno do llm_agent para falar com o módulo de
orquestração LLM (llm_api).

Aqui NÃO falamos direto com o Ollama; usamos o endpoint /api/llm/generate
exposto pelo módulo de orquestração, que já cuida de timeouts, retries e
tratamento de erros de baixo nível.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Tuple

import httpx

from .config import (
    AGENT_TIMEOUT,
    LLM_ORCHESTRATION_BASE_URL,
    LLM_ORCHESTRATION_GENERATE_PATH,
)


class OrchestrationError(Exception):
    """Erro ao chamar o módulo de orquestração LLM."""


async def call_generate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chama o endpoint /api/llm/generate do módulo de orquestração.

    Espera que esse endpoint devolva um JSON com a chave \"data\" contendo
    a resposta do modelo (protocolo definido em llm_api).
    """
    url = f"{LLM_ORCHESTRATION_BASE_URL}{LLM_ORCHESTRATION_GENERATE_PATH}"

    async with httpx.AsyncClient(timeout=AGENT_TIMEOUT) as client:
        try:
            resp = await client.post(url, json=payload)
        except httpx.RequestError as e:
            msg = str(e).strip() or e.__class__.__name__
            raise OrchestrationError(
                f"Falha ao chamar módulo de orquestração ({url}): {msg}. "
                "Verifique se o serviço llm_api está rodando e acessível."
            ) from e

    if resp.status_code != 200:
        raise OrchestrationError(
            f"Orquestração retornou status {resp.status_code}: {resp.text}"
        )

    try:
        body = resp.json()
    except json.JSONDecodeError as e:
        raise OrchestrationError(f"Resposta inválida do módulo de orquestração: {e}") from e

    if not isinstance(body, dict) or "data" not in body:
        raise OrchestrationError("Resposta do módulo de orquestração não contém chave 'data'.")

    data = body["data"]
    if not isinstance(data, dict):
        raise OrchestrationError("Campo 'data' da resposta da orquestração deve ser um objeto JSON.")

    return data

