from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    ok: bool = True
    service: str = "pncp_researcher_service"


class MarketSearchRequest(BaseModel):
    termo_busca: str = Field(..., description="Termo principal para busca no objeto da contratação.")
    uf: Optional[str] = Field(None, description="UF para recorte geográfico.")
    codigo_municipio_ibge: Optional[str] = Field(None, description="Código IBGE do município.")
    data_inicial: Optional[str] = Field(None, description="AAAAMMDD.")
    data_final: Optional[str] = Field(None, description="AAAAMMDD.")
    codigo_modalidade: int = Field(8, description="Código da modalidade no PNCP (8=dispensa).")
    pagina: int = Field(1, description="Página inicial.")
    tamanho_pagina: int = Field(50, description="Tamanho da página (10 a 50 no PNCP).")
    max_paginas: int = Field(2, description="Quantidade máxima de páginas para varrer.")

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
