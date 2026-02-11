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
