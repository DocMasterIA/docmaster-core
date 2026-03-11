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
from pathlib import Path
from typing import List, Optional, Sequence

from .pncp_discovery import list_contracts_periodo
from .pncp_types import PNCPContractRef, pncp_contract_to_text
from .pncp_attachments import PNCPAttachment, list_attachments_for_contract
from .pncp_downloader import download_attachments
from .pncp_text_extractor import extract_text_from_attachment

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
    base_dir: Optional[Path] = None,
    tipos_alvo: Optional[Sequence[str]] = None,
) -> None:
    """
    Ponto de entrada futuro para ingestão em massa.

    Implementa uma primeira etapa de ingestão:
        - descobre contratações no período;
        - descobre anexos PNCP para cada contratação;
        - filtra anexos por tipo lógico (TR, ETP, DFD, contrato);
        - baixa anexos filtrados para disco;
        - extrai texto de cada anexo baixado;
        - (ponto de extensão futuro) enviar texto + metadados para criação de chunks.
    """
    # Descobre e registra contratações (log de diagnóstico).
    refs = await inspect_contracts_periodo(
        data_inicial=data_inicial,
        data_final=data_final,
        codigo_modalidade=codigo_modalidade,
        uf=uf,
        codigo_municipio_ibge=codigo_municipio_ibge,
        limite=limite,
    )

    if base_dir is None:
        base_dir = Path("data/pncp")

    if tipos_alvo is None:
        tipos_alvo = ("termo_referencia", "etp", "dfd", "contrato")

    for idx, ref in enumerate(refs, start=1):
        logger.info(
            "PNCP ingest: [%s/%s] numero_pncp=%s tema=%s",
            idx,
            len(refs),
            ref.numero_pncp,
            ref.tema_objeto or "desconhecido",
        )

        try:
            anexos = await list_attachments_for_contract(ref)
        except Exception as e:
            logger.warning(
                "PNCP ingest: falha ao listar anexos para numero_pncp=%s erro=%s",
                ref.numero_pncp,
                e,
            )
            continue

        if not anexos:
            logger.info(
                "PNCP ingest: nenhum anexo encontrado para numero_pncp=%s",
                ref.numero_pncp,
            )
            continue

        anexos_filtrados: List[PNCPAttachment] = [
            a for a in anexos if a.document_type_inferido in tipos_alvo
        ]

        if not anexos_filtrados:
            logger.info(
                "PNCP ingest: nenhum anexo relevante (tipos=%s) para numero_pncp=%s",
                tipos_alvo,
                ref.numero_pncp,
            )
            continue

        logger.info(
            "PNCP ingest: %s anexos relevantes para numero_pncp=%s",
            len(anexos_filtrados),
            ref.numero_pncp,
        )

        saved_paths = await download_attachments(anexos_filtrados, base_dir=base_dir)

        for path in saved_paths:
            try:
                texto = extract_text_from_attachment(path)
            except Exception as e:
                logger.warning(
                    "PNCP ingest: falha ao extrair texto de %s (numero_pncp=%s) erro=%s",
                    path,
                    ref.numero_pncp,
                    e,
                )
                continue

            logger.info(
                "PNCP ingest: texto extraído de %s (numero_pncp=%s, tamanho=%s caracteres)",
                path,
                ref.numero_pncp,
                len(texto),
            )

            # Ponto de extensão: enviar (texto, metadados) para criação de chunks
            # e gravação no repositório vetorial (Chroma, etc.).

