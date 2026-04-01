from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean, median
from typing import Any, Dict, List
import re
import unicodedata

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


def _normalize_text(text: str) -> str:
    text = (text or "").strip().lower()
    if not text:
        return ""
    # Remove acentos para melhorar match (ex.: "bambolê" -> "bambole")
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _build_query_groups(termo_busca: str) -> List[List[str]]:
    """
    Divide consulta em grupos de itens para busca mais precisa.
    Ex.: "bambolê, cone e corda" -> [["bambole"], ["cone"], ["corda"]]
    """
    normalized = _normalize_text(termo_busca)
    if not normalized:
        return []

    raw_groups = [g.strip() for g in re.split(r"[;,/]+", normalized) if g.strip()]
    if not raw_groups:
        raw_groups = [normalized]

    stopwords = {
        "de", "da", "do", "das", "dos", "para", "com", "sem", "em", "no", "na", "nos", "nas",
        "por", "e", "ou", "a", "o", "as", "os", "um", "uma", "uns", "umas",
    }

    groups: List[List[str]] = []
    for raw in raw_groups:
        subgroups = [s.strip() for s in re.split(r"\be\b", raw) if s.strip()]
        if not subgroups:
            subgroups = [raw]
        for sg in subgroups:
            toks = [t for t in sg.split() if len(t) >= 3 and t not in stopwords]
            if toks:
                groups.append(toks)
    return groups


def _compute_match_score(text: str, query_groups: List[List[str]]) -> float:
    """
    Score de relevância + regra de precisão:
    - precisa casar ao menos 1 token de CADA grupo (AND entre grupos)
    - score favorece maior cobertura e frase completa do grupo.
    """
    if not query_groups:
        return 0.0

    normalized_text = _normalize_text(text)
    if not normalized_text:
        return 0.0

    total_score = 0.0
    for group in query_groups:
        hits = sum(1 for tok in group if tok in normalized_text)
        if hits == 0:
            return 0.0  # sem cobertura mínima de um grupo -> descarta

        coverage = hits / max(1, len(group))
        group_phrase = " ".join(group)
        phrase_bonus = 0.5 if group_phrase and group_phrase in normalized_text else 0.0
        total_score += coverage + phrase_bonus

    return round(total_score, 4)


async def market_search(payload: MarketSearchRequest) -> Dict[str, Any]:
    di, df = _default_dates()
    data_inicial = payload.data_inicial or di
    data_final = payload.data_final or df
    query_groups = _build_query_groups(payload.termo_busca)

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
        score = _compute_match_score(obj, query_groups)
        if score <= 0:
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
                "score_relevancia": score,
            }
        )

    # Ordena da maior relevância para menor
    items.sort(key=lambda x: x.get("score_relevancia") or 0, reverse=True)

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


def _extract_matching_items(raw_items: List[Dict[str, Any]], query_groups: List[List[str]]) -> List[Dict[str, Any]]:
    """Transforma payload bruto do PNCP em itens filtrados/rankeados."""
    matched: List[Dict[str, Any]] = []
    for raw in raw_items:
        obj = str(raw.get("objetoCompra") or "")
        score = _compute_match_score(obj, query_groups)
        if score <= 0:
            continue
        org = raw.get("orgaoEntidade") or {}
        unid = raw.get("unidadeOrgao") or {}
        valor = raw.get("valorTotalEstimado")
        try:
            valor_f = float(valor) if valor is not None else None
        except Exception:
            valor_f = None
        matched.append(
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
                "score_relevancia": score,
            }
        )
    matched.sort(key=lambda x: x.get("score_relevancia") or 0, reverse=True)
    return matched


async def market_search_stream(payload: MarketSearchRequest):
    """
    Versão incremental da busca:
    - processa página a página;
    - entrega eventos com progresso e itens encontrados.
    """
    di, df = _default_dates()
    data_inicial = payload.data_inicial or di
    data_final = payload.data_final or df
    query_groups = _build_query_groups(payload.termo_busca)

    all_items: List[Dict[str, Any]] = []
    page = payload.pagina
    pages_processed = 0

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
        pages_processed += 1

        page_items = _extract_matching_items(batch or [], query_groups)
        all_items.extend(page_items)

        yield {
            "type": "page",
            "page": page,
            "raw_count": len(batch or []),
            "matched_count": len(page_items),
            "items": page_items,
        }

        if not batch or len(batch) < max(10, min(payload.tamanho_pagina, 50)):
            break
        page += 1

    valores = [x["valor_global"] for x in all_items if isinstance(x.get("valor_global"), (int, float)) and x["valor_global"] > 0]
    stats = {
        "total_registros": len(all_items),
        "com_valor": len(valores),
        "valor_min": min(valores) if valores else None,
        "valor_max": max(valores) if valores else None,
        "valor_medio": round(mean(valores), 2) if valores else None,
        "valor_mediano": round(median(valores), 2) if valores else None,
        "pages_processed": pages_processed,
    }

    yield {
        "type": "final",
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
        "itens": all_items,
    }
