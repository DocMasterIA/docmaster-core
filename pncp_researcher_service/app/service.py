from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean, median
from typing import Any, Dict, List

from .config import PNCP_DEFAULT_LOOKBACK_DAYS
from .pncp_client import search_contracts
from .schemas import MarketSearchRequest


def _default_dates() -> tuple[str, str]:
    today = datetime.utcnow()
    start = today - timedelta(days=PNCP_DEFAULT_LOOKBACK_DAYS)
    return start.strftime("%Y%m%d"), today.strftime("%Y%m%d")


def _contains_tokens(text: str, tokens: List[str]) -> bool:
    if not tokens:
        return True
    t = (text or "").lower()
    return all(tok in t for tok in tokens[:2]) or any(tok in t for tok in tokens)


async def market_search(payload: MarketSearchRequest) -> Dict[str, Any]:
    di, df = _default_dates()
    data_inicial = payload.data_inicial or di
    data_final = payload.data_final or df
    tokens = [x for x in payload.termo_busca.lower().split() if len(x) >= 3][:16]

    raw_items: List[Dict[str, Any]] = []
    page = payload.pagina
    for _ in range(max(1, payload.max_paginas)):
        batch = await search_contracts(
            data_inicial=data_inicial,
            data_final=data_final,
            codigo_modalidade=payload.codigo_modalidade,
            uf=payload.uf,
            codigo_municipio_ibge=payload.codigo_municipio_ibge,
            pagina=page,
            tamanho_pagina=payload.tamanho_pagina,
        )
        if not batch:
            break
        raw_items.extend(batch)
        if len(batch) < max(10, min(payload.tamanho_pagina, 50)):
            break
        page += 1

    items: List[Dict[str, Any]] = []
    for raw in raw_items:
        obj = str(raw.get("objetoCompra") or "")
        if not _contains_tokens(obj, tokens):
            continue
        org = raw.get("orgaoEntidade") or {}
        unid = raw.get("unidadeOrgao") or {}
        valor = raw.get("valorTotalEstimado")
        try:
            valor_f = float(valor) if valor is not None else None
        except Exception:
            valor_f = None
        items.append(
            {
                "numero_pncp": raw.get("numeroControlePNCP"),
                "objeto_resumido": obj,
                "orgao": org.get("razaoSocial") or org.get("razaosocial"),
                "municipio": unid.get("municipioNome"),
                "uf": unid.get("ufSigla"),
                "modalidade": raw.get("modalidadeNome"),
                "valor_global": valor_f,
                "situacao": raw.get("situacaoCompraNome"),
                "ano_compra": raw.get("anoCompra"),
                "sequencial_compra": raw.get("sequencialCompra"),
            }
        )

    valores = [x["valor_global"] for x in items if isinstance(x.get("valor_global"), (int, float)) and x["valor_global"] > 0]
    stats = {
        "total_registros": len(items),
        "com_valor": len(valores),
        "valor_min": min(valores) if valores else None,
        "valor_max": max(valores) if valores else None,
        "valor_medio": round(mean(valores), 2) if valores else None,
        "valor_mediano": round(median(valores), 2) if valores else None,
    }

    return {
        "ok": True,
        "filtros": {
            "termo_busca": payload.termo_busca,
            "uf": payload.uf,
            "codigo_municipio_ibge": payload.codigo_municipio_ibge,
            "data_inicial": data_inicial,
            "data_final": data_final,
            "codigo_modalidade": payload.codigo_modalidade,
            "pagina_inicial": payload.pagina,
            "max_paginas": payload.max_paginas,
        },
        "stats": stats,
        "itens": items,
    }
