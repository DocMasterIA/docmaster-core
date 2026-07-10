from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .config import PNCP_MAX_PAGINAS_PER_REQUEST
from .pricing_faixa import normalize_variacao_sentido


class HealthResponse(BaseModel):
    ok: bool = True
    service: str = "pncp_researcher_service"
    search_code_rev: str = ""
    db_path: str = ""
    db_bytes: int = 0
    db_on_data_volume: bool = False
    index_hint: str = ""
    ingest: Optional[Dict[str, Any]] = None
    ia: Optional[Dict[str, Any]] = None


class GeoRecorte(BaseModel):
    """Um recorte UF + município opcional; vários recortes são unidos com OR no SQL."""

    uf: str = Field(..., min_length=2, max_length=2, description="Sigla da UF.")
    municipio: Optional[str] = Field(
        None,
        description="Nome do município; omitido ou vazio restringe apenas à UF.",
    )

    @field_validator("uf")
    @classmethod
    def normalize_uf(cls, v: str) -> str:
        s = (v or "").strip().upper()
        if len(s) != 2:
            raise ValueError("UF deve ter 2 letras.")
        return s

    @field_validator("municipio", mode="before")
    @classmethod
    def strip_municipio_recorte(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s or None


class MarketSearchRequest(BaseModel):
    termo_busca: str = Field(
        ...,
        description="Termo para busca no objeto da contratação e, quando disponível, nas linhas da tabela de itens (API de itens do PNCP).",
    )
    uf: Optional[str] = Field(None, description="UF para recorte geográfico.")
    codigo_municipio_ibge: Optional[str] = Field(None, description="Código IBGE do município.")
    municipio: Optional[str] = Field(
        None,
        description="Nome do município (filtro no índice local de itens; comparado com normalização de busca).",
    )
    recortes_geograficos: Optional[List[GeoRecorte]] = Field(
        None,
        description="Vários UF+município (OR). Se preenchido, substitui o par único uf/municipio (máx. 30).",
    )
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
    variacao_sentido_referencia: Optional[str] = Field(
        None,
        description="Sentido da variação: ambos (±), baixo (só abaixo do base) ou cima (só acima).",
    )
    somente_homologados: Optional[bool] = Field(
        None,
        description="Se true, retorna só itens homologados/adjudicados. Omitido = usa PNCP_SEARCH_ONLY_HOMOLOGATED do serviço.",
    )
    busca_lote: Optional[bool] = Field(
        False,
        description=(
            "Cotação com dezenas de itens: resumo LLM desligado; rerank opcional via "
            "PNCP_IA_RERANK_BULK_ENABLED (menos candidatos/timeout que busca manual)."
        ),
    )
    fontes_habilitadas: Optional[List[str]] = Field(
        None,
        description="IDs das fontes de preço (ex.: pncp). Usado em /market-search/federated.",
    )

    @field_validator("fontes_habilitadas", mode="before")
    @classmethod
    def normalize_fontes(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, str):
            parts = [p.strip().lower() for p in v.split(",") if p.strip()]
            return parts or None
        if isinstance(v, list):
            out = [str(x).strip().lower() for x in v if str(x).strip()]
            return out or None
        return None

    @field_validator("variacao_sentido_referencia", mode="before")
    @classmethod
    def normalize_sentido(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            return None
        return normalize_variacao_sentido(s)

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

    @field_validator("municipio", mode="before")
    @classmethod
    def strip_municipio(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    @field_validator("recortes_geograficos", mode="before")
    @classmethod
    def empty_recortes_to_none(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, list) and len(v) == 0:
            return None
        return v

    @field_validator("recortes_geograficos")
    @classmethod
    def cap_recortes_list(cls, v: Optional[List[GeoRecorte]]) -> Optional[List[GeoRecorte]]:
        if not v:
            return v
        return v[:30]


class MarketSearchResponse(BaseModel):
    ok: bool
    filtros: Dict[str, Any]
    stats: Dict[str, Any]
    itens: List[Dict[str, Any]]


class IngestPlanRequest(BaseModel):
    uf: Optional[str] = Field(None, description="Planejar só uma UF; omitido = todas.")
    pages_per_scope: Optional[int] = Field(
        None,
        description="Páginas de catálogo a enfileirar por escopo UF×modalidade.",
    )
    contracts_without_items_limit: Optional[int] = Field(
        None,
        description="Máx. contratos sem itens a enfileirar neste planejamento.",
    )


class LocalBackfillRequest(BaseModel):
    months: Optional[int] = Field(
        None,
        description="Legado: janela em meses (×30 dias). Ignorado se ``days`` for informado.",
    )
    days: Optional[int] = Field(
        None,
        description="Janela em dias (máx. 365). Default do serviço: PNCP_LOCAL_BACKFILL_DAYS.",
    )
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


class LocalSyncCatalogRequest(BaseModel):
    batch_size: int = Field(
        25000,
        ge=100,
        le=100000,
        description="Itens por lote ao materializar situacao_item/fornecedor_elegivel do raw_json.",
    )
    max_batches: int = Field(
        1,
        ge=1,
        le=200,
        description="Quantos lotes executar nesta chamada.",
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
