from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import httpx

from .config import PNCP_BASE_URL
from .pncp_types import PNCPContractRef
from .pncp_attachments import PNCPAttachment


@dataclass
class PNCPFileMeta:
    """
    Metadados simples de um arquivo retornado pelo endpoint de arquivos do PNCP.
    """

    id_arquivo: int
    nome_arquivo: Optional[str]
    conteudo_tipo: Optional[str]


def _build_arquivos_base_url(ref: PNCPContractRef) -> Optional[str]:
    """
    Monta a URL base para arquivos de uma compra PNCP, a partir dos campos
    técnicos disponíveis no PNCPContractRef (ou em ref.raw como fallback).
    """
    cnpj = ref.cnpj_orgao
    ano = ref.ano_compra
    seq = ref.sequencial_compra

    raw = ref.raw or {}
    if not cnpj:
        orgao = raw.get("orgaoEntidade") or {}
        cnpj = orgao.get("cnpj")
    if ano is None:
        ano = raw.get("anoCompra")
    if seq is None:
        seq = raw.get("sequencialCompra")

    if not (cnpj and ano and seq):
        return None

    return f"{PNCP_BASE_URL}/v1/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos"


async def list_arquivos_for_contract(ref: PNCPContractRef) -> List[PNCPFileMeta]:
    """
    Lista arquivos conhecidos para uma contratação PNCP, usando o endpoint
    de arquivos quando disponível.

    Retorna apenas metadados mínimos (id, nome, content-type).
    """
    base = _build_arquivos_base_url(ref)
    if not base:
        return []

    url = base
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except Exception:
            # Se o endpoint de listagem não existir ou falhar, retornamos vazio;
            # o chamador pode optar por uma estratégia de sondagem (arquivos/1, 2, 3...).
            return []

    data = resp.json()
    # A estrutura exata ainda não é 100% conhecida; assumimos alguns campos comuns.
    items = data if isinstance(data, list) else data.get("data") or []

    resultados: List[PNCPFileMeta] = []
    for item in items:
        try:
            file_id = int(item.get("id") or item.get("sequencial") or item.get("numero") or 0)
        except Exception:
            continue
        if not file_id:
            continue

        nome = item.get("nomeArquivo") or item.get("nome") or None
        content_type = item.get("contentType") or item.get("tipoMime") or None

        resultados.append(
            PNCPFileMeta(
                id_arquivo=file_id,
                nome_arquivo=nome,
                conteudo_tipo=content_type,
            )
        )

    return resultados


async def build_attachments_for_contract(ref: PNCPContractRef) -> List[PNCPAttachment]:
    """
    Constrói uma lista de PNCPAttachment com base nos metadados retornados por
    list_arquivos_for_contract. Neste momento, o tipo lógico do documento é
    marcado como \"outro\" por padrão, podendo ser refinado futuramente quando
    houver metadados mais ricos.
    """
    base = _build_arquivos_base_url(ref)
    if not base:
        return []

    arquivos = await list_arquivos_for_contract(ref)
    attachments: List[PNCPAttachment] = []
    for arquivo in arquivos:
        url_download = f"{base}/{arquivo.id_arquivo}"

        attachments.append(
            PNCPAttachment(
                numero_pncp=ref.numero_pncp,
                tipo_documento_codigo=0,
                tipo_documento_nome="Desconhecido",
                nome_arquivo=arquivo.nome_arquivo or f"arquivo_{arquivo.id_arquivo}",
                url_download=url_download,
                document_type_inferido="outro",
            )
        )

    return attachments

