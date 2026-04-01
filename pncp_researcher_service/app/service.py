from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean, median
from typing import Any, Dict, List
import re
import unicodedata
import math
import asyncio

from .config import (
    PNCP_DEFAULT_LOOKBACK_DAYS,
    PNCP_MODALIDADES_DEFAULT,
    PNCP_ENABLE_ITEM_TABLE_LOOKUP,
    PNCP_ITEM_LOOKUP_PER_PAGE,
    PNCP_ITEM_LOOKUP_CONCURRENCY,
    PNCP_ITEM_LOOKUP_TIMEOUT_SECONDS,
    PNCP_ITEM_LOOKUP_MAX_SECONDS_PER_PAGE,
)
from .pncp_client import search_contracts, get_contract_items
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
    generic_tokens = {
        "material", "materiais", "consumo", "consumiveis", "consumivel",
        "aquisicao", "aquisição", "contratacao", "contratação",
        "servico", "servicos", "serviço", "serviços",
        "equipamento", "equipamentos", "item", "itens",
    }

    groups: List[List[str]] = []
    for raw in raw_groups:
        subgroups = [s.strip() for s in re.split(r"\be\b", raw) if s.strip()]
        if not subgroups:
            subgroups = [raw]
        for sg in subgroups:
            toks = [
                t for t in sg.split()
                if len(t) >= 3 and t not in stopwords and t not in generic_tokens
            ]
            # Fallback: se sobrar vazio, mantém ao menos os termos não-stopword.
            if not toks:
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

    words = set(normalized_text.split())

    def token_hit(tok: str) -> bool:
        if not tok:
            return False
        if tok in normalized_text:
            return True
        # Fallback por radical para plural/flexão simples (ex.: esportivo/esportiva/esportes)
        stem = tok[: max(4, min(len(tok), 6))]
        for w in words:
            if w.startswith(stem) or stem.startswith(w[: max(3, min(len(w), 5))]):
                return True
        return False

    total_score = 0.0
    for group in query_groups:
        hits = sum(1 for tok in group if token_hit(tok))
        # Regra de precisão por tamanho do grupo:
        # - 1 termo: precisa 1 hit
        # - 2-3 termos: precisa pelo menos 2 hits
        # - 4+ termos: precisa ~60% dos termos
        if len(group) == 1:
            required_hits = 1
        elif len(group) <= 3:
            required_hits = 1
        else:
            required_hits = max(1, math.ceil(len(group) * 0.5))

        if hits < required_hits:
            return 0.0  # sem cobertura mínima de um grupo -> descarta

        coverage = hits / max(1, len(group))
        group_phrase = " ".join(group)
        phrase_bonus = 0.5 if group_phrase and group_phrase in normalized_text else 0.0
        total_score += coverage + phrase_bonus

    return round(total_score, 4)


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


def _extract_cnpj_from_raw(raw: Dict[str, Any]) -> str:
    """
    Extrai CNPJ do órgão a partir de campos comuns do payload PNCP.
    """
    org = raw.get("orgaoEntidade") or {}
    candidates = [
        org.get("cnpj"),
        org.get("cnpjOrgaoEntidade"),
        raw.get("cnpjOrgaoEntidade"),
    ]
    numero_controle = str(raw.get("numeroControlePNCP") or "")
    if numero_controle and "-" in numero_controle:
        candidates.append(numero_controle.split("-")[0])
    for c in candidates:
        s = re.sub(r"\D+", "", str(c or ""))
        if len(s) == 14:
            return s
    return ""


def _item_text_from_table_rows(rows: List[Dict[str, Any]]) -> str:
    """
    Concatena os campos de descrição dos itens da tabela.
    """
    texts: List[str] = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        for key in ("descricao", "descricaoItem", "objeto", "item", "nomeItem"):
            v = str(r.get(key) or "").strip()
            if v:
                texts.append(v)
                break
    return " | ".join(texts)


async def _extract_matching_items_with_table_lookup(
    raw_items: List[Dict[str, Any]],
    query_groups: List[List[str]],
) -> List[Dict[str, Any]]:
    """
    Faz match por objeto + tabela de itens da contratação (quando disponível).
    """
    if not raw_items:
        return []

    sem = asyncio.Semaphore(max(1, PNCP_ITEM_LOOKUP_CONCURRENCY))

    async def process_one(raw: Dict[str, Any]) -> Dict[str, Any] | None:
        obj = str(raw.get("objetoCompra") or "")
        score_obj = _compute_match_score(obj, query_groups)

        item_table_text = ""
        score_table = 0.0
        try:
            cnpj = _extract_cnpj_from_raw(raw)
            ano = raw.get("anoCompra")
            seq = raw.get("sequencialCompra")
            if cnpj and ano is not None and seq is not None and score_obj <= 0:
                async with sem:
                    lookup_coro = get_contract_items(cnpj, ano, seq)
                    if PNCP_ITEM_LOOKUP_TIMEOUT_SECONDS > 0:
                        rows = await asyncio.wait_for(lookup_coro, timeout=PNCP_ITEM_LOOKUP_TIMEOUT_SECONDS)
                    else:
                        rows = await lookup_coro
                item_table_text = _item_text_from_table_rows(rows)
                score_table = _compute_match_score(item_table_text, query_groups) if item_table_text else 0.0
        except Exception:
            # Não derruba busca por falha pontual na consulta de itens
            score_table = 0.0

        score = max(score_obj, score_table)
        if score <= 0:
            return None

        org = raw.get("orgaoEntidade") or {}
        unid = raw.get("unidadeOrgao") or {}
        valor = raw.get("valorTotalEstimado")
        try:
            valor_f = float(valor) if valor is not None else None
        except Exception:
            valor_f = None

        return {
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
            "match_origem": "tabela_itens" if score_table >= score_obj and score_table > 0 else "objeto",
        }

    selected = raw_items[: max(1, PNCP_ITEM_LOOKUP_PER_PAGE)]
    tasks = [asyncio.create_task(process_one(raw)) for raw in selected]
    matched: List[Dict[str, Any]] = []
    try:
        if PNCP_ITEM_LOOKUP_MAX_SECONDS_PER_PAGE > 0:
            done_iter = asyncio.as_completed(tasks, timeout=PNCP_ITEM_LOOKUP_MAX_SECONDS_PER_PAGE)
        else:
            done_iter = asyncio.as_completed(tasks)
        for done in done_iter:
            try:
                result = await done
            except Exception:
                result = None
            if result:
                matched.append(result)
    except TimeoutError:
        # Estourou orçamento da página: devolve o que já conseguiu sem travar stream.
        pass
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()

    matched.sort(key=lambda x: x.get("score_relevancia") or 0, reverse=True)
    return matched


def _dedupe_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for it in items:
        key = (
            str(it.get("numero_pncp") or ""),
            str(it.get("ano_compra") or ""),
            str(it.get("sequencial_compra") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


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
    modalidades = [payload.codigo_modalidade] if payload.codigo_modalidade is not None else PNCP_MODALIDADES_DEFAULT

    all_items: List[Dict[str, Any]] = []
    pages_processed = 0
    total_page_budget = max(1, payload.max_paginas)
    pages_per_modalidade = max(1, math.ceil(total_page_budget / max(1, len(modalidades))))

    for modalidade in modalidades:
        page = payload.pagina
        pages_used_this_modalidade = 0
        while pages_used_this_modalidade < pages_per_modalidade and pages_processed < total_page_budget:
            batch = await search_contracts(
                data_inicial=data_inicial,
                data_final=data_final,
                codigo_modalidade=modalidade,
                uf=payload.uf,
                codigo_municipio_ibge=payload.codigo_municipio_ibge,
                pagina=page,
                tamanho_pagina=payload.tamanho_pagina,
            )
            pages_used_this_modalidade += 1
            pages_processed += 1

            if PNCP_ENABLE_ITEM_TABLE_LOOKUP:
                page_items = await _extract_matching_items_with_table_lookup(batch or [], query_groups)
            else:
                page_items = _extract_matching_items(batch or [], query_groups)
            all_items.extend(page_items)

            yield {
                "type": "page",
                "modalidade": modalidade,
                "page": page,
                "raw_count": len(batch or []),
                "matched_count": len(page_items),
                "items": page_items,
            }

            if not batch or len(batch) < max(10, min(payload.tamanho_pagina, 50)):
                break
            page += 1
        if pages_processed >= total_page_budget:
            break

    all_items = _dedupe_items(all_items)
    all_items.sort(key=lambda x: x.get("score_relevancia") or 0, reverse=True)

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
            "modalidades_consideradas": modalidades,
            "pagina_inicial": payload.pagina,
            "max_paginas": payload.max_paginas,
        },
        "stats": stats,
        "itens": all_items,
    }


async def market_search(payload: MarketSearchRequest) -> Dict[str, Any]:
    final_event: Dict[str, Any] | None = None
    async for event in market_search_stream(payload):
        if event.get("type") == "final":
            final_event = event
    if not final_event:
        return {"ok": True, "filtros": {}, "stats": {"total_registros": 0}, "itens": []}
    # Mantém contrato de resposta do endpoint síncrono
    return {
        "ok": bool(final_event.get("ok", True)),
        "filtros": final_event.get("filtros", {}),
        "stats": final_event.get("stats", {}),
        "itens": final_event.get("itens", []),
    }
