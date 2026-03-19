from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from .config import RAG_HTTP_TIMEOUT
from .pncp_types import PNCPContractRef, infer_tema_objeto

logger = logging.getLogger(__name__)

# Base oficial da API de consultas do PNCP (${BASE_URL} no manual).
# Documentação: https://pncp.gov.br/api/consulta/swagger-ui/index.html
PNCP_BASE_URL = "https://pncp.gov.br/api/consulta"


class PNCPClientError(Exception):
    """Erro genérico na comunicação com o PNCP."""


async def search_contracts(
    data_inicial: str,
    data_final: str,
    codigo_modalidade: int,
    uf: Optional[str] = None,
    codigo_municipio_ibge: Optional[str] = None,
    pagina: int = 1,
    tamanho_pagina: int = 20,
) -> List[PNCPContractRef]:
    """
    Consulta contratações no PNCP usando o serviço oficial
    "Consultar Contratações por Data de Publicação" (seção 6.3 do manual).

    Endpoint: GET /v1/contratacoes/publicacao

    Parâmetros principais (query string):
    - dataInicial (AAAAMMDD) [obrigatório]
    - dataFinal   (AAAAMMDD) [obrigatório]
    - codigoModalidadeContratacao [obrigatório]
    - codigoModoDisputa, uf, codigoMunicipioIbge, cnpj, codigoUnidadeAdministrativa, idUsuario [opcionais]
    - pagina [obrigatório]
    - tamanhoPagina [opcional, padrão até 50/500]
    """
    if not data_inicial or not data_final:
        raise PNCPClientError("data_inicial e data_final são obrigatórios (formato AAAAMMDD).")

    endpoint = f"{PNCP_BASE_URL}/v1/contratacoes/publicacao"

    # Manual PNCP: tamanhoPagina mínimo 10, máximo 50.
    params: Dict[str, Any] = {
        "dataInicial": data_inicial,
        "dataFinal": data_final,
        "codigoModalidadeContratacao": codigo_modalidade,
        "pagina": max(1, pagina),
        # Manual impõe tamanho mínimo de página (>= 10) e máximo de 50
        "tamanhoPagina": max(10, min(tamanho_pagina, 50)),
    }
    if uf:
        params["uf"] = uf
    if codigo_municipio_ibge:
        params["codigoMunicipioIbge"] = codigo_municipio_ibge

    timeout = RAG_HTTP_TIMEOUT or 30.0

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(endpoint, params=params)
    except httpx.RequestError as e:
        logger.error("Erro de conexão com PNCP: %s", e)
        raise PNCPClientError(f"Não foi possível conectar ao PNCP ({endpoint}).") from e

    if resp.status_code == 204:
        # No Content: consulta válida, mas sem dados.
        return []

    if resp.status_code >= 500:
        logger.error("PNCP retornou erro 5xx: %s - %s", resp.status_code, resp.text[:500])
        raise PNCPClientError(f"PNCP retornou erro {resp.status_code}.")

    if resp.status_code == 400 or resp.status_code == 422:
        logger.error("Requisição inválida para PNCP (%s): %s", resp.status_code, resp.text[:500])
        raise PNCPClientError(f"Requisição inválida para PNCP: {resp.text[:200]}")

    try:
        data = resp.json()
    except ValueError as e:
        logger.error("Resposta PNCP não é JSON válido: %s", resp.text[:500])
        raise PNCPClientError("Resposta do PNCP não é JSON válido.") from e

    # Estrutura padrão de retorno (seção 4.2 do manual):
    # { data: [...], totalRegistros, totalPaginas, numeroPagina, paginasRestantes, empty }
    items: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        if isinstance(data.get("data"), list):
            items = data["data"]
    elif isinstance(data, list):
        items = data

    refs: List[PNCPContractRef] = []
    for raw in items:
        try:
            numero_pncp = str(raw.get("numeroControlePNCP") or "").strip()
            if not numero_pncp:
                continue

            orgao_entidade = raw.get("orgaoEntidade") or {}
            unidade_orgao = raw.get("unidadeOrgao") or {}

            objeto_resumido = raw.get("objetoCompra")
            tema = infer_tema_objeto(str(objeto_resumido or ""))

            ref = PNCPContractRef(
                numero_pncp=numero_pncp,
                id_licitacao=None,
                id_aviso=None,
                orgao=orgao_entidade.get("razaoSocial") or orgao_entidade.get("razaosocial"),
                unidade_compradora=unidade_orgao.get("nomeUnidade"),
                municipio=unidade_orgao.get("municipioNome"),
                uf=unidade_orgao.get("ufSigla"),
                cnpj_orgao=orgao_entidade.get("cnpj"),
                ano_compra=raw.get("anoCompra"),
                sequencial_compra=raw.get("sequencialCompra"),
                modalidade=raw.get("modalidadeNome"),
                objeto_resumido=objeto_resumido,
                valor_global=float(raw.get("valorTotalEstimado") or 0) or None,
                situacao=raw.get("situacaoCompraNome"),
                tema_objeto=tema,
                raw=raw,
            )
            refs.append(ref)
        except Exception as e:
            logger.warning("Falha ao converter item PNCP em PNCPContractRef: %s", e)
            continue

    return refs

