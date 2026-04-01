from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import httpx

from .config import PNCP_BASE_URL, PNCP_TIMEOUT, PNCP_MAX_RETRIES, PNCP_RETRY_BACKOFF_SECONDS


class PNCPClientError(Exception):
    pass


async def search_contracts(
    data_inicial: str,
    data_final: str,
    codigo_modalidade: Optional[int] = None,
    uf: Optional[str] = None,
    codigo_municipio_ibge: Optional[str] = None,
    pagina: int = 1,
    tamanho_pagina: int = 50,
) -> List[Dict[str, Any]]:
    endpoint = f"{PNCP_BASE_URL}/v1/contratacoes/publicacao"
    params: Dict[str, Any] = {
        "dataInicial": data_inicial,
        "dataFinal": data_final,
        "pagina": max(1, int(pagina)),
        "tamanhoPagina": max(10, min(int(tamanho_pagina), 50)),
    }
    if codigo_modalidade is not None:
        params["codigoModalidadeContratacao"] = int(codigo_modalidade)
    if uf:
        params["uf"] = uf
    if codigo_municipio_ibge:
        params["codigoMunicipioIbge"] = codigo_municipio_ibge

    # Retry com backoff para reduzir falhas transitórias/timeout.
    last_request_error: Optional[Exception] = None
    resp: Optional[httpx.Response] = None
    for attempt in range(max(1, PNCP_MAX_RETRIES)):
        try:
            async with httpx.AsyncClient(timeout=PNCP_TIMEOUT) as client:
                resp = await client.get(endpoint, params=params)
            break
        except httpx.RequestError as e:
            last_request_error = e
            if attempt < max(1, PNCP_MAX_RETRIES) - 1:
                wait_s = PNCP_RETRY_BACKOFF_SECONDS * (2 ** attempt)
                await asyncio.sleep(wait_s)
                continue
            # Não derruba o fluxo por timeout/conexão: trata como página vazia.
            return []

    if resp is None:
        if last_request_error is not None:
            raise PNCPClientError(f"Falha inesperada sem resposta do PNCP: {type(last_request_error).__name__}")
        raise PNCPClientError("Falha inesperada sem resposta do PNCP.")

    if resp.status_code == 204:
        return []
    if resp.status_code >= 400:
        raise PNCPClientError(f"PNCP retornou {resp.status_code}: {resp.text[:300]}")

    try:
        data = resp.json()
    except ValueError as e:
        raise PNCPClientError("PNCP retornou JSON inválido.") from e

    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return data["data"]
    if isinstance(data, list):
        return data
    return []
