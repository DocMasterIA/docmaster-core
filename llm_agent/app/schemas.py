"""
Modelos de entrada e saída do agente de estrutura documental.

Saída SEMPRE estrutural (JSON), sem texto jurídico final.

Inclui o modelo de seções versionáveis: definições técnicas controladas que
o agente apenas seleciona/organiza/omite, nunca inventa.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

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


# ---- Seções versionáveis (catálogo controlado, sem invenção pelo modelo) ----

class ApplicabilityScope(BaseModel):
    """
    Escopo de aplicabilidade da seção (município, estado, órgão, tipo de administração).

    Quando preenchido, a seção só é elegível se o contexto indicar explicitamente
    que aquele escopo se aplica. Evita generalizações indevidas.
    """

    municipio: Optional[str] = Field(None, description="Sigla ou nome do município.")
    estado: Optional[str] = Field(None, description="UF ou nome do estado.")
    orgao: Optional[str] = Field(None, description="Órgão ou entidade específica.")
    tipo_administracao: Optional[str] = Field(
        None,
        description="Tipo de administração (ex.: direta, indireta, autárquica).",
    )


class ConditionalRule(BaseModel):
    """
    Regra condicional de inclusão: avaliada de forma determinística contra o contexto.

    O modelo de IA não infere condições; elas vêm do registro da seção.
    """

    rule_type: Literal["has_field", "field_equals", "field_in"] = Field(
        ...,
        description=(
            "has_field: contexto tem valor não vazio no path. "
            "field_equals: valor no path é igual a value. "
            "field_in: valor no path está na lista values."
        ),
    )
    path: str = Field(
        ...,
        description="Caminho no contexto (ex.: 'modalidade', 'extras.valor_estimado').",
    )
    value: Optional[Any] = Field(None, description="Para field_equals.")
    values: Optional[List[Any]] = Field(None, description="Para field_in.")


class SectionCatalogEntry(BaseModel):
    """
    Definição técnica e versionável de uma seção do catálogo.

    O agente nunca inventa seções; apenas seleciona, ordena ou omite as que
    existem no catálogo. Título, content_type e table_schema vêm daqui.
    """

    key: str = Field(..., description="Identificador estável da seção (snake_case).")
    title: str = Field(..., description="Título formal exibido no documento.")
    document_types: List[str] = Field(
        ...,
        description="Tipos de documento nos quais a seção pode aparecer.",
    )
    content_type: Literal["text", "table", "list"] = Field(
        ..., description="Tipo de conteúdo: text, table ou list."
    )
    required: bool = Field(False, description="Se a seção é obrigatória para o tipo.")
    required_by: Optional[List[str]] = Field(
        None,
        description="Ex.: ['tcu', 'orgao_federal']. Seção obrigatória quando contexto indicar uma dessas autoridades.",
    )
    table_schema: Optional["TableSchema"] = Field(
        default=None,
        description="Schema da tabela quando content_type == 'table'.",
    )
    legal_basis: Optional[str] = Field(
        None,
        description="Fundamento legal ou normativo quando aplicável.",
    )
    conditional_rules: List[ConditionalRule] = Field(
        default_factory=list,
        description="Regras condicionais de inclusão (avaliadas deterministicamente).",
    )
    applicability_scope: Optional[ApplicabilityScope] = Field(
        None,
        description="Escopo (município, estado, órgão etc.); se presente, contexto deve bater.",
    )
    version: str = Field("1", description="Versão da definição (rastreabilidade).")
    is_active: bool = Field(True, description="Se está ativa para geração.")
    effective_from: Optional[str] = Field(
        None,
        description="Data a partir da qual a versão vale (ISO ou livre).",
    )
    parent_key: Optional[str] = Field(
        None,
        description="Key da seção pai, se for subseção; None = raiz.",
    )

    @model_validator(mode="after")
    def _validate_table_schema(self) -> "SectionCatalogEntry":
        if self.content_type == "table" and self.table_schema is None:
            raise ValueError("content_type 'table' exige table_schema.")
        if self.content_type != "table" and self.table_schema is not None:
            raise ValueError("table_schema só quando content_type == 'table'.")


class SectionCatalog(BaseModel):
    """
    Catálogo de seções versionáveis: contrato estrutural do sistema.

    Identificador e versão do catálogo permitem auditoria e compatibilidade
    com documentos antigos.
    """

    catalog_id: Optional[str] = Field(None, description="Identificador do catálogo.")
    catalog_version: Optional[str] = Field(None, description="Versão do catálogo.")
    entries: List[SectionCatalogEntry] = Field(
        ..., description="Definições de seções (sempre usar versão explícita ou ativa)."
    )


# ---- Registro manual (arquivo JSON atualizável via chave) ----
# Formato declarativo com lógica explícita; normalizado para SectionCatalogEntry.


class RegistryConditionalIf(BaseModel):
    """Atalho declarativo: incluir seção quando contexto tem valor em path contido em 'any'."""

    if_path: str = Field(
        "extras.tipo_objeto",
        description="Path no contexto (ex.: extras.tipo_objeto, extras.tipo_contratacao).",
    )
    any: List[str] = Field(
        ...,
        description="Lista de valores; se algum estiver presente no path, a seção é elegível.",
    )


class RegistrySectionEntry(BaseModel):
    """
    Entrada do registro de seções (formato JSON do arquivo / payload de atualização).

    Declarações lógicas claras; variabilidade por tipo de documento, obrigatoriedade
    por autoridade (required_by), condição por tipo de objeto (if), status e enabled.
    """

    key: str = Field(..., description="Identificador estável (snake_case).")
    title: str = Field(..., description="Título formal no documento.")
    document_types: List[str] = Field(
        ...,
        description="Tipos de documento em que a seção pode aparecer (ex.: ['etp', 'termo_referencia']).",
    )
    content_type: Literal["text", "table", "list"] = Field(
        "text", description="Tipo de conteúdo: text, table ou list."
    )
    required: bool = Field(False, description="Obrigatória para o tipo de documento.")
    required_by: Optional[List[str]] = Field(
        None,
        description="Ex.: ['tcu', 'orgao_federal']. Obrigatória quando o contexto indicar uma dessas autoridades.",
    )
    legal_basis: Optional[Union[str, List[str]]] = Field(
        None,
        description="Fundamento(s) legal(is), ex.: ['art_18_lei_14133'] ou string única.",
    )
    conditional_rules: Optional[Union[List[ConditionalRule], Dict[str, Any]]] = Field(
        None,
        description=(
            "Regras determinísticas. Formato completo: lista de ConditionalRule. "
            "Atalho: { \"if\": [\"obra\", \"servico_continuado\"], \"if_path\": \"extras.tipo_objeto\" }."
        ),
    )
    applicability_scope: Optional[ApplicabilityScope] = Field(None)
    table_schema: Optional["TableSchema"] = Field(None)
    status: Literal["optional", "required"] = Field(
        "optional",
        description="'optional' -> required=False; 'required' -> required=True (sobrescreve 'required' se ambos).",
    )
    enabled: bool = Field(True, description="Se a seção está ativa no registro (is_active).")
    version: str = Field("1", description="Versão da definição.")
    effective_from: Optional[str] = Field(None)
    parent_key: Optional[str] = Field(None, description="Key da seção pai; null = raiz.")

    @model_validator(mode="after")
    def _validate_table_for_table_type(self) -> "RegistrySectionEntry":
        if self.content_type == "table" and self.table_schema is None:
            raise ValueError("content_type 'table' exige table_schema.")
        if self.content_type != "table" and self.table_schema is not None:
            raise ValueError("table_schema só quando content_type == 'table'.")
        return self


class SectionsRegistry(BaseModel):
    """
    Registro completo de seções (arquivo JSON ou body de atualização).

    Atualização: POST /api/agent/registry com body = este JSON e header
    X-Update-Key igual ao configurado; o agente persiste no arquivo e recarrega.
    """

    catalog_id: Optional[str] = Field(None)
    catalog_version: Optional[str] = Field(None)
    entries: List[RegistrySectionEntry] = Field(..., description="Seções cadastradas manualmente.")


class StructureRequest(BaseModel):
    """
    Entrada principal do agente.

    - document_type: string identificando o tipo de documento (chave técnica).
    - context: informações mínimas (objeto, órgão, modalidade etc.).
    - sections_catalog: opcional; quando presente, o agente só seleciona/organiza
      seções deste catálogo (fluxo versionável, sem invenção de seções).
    """

    document_type: str = Field(
        ...,
        description=(
            "Tipo técnico do documento "
            "(ex.: termo_referencia, estudo_tecnico_preliminar, documento_formalizacao_demanda)."
        ),
    )
    context: ContextoBasico
    sections_catalog: Optional[SectionCatalog] = Field(
        None,
        description=(
            "Catálogo de seções versionáveis. Se informado, a IA apenas seleciona/ordena "
            "seções deste catálogo; não inventa novas. Se omitido, usa fluxo com hints/dicas."
        ),
    )

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


SectionCatalogEntry.model_rebuild()


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

