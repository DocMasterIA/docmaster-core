from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..schemas import GeoRecorte, MarketSearchRequest


@dataclass
class MarketPriceHit:
    """Preço normalizado de qualquer plataforma antes de scoring/save."""

    plataforma: str
    plataforma_item_id: str
    descricao_item: str
    valor_unitario: float
    valor_unitario_homologado: Optional[float] = None
    unidade_medida: Optional[str] = None
    quantidade: Optional[float] = None
    orgao: Optional[str] = None
    municipio: Optional[str] = None
    uf: Optional[str] = None
    fornecedor_nome: Optional[str] = None
    fornecedor_cnpj: Optional[str] = None
    data_referencia: Optional[str] = None
    inciso_classificacao: Optional[str] = None
    esfera: Optional[str] = None
    url_origem: Optional[str] = None
    raw: Optional[Dict[str, Any]] = field(default_factory=dict)
    # Identidade unificada para cruzamento entre plataformas (dedup federado).
    canonical_key: Optional[str] = None
    cross_refs: Dict[str, str] = field(default_factory=dict)


@dataclass
class FederatedSearchQuery:
    """Consulta canônica para busca federada (espelha MarketSearchRequest)."""

    termo_busca: str
    uf: Optional[str] = None
    codigo_municipio_ibge: Optional[str] = None
    municipio: Optional[str] = None
    recortes_geograficos: Optional[List[GeoRecorte]] = None
    data_inicial: Optional[str] = None
    data_final: Optional[str] = None
    codigo_modalidade: Optional[int] = None
    pagina: int = 1
    tamanho_pagina: int = 50
    max_paginas: int = 15
    quantidade_referencia: Optional[float] = None
    unidade_medida_referencia: Optional[str] = None
    valor_base_referencia: Optional[float] = None
    variacao_percentual_referencia: Optional[float] = None
    variacao_sentido_referencia: Optional[str] = None
    somente_homologados: Optional[bool] = None
    busca_lote: bool = False
    lista_completa: bool = False
    fontes_habilitadas: List[str] = field(default_factory=lambda: ["pncp"])

    @classmethod
    def from_market_request(
        cls,
        payload: MarketSearchRequest,
        *,
        fontes_habilitadas: Optional[List[str]] = None,
    ) -> "FederatedSearchQuery":
        sources = fontes_habilitadas or getattr(payload, "fontes_habilitadas", None) or ["pncp"]
        clean_sources = [str(s).strip().lower() for s in sources if str(s).strip()]
        return cls(
            termo_busca=payload.termo_busca,
            uf=payload.uf,
            codigo_municipio_ibge=payload.codigo_municipio_ibge,
            municipio=payload.municipio,
            recortes_geograficos=payload.recortes_geograficos,
            data_inicial=payload.data_inicial,
            data_final=payload.data_final,
            codigo_modalidade=payload.codigo_modalidade,
            pagina=payload.pagina,
            tamanho_pagina=payload.tamanho_pagina,
            max_paginas=payload.max_paginas,
            quantidade_referencia=payload.quantidade_referencia,
            unidade_medida_referencia=payload.unidade_medida_referencia,
            valor_base_referencia=payload.valor_base_referencia,
            variacao_percentual_referencia=payload.variacao_percentual_referencia,
            variacao_sentido_referencia=payload.variacao_sentido_referencia,
            somente_homologados=payload.somente_homologados,
            busca_lote=bool(payload.busca_lote),
            lista_completa=bool(getattr(payload, "lista_completa", False)),
            fontes_habilitadas=clean_sources or ["pncp"],
        )

    def to_market_request(self) -> MarketSearchRequest:
        return MarketSearchRequest(
            termo_busca=self.termo_busca,
            uf=self.uf,
            codigo_municipio_ibge=self.codigo_municipio_ibge,
            municipio=self.municipio,
            recortes_geograficos=self.recortes_geograficos,
            data_inicial=self.data_inicial,
            data_final=self.data_final,
            codigo_modalidade=self.codigo_modalidade,
            pagina=self.pagina,
            tamanho_pagina=self.tamanho_pagina,
            max_paginas=self.max_paginas,
            quantidade_referencia=self.quantidade_referencia,
            unidade_medida_referencia=self.unidade_medida_referencia,
            valor_base_referencia=self.valor_base_referencia,
            variacao_percentual_referencia=self.variacao_percentual_referencia,
            variacao_sentido_referencia=self.variacao_sentido_referencia,
            somente_homologados=self.somente_homologados,
            busca_lote=self.busca_lote,
            lista_completa=self.lista_completa,
            fontes_habilitadas=list(self.fontes_habilitadas or ["pncp"]),
        )
