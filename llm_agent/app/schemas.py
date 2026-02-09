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
    categories: Optional[List[str]] = Field(
        None,
        description=(
            "Padrões/categorias do documento (ex.: compra_medicamentos, obras, tic). "
            "Quando o contexto informar document_pattern ou categoria, seções com matching são elegíveis."
        ),
    )
    description: Optional[str] = Field(
        None,
        description="Texto curto para matching por intenção (ex.: 'Especificações para aquisição de medicamentos').",
    )
    content_type: Literal["text", "table", "list"] = Field(
        ..., description="Tipo de conteúdo: text, table ou list."
    )
    required: bool = Field(False, description="Se a seção é obrigatória para o tipo (nível estrutural).")
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

    Declarações lógicas claras; variabilidade por tipo de documento, condição por tipo
    de objeto (if), status e enabled. Aspectos de funcionamento jurídico (fundamento
    legal, obrigatoriedade por autoridade etc.) ficam para a camada de RAG, não aqui.
    """

    key: str = Field(..., description="Identificador estável (snake_case).")
    title: str = Field(..., description="Título formal no documento.")
    document_types: List[str] = Field(
        ...,
        description="Tipos de documento em que a seção pode aparecer (ex.: ['etp', 'termo_referencia']).",
    )
    categories: Optional[List[str]] = Field(
        None,
        description="Padrões/categorias (ex.: compra_medicamentos, obras, tic). Definido posteriormente.",
    )
    description: Optional[str] = Field(
        None,
        description="Texto curto para a IA mapear intenção do usuário (título ou pedido em outro formato).",
    )
    content_type: Literal["text", "table", "list"] = Field(
        "text", description="Tipo de conteúdo: text, table ou list."
    )
    required: bool = Field(False, description="Obrigatória para o tipo de documento (nível estrutural).")
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

    Atualização: POST /api/agent/registry com body = este JSON; o agente persiste no arquivo e recarrega.
    """

    catalog_id: Optional[str] = Field(None)
    catalog_version: Optional[str] = Field(None)
    entries: List[RegistrySectionEntry] = Field(..., description="Seções cadastradas manualmente.")


class SectionMatchAnnotation(BaseModel):
    """
    Anotação de correspondência: o pedido do usuário (user_phrase) foi interpretado
    como referindo-se à seção cadastrada (key), com nível de certeza (confidence).
    """
    key: str = Field(..., description="Key da seção no catálogo que corresponde ao pedido.")
    user_phrase: str = Field(
        ...,
        description="Trecho ou paráfrase do pedido do usuário que foi associado a esta seção.",
    )
    confidence: Literal["high", "medium", "low"] = Field(
        ...,
        description=(
            "high = praticamente a mesma cláusula; "
            "medium = claramente relacionada; low = possível relação."
        ),
    )


class StructureRequest(BaseModel):
    """
    Entrada principal do agente.

    - document_type: string identificando o tipo de documento (chave técnica).
    - context: informações mínimas (objeto, órgão, modalidade etc.).
    - sections_catalog: opcional; quando presente, o agente só seleciona/organiza
      seções deste catálogo (fluxo versionável, sem invenção de seções).
    - user_prompt: opcional; quando presente (ex.: structure-from-prompt), a IA
      calcula correspondências entre o pedido e as seções cadastradas (section_matches).
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
    user_prompt: Optional[str] = Field(
        None,
        description=(
            "Texto livre do usuário (ex.: pedido por cláusula). Quando informado no fluxo "
            "com catálogo, a IA devolve section_matches com nível de certeza (high/medium/low)."
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
    section_matches: Optional[List[SectionMatchAnnotation]] = Field(
        None,
        description=(
            "Quando user_prompt foi informado e há catálogo: correspondências entre "
            "trechos do pedido e seções incluídas, com nível de certeza (high/medium/low)."
        ),
    )


# ---- Estrutura de cláusulas hierárquicas (esqueleto, sem texto) ----
# Usada para descrever a árvore de cláusulas/subcláusulas que um documento pode ter.
# Subcláusulas NÃO possuem título próprio; apenas cláusulas de topo têm title exibido.


class ClauseNode(BaseModel):
    """
    Nó estrutural de cláusula.

    - logical_id: identificador lógico estável (ex.: RESPONSABILIDADES_CONTRATADA).
    - title: título exibido apenas para cláusulas de topo; subcláusulas não têm título.
    - status: situação estrutural da cláusula (ativa, substituída, revogada).
    - scope: escopo de validade (federal, estadual, municipal, etc.).
    - version: versão estrutural da cláusula.
    - children: subcláusulas hierárquicas, que representam slots estruturais.
    """

    logical_id: str = Field(..., description="Identificador lógico estável da cláusula.")
    title: Optional[str] = Field(
        None,
        description=(
            "Título exibido apenas para cláusulas de topo. "
            "Subcláusulas não devem ter título próprio."
        ),
    )
    status: Optional[Literal["active", "superseded", "revoked"]] = Field(
        None,
        description="Situação estrutural da cláusula.",
    )
    scope: Optional[Dict[str, Any]] = Field(
        None,
        description="Escopo de validade (federal, estadual, municipal, órgão específico, etc.).",
    )
    version: Optional[str] = Field(
        None,
        description="Versão estrutural da cláusula.",
    )
    children: List["ClauseNode"] = Field(
        default_factory=list,
        description="Subcláusulas hierárquicas (slots estruturais, sem texto jurídico).",
    )


class ClauseStructureRequest(BaseModel):
    """
    Entrada para o agente de estrutura de cláusulas hierárquicas.

    O objetivo é obter APENAS o esqueleto estrutural de cláusulas/subcláusulas
    (slots), sem texto jurídico final.
    """

    document_type: str = Field(
        ...,
        description="Tipo de documento ao qual a estrutura de cláusulas se aplica.",
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Contexto livre (objeto, modalidade, órgão, extras, etc.).",
    )
    section_key: Optional[str] = Field(
        None,
        description="Opcional: key da seção/camada estrutural à qual as cláusulas se referem.",
    )
    base_description: Optional[str] = Field(
        None,
        description=(
            "Descrição textual breve da cláusula/assunto a estruturar "
            "(ex.: 'cláusula de garantias', 'cláusula de responsabilidades')."
        ),
    )

    @field_validator("document_type", "section_key", "base_description", mode="before")
    @classmethod
    def _strip_opt_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


class ClauseStructureResponse(BaseModel):
    """
    Resposta do agente de estrutura de cláusulas.

    Retorna apenas a árvore estrutural (ClauseNode), sem texto jurídico.
    """

    ok: bool
    root_clauses: Optional[List[ClauseNode]] = Field(
        None,
        description="Cláusulas de topo estruturais, com subcláusulas hierárquicas.",
    )
    error: Optional[str] = None
    retries: int = 0


# ---- Composição jurídica controlada (cláusulas - TEXTO) ----
# Contrato para geração de texto de cláusulas a partir de base registrada + RAG.
# O agente NUNCA inventa; só adapta cláusulas existentes e indica proveniência.


class ClauseCompositionRequest(BaseModel):
    """
    Entrada para o agente de composição de cláusulas.

    A geração deve derivar da cláusula base (key/version/scope) e do contexto;
    RAG snippets fundamentam variações textuais.
    """

    clause_key: str = Field(..., description="Key técnica da cláusula base registrada.")
    version: Optional[str] = Field(None, description="Versão da cláusula base; se omitido, usa ativa.")
    applicability_scope: Optional[Dict[str, Any]] = Field(
        None,
        description="Escopo (município, estado, órgão etc.) quando relevante.",
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parâmetros contextuais: objeto, modalidade, natureza do bem, finalidade, etc.",
    )
    rag_snippets: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Documentos/trechos recuperados (RAG) que podem fundamentar variações.",
    )


class ClauseCompositionResponse(BaseModel):
    """
    Saída do agente de composição: texto gerado + proveniência obrigatória,
    ou sinalização explícita de que não pode gerar com segurança.
    """

    generated_text: Optional[str] = Field(
        None,
        description="Texto da cláusula adaptada ao contexto. Nulo se cannot_generate=True.",
    )
    source_key: str = Field(..., description="Key da cláusula base utilizada.")
    source_version: str = Field(..., description="Versão da cláusula base utilizada.")
    params_applied: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parâmetros contextuais efetivamente aplicados na adaptação.",
    )
    sources_used: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Referências aos trechos RAG que justificam variações textuais.",
    )
    cannot_generate: bool = Field(
        False,
        description="True quando não há cláusula registrada adequada; não produzir conteúdo especulativo.",
    )
    reason: Optional[str] = Field(
        None,
        description="Motivo quando cannot_generate=True (ex.: cláusula não encontrada, escopo incompatível).",
    )

