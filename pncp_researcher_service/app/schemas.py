from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .config import PNCP_MAX_PAGINAS_PER_REQUEST


class HealthResponse(BaseModel):
    ok: bool = True
    service: str = "pncp_researcher_service"


class MarketSearchRequest(BaseModel):
    termo_busca: str = Field(
        ...,
        description="Termo para busca no objeto da contratação e, quando disponível, nas linhas da tabela de itens (API de itens do PNCP).",
    )
    uf: Optional[str] = Field(None, description="UF para recorte geográfico.")
    codigo_municipio_ibge: Optional[str] = Field(None, description="Código IBGE do município.")
    data_inicial: Optional[str] = Field(None, description="AAAAMMDD.")
    data_final: Optional[str] = Field(None, description="AAAAMMDD.")
    codigo_modalidade: Optional[int] = Field(
        None,
        description="Código da modalidade no PNCP. Se omitido, pesquisa todas as modalidades.",
    )
    pagina: int = Field(1, description="Página inicial.")
    tamanho_pagina: int = Field(50, description="Tamanho da página (10 a 50 no PNCP).")
    max_paginas: int = Field(
        15,
        description=f"Quantidade máxima de páginas para varrer (1–{PNCP_MAX_PAGINAS_PER_REQUEST}, teto via PNCP_MAX_PAGINAS_PER_REQUEST).",
    )
    quantidade_referencia: Optional[float] = Field(
        None,
        description="Quantidade de referência do item da cotação para melhorar julgamento de aderência.",
    )
    unidade_medida_referencia: Optional[str] = Field(
        None,
        description="Unidade de referência do item da cotação (ex.: UN, KG, M2).",
    )
    valor_base_referencia: Optional[float] = Field(
        None,
        description="Valor base/faixa regional do item da cotação para coerência de preço.",
    )
    variacao_percentual_referencia: Optional[float] = Field(
        None,
        description="Variação percentual da faixa regional do item (ex.: 20 => +/-20%).",
    )

    @field_validator("max_paginas")
    @classmethod
    def validate_max_paginas(cls, v: int) -> int:
        cap = max(1, int(PNCP_MAX_PAGINAS_PER_REQUEST))
        return max(1, min(int(v), cap))

    @field_validator("termo_busca")
    @classmethod
    def validate_termo(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("termo_busca é obrigatório.")
        return v


class MarketSearchResponse(BaseModel):
    ok: bool
    filtros: Dict[str, Any]
    stats: Dict[str, Any]
    itens: List[Dict[str, Any]]


class LocalBackfillRequest(BaseModel):
    months: int = Field(12, description="Janela histórica em meses para ingestão local.")
    max_paginas: Optional[int] = Field(
        None,
        description="Máximo de páginas por modalidade. Use null para varrer sem teto (até o PNCP não retornar mais dados).",
    )
    tamanho_pagina: int = Field(50, description="Tamanho da página no PNCP (10-50).")
    uf: Optional[str] = Field(None, description="Filtro opcional de UF para reduzir volume.")
    codigo_municipio_ibge: Optional[str] = Field(
        None, description="Filtro opcional de município (IBGE)."
    )
    include_items: bool = Field(
        True,
        description="Se true, busca também tabela de itens de cada contratação (sem baixar PDFs).",
    )


class ResearchSessionCreateRequest(BaseModel):
    """Corpo para criar uma ordem de pesquisa (cotação) persistida no serviço PNCP."""

    titulo: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Título da cotação / ordem de pesquisa.",
    )
    modelo_cotacao: str = Field(
        default="pesquisa_precos_padrao",
        min_length=1,
        max_length=120,
        description="Chave do modelo de cotação (ex.: pesquisa_precos_padrao). Persistida em pesquisador_sessoes.modelo_cotacao.",
    )
    termo_busca: Optional[str] = Field(
        None,
        max_length=2000,
        description="Termo inicial de busca no PNCP; se omitido, usa o título.",
    )
    filtros: Dict[str, Any] = Field(default_factory=dict, description="Filtros adicionais (UF, período, etc.).")

    @field_validator("titulo", "modelo_cotacao")
    @classmethod
    def strip_required_strings(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("Campo não pode ser vazio.")
        return s

    @model_validator(mode="after")
    def default_termo_busca(self) -> ResearchSessionCreateRequest:
        tb = (self.termo_busca or "").strip()
        self.termo_busca = tb if tb else self.titulo.strip()
        return self


class ResearchSessionAddItemsRequest(BaseModel):
    itens: List[Dict[str, Any]] = Field(default_factory=list, description="Itens selecionados para registro na cotação.")


class ResearchSessionUpdateRequest(BaseModel):
    titulo: Optional[str] = Field(None, description="Novo título da cotação.")
    status: Optional[str] = Field(None, description="Status da cotação (ex.: aberta/finalizada).")
    termo_busca: Optional[str] = Field(None, description="Novo termo de pesquisa PNCP associado à cotação.")
    modelo_cotacao: Optional[str] = Field(None, description="Novo modelo de cotação (chave persistida).")
