from __future__ import annotations

"""
Download de anexos PNCP para armazenamento local.

Recebe PNCPAttachment (com url_download) e salva os arquivos em uma pasta base,
organizando por número de contratação PNCP.
"""

import logging
from pathlib import Path
from typing import Iterable, List

import httpx

from .pncp_attachments import PNCPAttachment

logger = logging.getLogger(__name__)


async def download_attachments(
    attachments: Iterable[PNCPAttachment],
    base_dir: Path,
) -> List[Path]:
    """
    Faz download dos anexos informados e salva em disco.

    Args:
        attachments: iterável de PNCPAttachment (idealmente já filtrados por tipo).
        base_dir: diretório base onde os arquivos serão gravados (ex.: data/pncp).

    Returns:
        Lista de caminhos de arquivos baixados com sucesso.
    """
    base_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: List[Path] = []

    async with httpx.AsyncClient() as client:
        for att in attachments:
            if not att.url_download:
                logger.info(
                    "PNCP download ignorado (sem URL): numero_pncp=%s tipo=%s nome=%s",
                    att.numero_pncp,
                    att.tipo_documento_codigo,
                    att.nome_arquivo,
                )
                continue

            try:
                resp = await client.get(att.url_download)
                resp.raise_for_status()
            except httpx.RequestError as e:
                logger.warning(
                    "Falha ao baixar anexo PNCP (conexão): numero_pncp=%s url=%s erro=%s",
                    att.numero_pncp,
                    att.url_download,
                    e,
                )
                continue
            except httpx.HTTPStatusError as e:
                logger.warning(
                    "Falha ao baixar anexo PNCP (status %s): numero_pncp=%s url=%s",
                    e.response.status_code,
                    att.numero_pncp,
                    att.url_download,
                )
                continue

            contrato_dir = base_dir / att.numero_pncp
            contrato_dir.mkdir(parents=True, exist_ok=True)

            # Monta nome de arquivo seguro
            safe_name = att.nome_arquivo or f"doc_{att.tipo_documento_codigo}"
            out_path = contrato_dir / safe_name

            try:
                out_path.write_bytes(resp.content)
                saved_paths.append(out_path)
                logger.info(
                    "Anexo PNCP baixado: numero_pncp=%s tipo=%s arquivo=%s",
                    att.numero_pncp,
                    att.tipo_documento_codigo,
                    out_path,
                )
            except Exception as e:
                logger.warning(
                    "Falha ao salvar anexo PNCP em disco: numero_pncp=%s arquivo=%s erro=%s",
                    att.numero_pncp,
                    out_path,
                    e,
                )

    return saved_paths

