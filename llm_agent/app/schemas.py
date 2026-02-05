"""
Modelos de entrada e saída do agente de estrutura documental.

Saída SEMPRE estrutural (JSON), sem texto jurídico final.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ContextoBasico(BaseModel):
    """Contexto mínimo exigido para gerar a estrutura do documento."""

    objeto: str = Field(..., description="Objeto da contratação ou finalidade principal.")
    orgao: Optional[str] = Field(
        None,
        description="Órgão demandante / secretaria / entidade responsável.",
    )
    modalidade: Optional[str] = Field(
        None,
        description="Modalidade (ex.: pregão eletrônico, dispensa, concorrência).",
    )
    # Campo livre para informações adicionais (mapa chave-valor).
    extras: Optional[dict] = Field(
        default=None,
        description="Outros parâmetros relevantes (mapa livre).",
    )

    @field_validator("objeto", "orgao", "modalidade", mode="before")
    @classmethod
    def _strip_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if isinstance(v, str):
            return v.strip()
        return v


class DocumentoTipo(str):
    """
    Tipos suportados de documento.

    As chaves técnicas são em snake_case; os valores de negócio são:
    - TERMO_DE_REFERENCIA
    - ESTUDO_TECNICO_PRELIMINAR
    - DOCUMENTO_FORMALIZACAO_DEMANDA
    """

    TERMO_DE_REFERENCIA = "termo_referencia"
    ESTUDO_TECNICO_PRELIMINAR = "estudo_tecnico_preliminar"
    DOCUMENTO_FORMALIZACAO_DEMANDA = "documento_formalizacao_demanda"
    # Outros tipos podem ser usados livremente (string arbitrária).


class PromptStructureRequest(BaseModel):
    """
    Entrada para o endpoint que interpreta prompt livre do usuário.

    O agente interpreta o texto e extrai document_type + context para
    então gerar a estrutura via generate_structure.
    """

    user_prompt: str = Field(
        ...,
        description="Texto livre descrevendo o documento desejado (ex.: tipo, objeto, órgão, modalidade).",
    )

    @field_validator("user_prompt")
    @classmethod
    def _user_prompt_not_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("user_prompt é obrigatório.")
        return v


class StructureRequest(BaseModel):
    """
    Entrada principal do agente.

    - document_type: string identificando o tipo de documento (chave técnica).
    - context: informações mínimas (objeto, órgão, modalidade etc.).
    """

    document_type: str = Field(
        ...,
        description=(
            "Tipo técnico do documento "
            "(ex.: termo_referencia, estudo_tecnico_preliminar, documento_formalizacao_demanda)."
        ),
    )
    context: ContextoBasico

    @field_validator("document_type")
    @classmethod
    def _document_type_not_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("document_type é obrigatório.")
        return v


class TableColumn(BaseModel):
    """Coluna de uma seção tabular."""

    key: str = Field(..., description="Identificador técnico da coluna (snake_case).")
    label: str = Field(..., description="Rótulo exibido na tabela.")

    @field_validator("key", "label")
    @classmethod
    def _not_blank_col(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Campo não pode ser vazio.")
        return v


class TableSchema(BaseModel):
    """Schema de tabela: apenas definição de colunas (sem dados)."""

    columns: List[TableColumn] = Field(
        ..., description="Lista de colunas da tabela (sem linhas/dados)."
    )

    @field_validator("columns")
    @classmethod
    def _at_least_one_column(cls, v: List[TableColumn]) -> List[TableColumn]:
        if not v:
            raise ValueError("Pelo menos uma coluna é obrigatória em uma tabela.")
        return v


class SectionNode(BaseModel):
    """
    Nó de estrutura: seção ou subseção.

    - key: identificador técnico (estável) da seção.
    - title: título formal exibido no documento.
    - required: se a seção é obrigatória.
    - content_type: tipo de conteúdo (texto, tabela ou lista).
    - table_schema: schema da tabela quando content_type == 'table'.
    - children: lista de subseções (mesmo formato).
    """

    key: str = Field(..., description="Identificador técnico único da seção (ex.: 'objeto', 'fundamentacao_legal').")
    title: str = Field(..., description="Título formal da seção.")
    required: bool = Field(..., description="Indica se a seção é obrigatória.")
    content_type: Literal["text", "table", "list"] = Field(
        ..., description="Tipo de conteúdo da seção: 'text', 'table' ou 'list'."
    )
    table_schema: Optional[TableSchema] = Field(
        default=None,
        description="Schema da tabela quando content_type == 'table'. Não deve ser usado para outros tipos.",
    )
    children: List["SectionNode"] = Field(
        default_factory=list,
        description="Subseções desta seção (estrutura recursiva).",
    )

    @field_validator("key", "title")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Campo não pode ser vazio.")
        return v

    @model_validator(mode="after")
    def _validate_table_schema(self) -> "SectionNode":
        ctype = self.content_type
        schema = self.table_schema
        if ctype == "table" and schema is None:
            raise ValueError("Se content_type == 'table', table_schema é obrigatório.")
        if ctype != "table" and schema is not None:
            raise ValueError("table_schema só deve ser informado quando content_type == 'table'.")
        return self


SectionNode.model_rebuild()


class DocumentStructure(BaseModel):
    """
    Estrutura completa do documento.

    - document_type: ecoa o tipo solicitado.
    - root_sections: lista de seções de topo.
    """

    document_type: str
    root_sections: List[SectionNode]

    @field_validator("root_sections")
    @classmethod
    def _at_least_one_section(cls, v: List[SectionNode]) -> List[SectionNode]:
        if not v:
            raise ValueError("Pelo menos uma seção raiz é obrigatória.")
        return v


class StructureResponse(BaseModel):
    """
    Resposta envelopada usada pelo endpoint interno.
    """

    ok: bool
    structure: Optional[DocumentStructure] = None
    error: Optional[str] = None
    retries: int = 0

