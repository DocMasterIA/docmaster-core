from __future__ import annotations

"""
Descoberta de anexos (documentos) de uma contratação no PNCP.

IMPORTANTE: a estrutura exata dos anexos/documentos no payload do PNCP
depende do contrato da API de origem (que pode variar por versão).

Este módulo define:
- o tipo PNCPAttachment, que padroniza como tratamos anexos; e
- a função list_attachments_for_contract(ref), atualmente como esqueleto
  a ser preenchido assim que a estrutura de `ref.raw` com documentos
  estiver conhecida.
"""

from dataclasses import dataclass
from typing import List, Optional

from .pncp_types import PNCPContractRef
from .pncp_files_client import build_attachments_for_contract


@dataclass
class PNCPAttachment:
    """
    Representa um anexo (documento) associado a uma contratação PNCP.
    """

    numero_pncp: str
    tipo_documento_codigo: int
    tipo_documento_nome: str
    nome_arquivo: str
    url_download: Optional[str]

    # Mapeamento interno para o tipo lógico usado pelo RAG:
    # ex.: "termo_referencia", "etp", "dfd", "contrato", "outro".
    document_type_inferido: str


def _infer_document_type_from_codigo(tipo_codigo: int) -> str:
    """
    Mapeia o código de Tipo de Documento (manual PNCP, seção 5.12)
    para o document_type lógico usado no RAG.
    """
    mapping = {
        4: "termo_referencia",  # Termo de Referência
        7: "etp",               # Estudo Técnico Preliminar
        10: "dfd",              # DFD
        3: "contrato",          # Minuta do Contrato (pode ser tratada como contrato)
        12: "contrato",         # Contrato
    }
    return mapping.get(tipo_codigo, "outro")


async def list_attachments_for_contract(ref: PNCPContractRef) -> List[PNCPAttachment]:
    """
    Retorna a lista de anexos conhecidos para uma contratação PNCP.

    Neste primeiro momento, a função é um ESQUELETO:
    - Usa apenas informações que eventualmente já estejam presentes em `ref.raw`,
      se houver uma chave com documentos anexos.
    - Caso contrário, retorna lista vazia.

    Quando a estrutura exata dos anexos estiver clara (por exemplo, após
    analisar `ref.raw` de uma resposta real que contenha documentos),
    este método deve ser atualizado para:
        - ler a lista de documentos da contratação;
        - montar PNCPAttachment com url_download preenchida;
        - filtrar por tipo_documento_codigo (4=TR, 7=ETP, 10=DFD, etc.).
    """
    raw = ref.raw or {}

    attachments: List[PNCPAttachment] = []

    # Exemplo de estrutura hipotética:
    # raw.get("documentos") -> lista com dicts:
    #   {
    #       "tipoDocumentoCodigo": 4,
    #       "tipoDocumentoNome": "Termo de Referência",
    #       "nomeArquivo": "TR_objeto_XYZ.pdf",
    #       "url": "https://pncp.gov.br/.../download"
    #   }
    #
    # Enquanto a estrutura real não for conhecida, tratamos de forma segura:
    docs = raw.get("documentos") or raw.get("anexos") or []
    if isinstance(docs, list):
        for d in docs:
            try:
                tipo_codigo = int(d.get("tipoDocumentoCodigo"))
            except Exception:
                continue
            tipo_nome = str(d.get("tipoDocumentoNome") or "")
            nome_arquivo = str(d.get("nomeArquivo") or "")
            url = d.get("url") or d.get("urlDownload")

            document_type = _infer_document_type_from_codigo(tipo_codigo)

            attachments.append(
                PNCPAttachment(
                    numero_pncp=ref.numero_pncp,
                    tipo_documento_codigo=tipo_codigo,
                    tipo_documento_nome=tipo_nome,
                    nome_arquivo=nome_arquivo,
                    url_download=url,
                    document_type_inferido=document_type,
                )
            )

    # Se o payload bruto não trouxer anexos estruturados, usamos o cliente
    # de arquivos baseado em /v1/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos.
    if not attachments:
        try:
            attachments = await build_attachments_for_contract(ref)
        except Exception:
            # Em caso de erro na descoberta via API de arquivos, retornamos
            # o que já foi possível montar (vazio, na maioria dos casos).
            return []

    return attachments

