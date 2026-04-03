from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

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
