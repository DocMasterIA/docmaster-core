from __future__ import annotations

"""
Esqueleto do pipeline de ingestão de contratações PNCP no RAG.

Este módulo, por enquanto, foca em:
- descobrir contratações de interesse via API (pncp_discovery),
- inspecionar e registrar os candidatos para scraping/ingestão futura.

Etapas de download de anexos, extração de texto e ingestão em chunks
serão implementadas progressivamente.
"""

import logging
from typing import List, Optional

from .pncp_discovery import list_contracts_periodo
from .pncp_types import PNCPContractRef, pncp_contract_to_text

logger = logging.getLogger(__name__)


async def inspect_contracts_periodo(
    data_inicial: str,
    data_final: str,
    codigo_modalidade: int,
    uf: Optional[str] = None,
    codigo_municipio_ibge: Optional[str] = None,
    limite: int = 50,
) -> List[PNCPContractRef]:
    """
    Descobre contratações no PNCP em um período e registra um resumo em log.

    Útil para testar/ajustar filtros antes de partir para scraping pesado.
    """
    refs = await list_contracts_periodo(
        data_inicial=data_inicial,
        data_final=data_final,
        codigo_modalidade=codigo_modalidade,
        uf=uf,
        codigo_municipio_ibge=codigo_municipio_ibge,
        limite=limite,
    )

    logger.info(
        "PNCP inspect: encontrados %s registros para periodo %s-%s, modalidade=%s, uf=%s, municipio_ibge=%s",
        len(refs),
        data_inicial,
        data_final,
        codigo_modalidade,
        uf,
        codigo_municipio_ibge,
    )

    for idx, ref in enumerate(refs, start=1):
        resumo = pncp_contract_to_text(ref)
        logger.info(
            "PNCP [%s/%s] tema=%s numero_pncp=%s resumo=%s",
            idx,
            len(refs),
            ref.tema_objeto or "desconhecido",
            ref.numero_pncp,
            resumo,
        )

    return refs


async def ingest_contracts_periodo(
    data_inicial: str,
    data_final: str,
    codigo_modalidade: int,
    uf: Optional[str] = None,
    codigo_municipio_ibge: Optional[str] = None,
    limite: int = 50,
) -> None:
    """
    Ponto de entrada futuro para ingestão em massa.

    Por enquanto, apenas descobre e registra as contratações do período.
    Em etapas futuras, este método deverá:
        - baixar anexos relevantes (TR, ETP, DFD, etc.),
        - extrair texto,
        - criar chunks com metadados refinados (incluindo tema_objeto),
        - chamar ingest_text(...) para gravar no Chroma.
    """
    await inspect_contracts_periodo(
        data_inicial=data_inicial,
        data_final=data_final,
        codigo_modalidade=codigo_modalidade,
        uf=uf,
        codigo_municipio_ibge=codigo_municipio_ibge,
        limite=limite,
    )

