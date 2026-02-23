"""
Modelos de entrada e saída do serviço RAG.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class IngestRequest(BaseModel):
    """
    Entrada para ingestão de documento.

    Aceita texto ou referência a arquivo (implementação futura).
    """

    text: str = Field(..., description="Conteúdo textual a indexar.")
    metadata: Optional[dict] = Field(
        default=None,
        description="Metadados opcionais (document_type, source, etc.).",
    )
    collection: Optional[str] = Field(
        None,
        description="Nome da coleção; se omitido, usa a padrão.",
    )

    @field_validator("text")
    @classmethod
    def _text_not_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("text é obrigatório.")
        return v


class IngestResponse(BaseModel):
    """Resposta da ingestão."""

    ok: bool = Field(..., description="Indica sucesso.")
    message: str = Field(..., description="Mensagem descritiva.")
    chunks_added: Optional[int] = Field(
        None,
        description="Quantidade de chunks adicionados ao índice.",
    )
    collection: Optional[str] = Field(None, description="Coleção utilizada.")
    error: Optional[str] = Field(None, description="Erro, se houver.")


class RetrievedChunk(BaseModel):
    """Trecho recuperado da busca vetorial."""

    content: str = Field(..., description="Conteúdo do trecho.")
    score: Optional[float] = Field(None, description="Score de similaridade.")
    metadata: Optional[dict] = Field(None, description="Metadados associados.")


class QueryRequest(BaseModel):
    """
    Entrada para consulta RAG.
    """

    query: str = Field(..., description="Pergunta ou busca textual.")
    collection: Optional[str] = Field(
        None,
        description="Coleção a consultar; se omitido, usa a padrão.",
    )
    top_k: Optional[int] = Field(
        None,
        description="Quantidade de trechos a recuperar (override da config).",
    )
    include_sources: bool = Field(
        True,
        description="Incluir trechos recuperados na resposta.",
    )
    generate_answer: bool = Field(
        True,
        description="Gerar resposta via LLM a partir do contexto recuperado.",
    )

    @field_validator("query")
    @classmethod
    def _query_not_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("query é obrigatório.")
        return v


class QueryResponse(BaseModel):
    """Resposta da consulta RAG."""

    ok: bool = Field(..., description="Indica sucesso.")
    answer: Optional[str] = Field(
        None,
        description="Resposta gerada pelo LLM (quando generate_answer=True).",
    )
    sources: Optional[List[RetrievedChunk]] = Field(
        None,
        description="Trechos recuperados (quando include_sources=True).",
    )
    error: Optional[str] = Field(None, description="Erro, se houver.")


class CollectionsResponse(BaseModel):
    """Lista de coleções disponíveis."""

    ok: bool = Field(..., description="Indica sucesso.")
    collections: List[str] = Field(
        default_factory=list,
        description="Nomes das coleções.",
    )
    error: Optional[str] = Field(None, description="Erro, se houver.")


class HealthResponse(BaseModel):
    """Resposta do health check."""

    ok: bool = Field(..., description="Serviço em operação.")
    chroma_connected: Optional[bool] = Field(
        None,
        description="Conexão com ChromaDB.",
    )
    message: Optional[str] = Field(None, description="Mensagem adicional.")


class CheckComplianceRequest(BaseModel):
    """Request para verificação de conformidade com a Lei 14.133."""

    text: str = Field(..., description="Texto gerado a validar (cláusula ou documento).")
    collection: Optional[str] = Field(None, description="Coleção a consultar.")
    top_k: int = Field(5, description="Quantidade de trechos da lei a recuperar.")

    @field_validator("text")
    @classmethod
    def _text_not_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("text é obrigatório.")
        return v


class CheckComplianceResponse(BaseModel):
    """Resposta da verificação de conformidade."""

    ok: bool = Field(..., description="Indica sucesso da operação.")
    compliant: Optional[bool] = Field(
        None,
        description="True=em conformidade, False=não, None=indeterminado ou lei não indexada.",
    )
    observations: str = Field(
        "",
        description="Observação do LLM (resposta SIM/NÃO + breve justificativa).",
    )
    relevant_articles: Optional[List[dict]] = Field(
        None,
        description="Trechos da lei recuperados como referência.",
    )
    error: Optional[str] = Field(None, description="Erro, se houver.")


class AnalyzeDocumentResponse(BaseModel):
    """Resposta da análise de documento contra Lei 14.133."""

    ok: bool = Field(..., description="Indica sucesso.")
    document_type: str = Field("outro", description="etp, dfd, termo_referencia, contrato, outro")
    sections_detected: List[str] = Field(default_factory=list, description="Seções identificadas")
    pontos_importantes: List[str] = Field(default_factory=list, description="Pontos principais do doc")
    acertos: List[str] = Field(default_factory=list, description="O que está correto conforme a lei (apenas itens claros, sem dúvida)")
    ressalvas: List[str] = Field(default_factory=list, description="Itens ambíguos ou positivos com dúvida/ressalva")
    erros: List[str] = Field(default_factory=list, description="O que está incorreto ou viola a lei (incl. erros formais)")
    riscos_juridicos: List[str] = Field(default_factory=list, description="Riscos de impugnação ou vício jurídico")
    sugestoes_reescrita: List[str] = Field(default_factory=list, description="Sugestões de reescrita ou complementação")
    conformidade_geral: Optional[bool] = Field(None, description="True=conforme, False=não")
    observacoes: str = Field("", description="Comentário breve")
    resumo_executivo: str = Field("", description="Parágrafo único de resumo executivo da análise")
    error: Optional[str] = Field(None, description="Erro, se houver")
