from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import httpx

from .pncp_types import PNCPContractRef


# Base específica para download de arquivos no PNCP (não é a mesma da API de consulta).
PNCP_FILES_BASE_URL = "https://pncp.gov.br/pncp-api"


@dataclass
class PNCPFileMeta:
    """
    Metadados simples de um arquivo associado a uma contratação PNCP,
    baseados na resposta JSON de /v1/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos.
    """

    id_arquivo: int
    url: str
    titulo: Optional[str]
    tipo_documento_id: Optional[int]
    tipo_documento_nome: Optional[str]


def _build_arquivos_base_url(ref: PNCPContractRef) -> Optional[str]:
    """
    Monta a URL base para uma compra PNCP na API de arquivos,
    a partir dos campos técnicos disponíveis no PNCPContractRef
    (ou em ref.raw como fallback).

    Exemplo:
        https://pncp.gov.br/pncp-api/v1/orgaos/{cnpj}/compras/{ano}/{seq}
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

    return f"{PNCP_FILES_BASE_URL}/v1/orgaos/{cnpj}/compras/{ano}/{seq}"


async def list_arquivos_for_contract(ref: PNCPContractRef, max_ids: int = 10) -> List[PNCPFileMeta]:
    """
    Consulta a lista de arquivos de uma contratação PNCP.

    Endpoint observado (resposta de exemplo fornecida pelo usuário):
        GET /v1/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos

    que retorna um array JSON com itens contendo, entre outros:
        - url / uri
        - sequencialDocumento
        - titulo
        - tipoDocumentoId / tipoDocumentoNome
    """
    base = _build_arquivos_base_url(ref)
    if not base:
        return []

    resultados: List[PNCPFileMeta] = []

    async with httpx.AsyncClient() as client:
        url = f"{base}/arquivos"
        try:
            resp = await client.get(url)
        except httpx.RequestError:
            return []

    if not resp.is_success:
        return []

    try:
        data = resp.json()
    except ValueError:
        return []

    if not isinstance(data, list):
        return []

    for item in data:
        try:
            file_id = int(item.get("sequencialDocumento") or 0)
        except Exception:
            file_id = 0
        if not file_id:
            # fallback: extrair do final da URL, se existir
            try:
                url_item = str(item.get("url") or item.get("uri") or "")
                file_id = int(url_item.rstrip("/").split("/")[-1])
            except Exception:
                file_id = 0
        if not file_id:
            continue

        url_item = str(item.get("url") or item.get("uri") or "").strip()
        if not url_item:
            # constrói a partir da base, se necessário
            url_item = f"{base}/arquivos/{file_id}"

        titulo = item.get("titulo") or None
        try:
            tipo_id = int(item.get("tipoDocumentoId")) if item.get("tipoDocumentoId") is not None else None
        except Exception:
            tipo_id = None
        tipo_nome = item.get("tipoDocumentoNome") or None

        resultados.append(
            PNCPFileMeta(
                id_arquivo=file_id,
                url=url_item,
                titulo=titulo,
                tipo_documento_id=tipo_id,
                tipo_documento_nome=tipo_nome,
            )
        )

    return resultados

