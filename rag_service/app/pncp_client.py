from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from .config import RAG_HTTP_TIMEOUT
from .pncp_types import PNCPContractRef

logger = logging.getLogger(__name__)

# Base oficial da API de consultas do PNCP.
# A documentação pública fica em: https://pncp.gov.br/api/consulta/swagger-ui/index.html
PNCP_BASE_URL = "https://pncp.gov.br/api/consulta"


class PNCPClientError(Exception):
    """Erro genérico na comunicação com o PNCP."""


async def search_contracts(
    query: str,
    municipio: Optional[str] = None,
    uf: Optional[str] = None,
    modalidade: Optional[str] = None,
    limit: int = 20,
) -> List[PNCPContractRef]:
    """
    Busca contratações similares no PNCP a partir de uma consulta textual.

    NOTA IMPORTANTE:
    ----------------
    A API oficial do PNCP possui diversos endpoints (avisos, licitações, contratos, etc.).
    Aqui implementamos uma chamada genérica a um endpoint de pesquisa textual.

    Dependendo da versão da API, o endpoint e os parâmetros exatos podem variar.
    Esta função foi escrita para ser facilmente ajustada assim que você definir,
    com base no manual oficial, qual endpoint e filtros quer utilizar.
    """
    if not query or not query.strip():
        return []

    # Endpoint e parâmetros precisam ser ajustados quando você escolher o serviço exato
    # (ex.: /v1/avisos, /v1/contratos, etc.). Vamos começar com um stub de exemplo.
    endpoint = f"{PNCP_BASE_URL}/v1/avisos"

    params: Dict[str, Any] = {
        "pagina": 1,
        "tamanhoPagina": max(1, min(limit, 50)),
        "termo": query[:200],
    }
    if municipio:
        params["nomeMunicipio"] = municipio
    if uf:
        params["siglaUf"] = uf
    if modalidade:
        params["modalidade"] = modalidade

    timeout = RAG_HTTP_TIMEOUT or 30.0

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(endpoint, params=params)
    except httpx.RequestError as e:
        logger.error("Erro de conexão com PNCP: %s", e)
        raise PNCPClientError(f"Não foi possível conectar ao PNCP ({endpoint}).") from e

    if resp.status_code >= 500:
        logger.error("PNCP retornou erro 5xx: %s - %s", resp.status_code, resp.text[:500])
        raise PNCPClientError(f"PNCP retornou erro {resp.status_code}.")

    if resp.status_code == 404:
        # Nenhum resultado encontrado para a combinação de filtros.
        return []

    try:
        data = resp.json()
    except ValueError as e:
        logger.error("Resposta PNCP não é JSON válido: %s", resp.text[:500])
        raise PNCPClientError("Resposta do PNCP não é JSON válido.") from e

    items: List[Dict[str, Any]] = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        # Muitas APIs de consulta retornam estrutura paginada; adaptamos aqui.
        # Ajuste 'conteudo' / 'items' / 'data' conforme o schema real da API PNCP.
        if isinstance(data.get("conteudo"), list):
            items = data["conteudo"]
        elif isinstance(data.get("items"), list):
            items = data["items"]

    refs: List[PNCPContractRef] = []
    for raw in items[:limit]:
        try:
            numero_pncp = str(
                raw.get("numeroControlePNCP")
                or raw.get("numeroControlePncp")
                or raw.get("numeroControle")
                or ""
            ).strip()
            if not numero_pncp:
                # Sem identificador PNCP, mantém apenas se você considerar útil
                continue

            ref = PNCPContractRef(
                numero_pncp=numero_pncp,
                id_licitacao=str(raw.get("idLicitacao") or "") or None,
                id_aviso=str(raw.get("idAviso") or "") or None,
                orgao=raw.get("nomeOrgao"),
                unidade_compradora=raw.get("unidadeCompradora"),
                municipio=raw.get("nomeMunicipio"),
                uf=raw.get("siglaUf"),
                modalidade=raw.get("modalidade"),
                objeto_resumido=raw.get("objeto"),
                # Valor e datas dependem do schema; incluímos como placeholders.
                valor_global=float(raw.get("valorEstimado", 0) or 0) or None,
                situacao=raw.get("situacao"),
                raw=raw,
            )
            refs.append(ref)
        except Exception as e:
            logger.warning("Falha ao converter item PNCP em PNCPContractRef: %s", e)
            continue

    return refs

