from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Optional


@dataclass
class PNCPContractRef:
    """
    Representa uma contratação/aviso retornado pelo PNCP em formato simplificado.

    Esta estrutura é pensada para consumo interno do DocMaster (RAG/LLM),
    não necessariamente espelha 1:1 o schema oficial da API PNCP.
    """

    # Identificadores principais
    numero_pncp: str  # número de controle PNCP, quando disponível
    id_licitacao: Optional[str] = None
    id_aviso: Optional[str] = None

    # Dados institucionais
    orgao: Optional[str] = None
    unidade_compradora: Optional[str] = None
    municipio: Optional[str] = None
    uf: Optional[str] = None

    # Informações da contratação
    modalidade: Optional[str] = None
    objeto_resumido: Optional[str] = None
    valor_global: Optional[float] = None
    data_publicacao: Optional[date] = None
    situacao: Optional[str] = None

    # Metadados auxiliares
    fonte: str = "pncp"
    raw: Optional[Dict[str, Any]] = None  # payload bruto da API, se for útil para debug


def pncp_contract_to_text(ref: PNCPContractRef) -> str:
    """
    Converte um PNCPContractRef em texto curto para ser injetado no prompt da LLM.

    Não é uma renderização final de cláusula; serve como "exemplo de contexto"
    de contratações semelhantes.
    """
    partes = []

    if ref.objeto_resumido:
        partes.append(f"Objeto: {ref.objeto_resumido}.")

    if ref.orgao or ref.unidade_compradora:
        orgao_txt = ref.unidade_compradora or ref.orgao
        partes.append(f"Órgão/Unidade: {orgao_txt}.")

    if ref.municipio or ref.uf:
        loc = ", ".join(p for p in [ref.municipio, ref.uf] if p)
        if loc:
            partes.append(f"Localidade: {loc}.")

    if ref.modalidade:
        partes.append(f"Modalidade: {ref.modalidade}.")

    if ref.valor_global is not None:
        partes.append(f"Valor global aproximado: R$ {ref.valor_global:,.2f}.")

    if ref.data_publicacao:
        partes.append(f"Data de publicação: {ref.data_publicacao.isoformat()}.")

    if ref.numero_pncp:
        partes.append(f"Número PNCP: {ref.numero_pncp}.")

    if ref.situacao:
        partes.append(f"Situação: {ref.situacao}.")

    return " ".join(partes)

