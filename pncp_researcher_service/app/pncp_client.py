from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from .config import PNCP_BASE_URL, PNCP_TIMEOUT


class PNCPClientError(Exception):
    pass


async def search_contracts(
    data_inicial: str,
    data_final: str,
    codigo_modalidade: int,
    uf: Optional[str] = None,
    codigo_municipio_ibge: Optional[str] = None,
    pagina: int = 1,
    tamanho_pagina: int = 50,
) -> List[Dict[str, Any]]:
    endpoint = f"{PNCP_BASE_URL}/v1/contratacoes/publicacao"
    params: Dict[str, Any] = {
        "dataInicial": data_inicial,
        "dataFinal": data_final,
        "codigoModalidadeContratacao": codigo_modalidade,
        "pagina": max(1, int(pagina)),
        "tamanhoPagina": max(10, min(int(tamanho_pagina), 50)),
    }
    if uf:
        params["uf"] = uf
    if codigo_municipio_ibge:
        params["codigoMunicipioIbge"] = codigo_municipio_ibge

    try:
        async with httpx.AsyncClient(timeout=PNCP_TIMEOUT) as client:
            resp = await client.get(endpoint, params=params)
    except httpx.RequestError as e:
        raise PNCPClientError(f"Erro de conexão com PNCP: {e}") from e

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
