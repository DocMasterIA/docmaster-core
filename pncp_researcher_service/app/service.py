from __future__ import annotations

from datetime import date, datetime, timedelta
from statistics import mean, median
from typing import Any, Dict, List, Optional
import re
import unicodedata
import math
import asyncio

import httpx

from .config import (
    PNCP_DEFAULT_LOOKBACK_DAYS,
    PNCP_MODALIDADES_DEFAULT,
    PNCP_ENABLE_ITEM_TABLE_LOOKUP,
    PNCP_ITEM_LOOKUP_PER_PAGE,
    PNCP_ITEM_LOOKUP_CONCURRENCY,
    PNCP_ITEM_LOOKUP_TIMEOUT_SECONDS,
    PNCP_ITEM_LOOKUP_MAX_SECONDS_PER_PAGE,
    PNCP_FETCH_ITEMS_ALWAYS,
    PNCP_ITEM_ROWS_MAX_DESTAQUE,
    PNCP_ITEM_AMOSTRA_LINHAS,
    PNCP_REQUIRE_TABLE_MATCH_WHEN_ITENS_EXIST,
    PNCP_LOCAL_AUTO_INGEST,
)
from .pncp_client import create_pncp_http_client, search_contracts, get_contract_items
from .local_index import upsert_contracts, local_item_search
from .schemas import MarketSearchRequest


def _default_dates() -> tuple[str, str]:
    today = datetime.utcnow()
    start = today - timedelta(days=PNCP_DEFAULT_LOOKBACK_DAYS)
    return start.strftime("%Y%m%d"), today.strftime("%Y%m%d")


def _parse_pn_date(s: str) -> date:
    return datetime.strptime(s.strip(), "%Y%m%d").date()


def _pn_date_windows(di_s: str, df_s: str) -> List[tuple[str, str]]:
    """
    O PNCP retorna 422 se (dataFinal - dataInicial) ultrapassar 365 dias.
    Gera janelas consecutivas com folga (delta máximo 364 dias entre início e fim).
    """
    d0 = _parse_pn_date(di_s)
    d1 = _parse_pn_date(df_s)
    if d1 < d0:
        d0, d1 = d1, d0
    max_step = timedelta(days=364)
    out: List[tuple[str, str]] = []
    cur = d0
    while cur <= d1:
        chunk_end = min(cur + max_step, d1)
        out.append((cur.strftime("%Y%m%d"), chunk_end.strftime("%Y%m%d")))
        cur = chunk_end + timedelta(days=1)
    return out


def _objeto_compra_text(raw: Dict[str, Any]) -> str:
    """Texto do objeto nos campos usados pelo PNCP (nomemclatura varia entre versões)."""
    for k in ("objetoCompra", "objeto", "descricaoObjeto", "titulo"):
        v = raw.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


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
    # Não incluir "material"/"materiais" aqui: em buscas como "material esportivo"
    # o usuário quer os dois termos; remover "material" gerava só "esportivo" e muito ruído.
    generic_tokens = {
        "consumo", "consumiveis", "consumivel",
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
    if not groups and normalized:
        toks = [t for t in normalized.split() if len(t) >= 2]
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
        if tok in words:
            return True
        # Token muito curto: só casamento exato (evita "sol" em "solicitacao").
        if len(tok) < 4:
            return False
        # 4 letras (ex.: "pneu"): plural / flexão curta — sem isso "pneus" nunca casava.
        if len(tok) == 4:
            max_w = len(tok) + 2
            for w in words:
                if w.startswith(tok) and len(w) <= max_w:
                    return True
            return False
        # >= 5: radical para flexões (ex.: esportivo/esportiva/esportes).
        stem = tok[: min(len(tok), 6)]
        for w in words:
            if len(w) < 5:
                continue
            if w.startswith(stem):
                return True
            if tok.startswith(w[:5]):
                return True
        return False

    total_score = 0.0
    for group in query_groups:
        hits = sum(1 for tok in group if token_hit(tok))
        # Dentro do mesmo segmento (ex.: "material esportivo"), exige AND entre termos
        # quando há 2 palavras: evita "só esporte/esportivas" sem material.
        if len(group) == 1:
            required_hits = 1
        elif len(group) == 2:
            required_hits = 2
        elif len(group) == 3:
            required_hits = 2
        else:
            required_hits = max(2, math.ceil(len(group) * 0.5))

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
        obj = _objeto_compra_text(raw)
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


def _row_text_for_match(r: Dict[str, Any]) -> str:
    """Texto de uma linha da tabela PNCP para pontuação."""
    if not isinstance(r, dict):
        return ""
    parts: List[str] = []
    for key in (
        "descricao",
        "descricaoItem",
        "descricaoResumida",
        "materialOuServicoNome",
        "item",
        "nomeItem",
        "objeto",
        "tipoItemNome",
        "denominacao",
        "nome",
    ):
        v = str(r.get(key) or "").strip()
        if v:
            parts.append(v)
    return " ".join(parts)


def _normalize_pncp_item_row(r: Dict[str, Any]) -> Dict[str, Any]:
    """Campos úteis da linha de item retornados ao cliente."""
    if not isinstance(r, dict):
        return {}
    out: Dict[str, Any] = {}
    for k in (
        "numeroItem",
        "ordemItem",
        "sequencialItem",
        "descricao",
        "descricaoItem",
        "descricaoResumida",
        "materialOuServicoNome",
        "tipoItemNome",
        "quantidade",
        "unidadeMedida",
        "unidadeFornecimentoNome",
        "valorUnitarioEstimado",
        "valorTotal",
        "valorTotalEstimado",
        "valorUnitarioHomologado",
        "valorTotalHomologado",
        "situacaoItemNome",
    ):
        if r.get(k) is not None:
            out[k] = r[k]
    return out


def _item_text_from_table_rows(rows: List[Dict[str, Any]]) -> str:
    """Concatena textos das linhas para pontuação agregada na tabela."""
    texts: List[str] = []
    for r in rows or []:
        t = _row_text_for_match(r)
        if t:
            texts.append(t)
    return " | ".join(texts)


def _itens_destaque_e_amostra(
    rows: List[Dict[str, Any]],
    query_groups: List[List[str]],
    score_obj: float,
) -> tuple[List[Dict[str, Any]], str, int]:
    """
    Monta lista para o JSON: linhas que batem na busca; se não houver, amostra quando objeto bate.
    Retorna (lista_normalizada, modo, total_linhas).
    """
    total = len(rows or [])
    cap = max(1, PNCP_ITEM_ROWS_MAX_DESTAQUE)
    destaque: List[Dict[str, Any]] = []
    for r in rows or []:
        line = _row_text_for_match(r)
        if line and _compute_match_score(line, query_groups) > 0:
            destaque.append(_normalize_pncp_item_row(r))
            if len(destaque) >= cap:
                break
    if destaque:
        return destaque[:cap], "linhas_match", total
    if score_obj > 0 and rows:
        amostra_n = max(0, PNCP_ITEM_AMOSTRA_LINHAS)
        sample = [_normalize_pncp_item_row(r) for r in rows[:amostra_n]]
        return sample, "amostra_objeto", total
    return [], "sem_linhas", total


def _table_supports_query(rows: List[Dict[str, Any]], query_groups: List[List[str]]) -> bool:
    """
    True se alguma linha (ou o texto agregado) da tabela PNCP sustenta o termo de busca.
    Lista vazia = não aplicável (chamador trata como "sem confirmação possível").
    """
    if not rows:
        return False
    for r in rows:
        line = _row_text_for_match(r)
        if line and _compute_match_score(line, query_groups) > 0:
            return True
    agg = _item_text_from_table_rows(rows)
    if agg and _compute_match_score(agg, query_groups) > 0:
        return True
    return False


async def _extract_matching_items_with_table_lookup(
    raw_items: List[Dict[str, Any]],
    query_groups: List[List[str]],
    http_client: Optional[httpx.AsyncClient] = None,
) -> List[Dict[str, Any]]:
    """
    Faz match por objeto + tabela de itens da contratação (quando disponível).
    """
    if not raw_items:
        return []

    sem = asyncio.Semaphore(max(1, PNCP_ITEM_LOOKUP_CONCURRENCY))

    async def process_one(raw: Dict[str, Any]) -> Dict[str, Any] | None:
        obj = _objeto_compra_text(raw)
        score_obj_bruto = _compute_match_score(obj, query_groups)

        item_table_text = ""
        score_table = 0.0
        rows: List[Dict[str, Any]] = []
        try:
            cnpj = _extract_cnpj_from_raw(raw)
            ano = raw.get("anoCompra")
            seq = raw.get("sequencialCompra")
            should_fetch = cnpj and ano is not None and seq is not None
            if should_fetch and (PNCP_FETCH_ITEMS_ALWAYS or score_obj_bruto <= 0):
                async with sem:
                    lookup_coro = get_contract_items(cnpj, ano, seq, client=http_client)
                    if PNCP_ITEM_LOOKUP_TIMEOUT_SECONDS > 0:
                        rows = await asyncio.wait_for(lookup_coro, timeout=PNCP_ITEM_LOOKUP_TIMEOUT_SECONDS)
                    else:
                        rows = await lookup_coro
                item_table_text = _item_text_from_table_rows(rows)
                score_table = _compute_match_score(item_table_text, query_groups) if item_table_text else 0.0
        except Exception:
            # Não derruba busca por falha pontual na consulta de itens
            score_table = 0.0
            rows = []

        confirmado_itens: bool | None = None
        if rows and PNCP_REQUIRE_TABLE_MATCH_WHEN_ITENS_EXIST:
            tem_texto_linha = any(bool(_row_text_for_match(r).strip()) for r in rows)
            if not tem_texto_linha:
                # API devolveu linhas mas sem campos de descrição reconhecidos: não dá para
                # confirmar nem contradizer o termo na tabela — mantém o match pelo objeto.
                confirmado_itens = None
                score_obj = score_obj_bruto
            else:
                confirmado_itens = _table_supports_query(rows, query_groups)
                # Mantém sempre o score do objeto; confirmado_nos_itens só informa se a tabela
                # reforça o termo (evita lista vazia quando o PNCP omite o token nas linhas).
                score_obj = score_obj_bruto
        elif rows:
            confirmado_itens = _table_supports_query(rows, query_groups)
            score_obj = score_obj_bruto
        else:
            # Sem linhas na API: não dá para confirmar pelos itens; mantém score do objeto.
            confirmado_itens = None
            score_obj = score_obj_bruto

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

        itens_json, itens_modo, qtd_itens = _itens_destaque_e_amostra(
            rows, query_groups, score_obj_bruto
        )
        if score_obj_bruto > 0 and score_table > 0:
            match_origem = "objeto_e_tabela"
        elif score_table > 0 and score_obj_bruto <= 0:
            match_origem = "tabela_itens"
        else:
            match_origem = "objeto"

        return {
            "numero_pncp": raw.get("numeroControlePNCP"),
            "objeto_resumido": obj,
            "orgao": org.get("razaoSocial") or org.get("razaosocial"),
            "municipio": unid.get("municipioNome"),
            "uf": unid.get("ufSigla"),
            "modalidade": raw.get("modalidadeNome"),
            "data_publicacao": raw.get("dataPublicacaoPncp") or raw.get("dataInclusao") or raw.get("dataAtualizacao"),
            "valor_global": valor_f,
            "situacao": raw.get("situacaoCompraNome"),
            "ano_compra": raw.get("anoCompra"),
            "sequencial_compra": raw.get("sequencialCompra"),
            "score_relevancia": score,
            "score_objeto": round(score_obj, 4),
            "score_objeto_texto": round(score_obj_bruto, 4),
            "score_tabela_itens": round(score_table, 4),
            "match_origem": match_origem,
            "confirmado_nos_itens": confirmado_itens,
            "qtd_itens_pncp": qtd_itens,
            "itens_pncp_modo": itens_modo,
            "itens_pncp": itens_json,
        }

    # Até o teto da própria página PNCP (50); antes cortava em 30 e descartava resultado.
    page_slice = min(50, max(1, PNCP_ITEM_LOOKUP_PER_PAGE), len(raw_items))
    selected = raw_items[:page_slice]
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
    periodo_janelas = _pn_date_windows(data_inicial, data_final)
    query_groups = _build_query_groups(payload.termo_busca)
    modalidades = [payload.codigo_modalidade] if payload.codigo_modalidade is not None else PNCP_MODALIDADES_DEFAULT

    all_items: List[Dict[str, Any]] = []
    pages_processed = 0
    total_page_budget = max(1, payload.max_paginas)
    pages_per_modalidade = max(1, math.ceil(total_page_budget / max(1, len(modalidades))))
    min_batch_full = max(10, min(payload.tamanho_pagina, 50))

    async with create_pncp_http_client() as http:
        for janela_idx, (w_di, w_df) in enumerate(periodo_janelas):
            if pages_processed >= total_page_budget:
                break
            mod_state: Dict[int, Dict[str, Any]] = {
                int(m): {"page": payload.pagina, "exhausted": False, "fetched": 0} for m in modalidades
            }
            while pages_processed < total_page_budget:
                remaining = max(0, total_page_budget - pages_processed)
                to_fetch: List[int] = []
                for m in modalidades:
                    if len(to_fetch) >= remaining:
                        break
                    mi = int(m)
                    st = mod_state[mi]
                    if st["exhausted"] or st["fetched"] >= pages_per_modalidade:
                        continue
                    to_fetch.append(mi)

                if not to_fetch:
                    break

                search_tasks = [
                    search_contracts(
                        data_inicial=w_di,
                        data_final=w_df,
                        codigo_modalidade=mi,
                        uf=payload.uf,
                        codigo_municipio_ibge=payload.codigo_municipio_ibge,
                        pagina=mod_state[mi]["page"],
                        tamanho_pagina=payload.tamanho_pagina,
                        client=http,
                    )
                    for mi in to_fetch
                ]
                raw_batches = await asyncio.gather(*search_tasks, return_exceptions=True)
                batches: List[List[Dict[str, Any]]] = []
                for mi, r in zip(to_fetch, raw_batches):
                    if isinstance(r, Exception):
                        batches.append([])
                    else:
                        batches.append(list(r) if r else [])

                if PNCP_ENABLE_ITEM_TABLE_LOOKUP:
                    item_tasks = [
                        _extract_matching_items_with_table_lookup(b or [], query_groups, http_client=http)
                        for b in batches
                    ]
                    page_items_list: List[List[Dict[str, Any]]] = await asyncio.gather(*item_tasks)
                else:
                    page_items_list = [_extract_matching_items(b or [], query_groups) for b in batches]

                for mi, batch, page_items in zip(to_fetch, batches, page_items_list):
                    st = mod_state[mi]
                    page_num = st["page"]
                    st["page"] = page_num + 1
                    st["fetched"] += 1
                    pages_processed += 1

                    all_items.extend(page_items)
                    if PNCP_LOCAL_AUTO_INGEST and batch:
                        try:
                            upsert_contracts(batch)
                        except Exception:
                            # Falha no cache local não deve interromper a busca online.
                            pass

                    ev: Dict[str, Any] = {
                        "type": "page",
                        "modalidade": mi,
                        "page": page_num,
                        "raw_count": len(batch or []),
                        "matched_count": len(page_items),
                        "items": page_items,
                    }
                    if len(periodo_janelas) > 1:
                        ev["periodo_janela"] = janela_idx + 1
                        ev["data_inicial_janela"] = w_di
                        ev["data_final_janela"] = w_df
                    yield ev

                    if not batch or len(batch) < min_batch_full:
                        st["exhausted"] = True

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
            "periodo_particionado_pncp_365d": len(periodo_janelas) > 1,
            "periodo_janelas": [{"inicio": a, "fim": b} for a, b in periodo_janelas],
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


def _parse_any_date(v: Any) -> Optional[datetime]:
    s = str(v or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y%m%d"):
        try:
            return datetime.strptime(s[: len(fmt)], fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _score_recency(item: Dict[str, Any]) -> float:
    dt = _parse_any_date(item.get("data_publicacao"))
    if not dt:
        return 6.0
    days = max(0, (datetime.utcnow() - dt.replace(tzinfo=None)).days)
    if days <= 90:
        return 15.0
    if days <= 180:
        return 12.0
    if days <= 365:
        return 8.0
    return 4.0


def _score_value_coherence(item: Dict[str, Any], median_val: Optional[float]) -> float:
    if not median_val or median_val <= 0:
        return 8.0
    v = item.get("valor_unitario") or item.get("valor_total") or item.get("valor_global")
    try:
        f = float(v)
    except Exception:
        return 4.0
    if f <= 0:
        return 2.0
    dev = abs(f - median_val) / median_val
    if dev <= 0.2:
        return 15.0
    if dev <= 0.4:
        return 9.0
    return 4.0


def _score_clarity_and_unit(item: Dict[str, Any], query_groups: List[List[str]]) -> float:
    """
    Penaliza itens "lote/kit/diversos" e favorece descrições diretas e unidades razoáveis.
    """
    desc = str(item.get("descricao_item") or "").lower()
    mat = str(item.get("material_servico") or "").lower()
    full = f"{desc} {mat}"
    text_norm = _normalize_text(full)

    # Muito texto geralmente indica descrição de lote com vários itens.
    word_count = len(text_norm.split())
    if word_count > 80:
        return 0.0

    # Penaliza palavras típicas de lote/kit/misturado.
    bad_tokens = ["lote", "itens diversos", "diversos materiais", "kit ", "conjunto ", "varios itens"]
    for tok in bad_tokens:
        if tok.strip() and tok in full:
            return 1.0

    # Requer casamento explícito de todos tokens principais da consulta
    # (ex.: "parafuso" e "aco") quando vierem no termo.
    if query_groups:
        hits = 0
        needed = 0
        words = set(text_norm.split())
        for group in query_groups:
            for tok in group:
                needed += 1
                if tok in words:
                    hits += 1
        if needed and hits / needed < 0.6:
            return 0.0

    # Heurística de unidade / quantidade.
    qtd = item.get("quantidade")
    um = str(item.get("unidade_medida") or "").upper()
    try:
        qtd_f = float(qtd) if qtd is not None else None
    except Exception:
        qtd_f = None

    score = 6.0
    if um in {"UN", "UND", "UNID", "UNIDADE", "PC", "PÇ"}:
        score += 4.0
    if qtd_f is not None:
        if 0 < qtd_f <= 10_000:
            score += 3.0
        elif qtd_f > 100_000:
            score -= 2.0
    return max(0.0, min(15.0, score))


def _score_semantic(item: Dict[str, Any]) -> float:
    raw = item.get("score_relevancia")
    try:
        f = float(raw)
    except Exception:
        return 0.0
    if math.isnan(f) or math.isinf(f) or f <= 0:
        return 0.0
    # score_relevancia costuma variar pouco; cap para normalização estável.
    return min(55.0, (min(f, 3.0) / 3.0) * 55.0)


def _score_table_confirmation(item: Dict[str, Any]) -> float:
    c = item.get("confirmado_nos_itens")
    if c is True:
        return 15.0
    if c is False:
        return 3.0
    return 8.0


def _classify_confiabilidade(score: float) -> str:
    if score >= 75:
        return "Alta"
    if score >= 55:
        return "Média"
    return "Baixa"


def _classify_risco(score: float) -> str:
    if score >= 75:
        return "Baixo"
    if score >= 55:
        return "Médio"
    return "Alto"


def _select_top3_with_diversity(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    used_org: set[str] = set()
    for it in items:
        org = str(it.get("orgao") or "").strip().lower()
        if org and org not in used_org:
            selected.append(it)
            used_org.add(org)
        if len(selected) >= 3:
            return selected[:3]
    for it in items:
        if it in selected:
            continue
        selected.append(it)
        if len(selected) >= 3:
            break
    return selected[:3]


async def market_search_intelligent(payload: MarketSearchRequest) -> Dict[str, Any]:
    """
    Versão inteligente da busca manual:
    - usa o mesmo índice local de itens PNCP (local_item_search);
    - aplica score 0-100 por item;
    - retorna exatamente 3 cotações com diversidade de órgão.
    """
    # Reutiliza a mesma fonte da busca manual (itens PNCP normalizados)
    limit = max(50, payload.max_paginas * payload.tamanho_pagina)
    base_items = local_item_search(
        payload.termo_busca,
        uf=payload.uf,
        codigo_modalidade=payload.codigo_modalidade,
        limit=limit,
    )
    itens = list(base_items.get("itens") or [])
    if not itens:
        return {
            "ok": True,
            "filtros": {
                "termo_busca": payload.termo_busca,
                "uf": payload.uf,
                "codigo_municipio_ibge": payload.codigo_municipio_ibge,
                "codigo_modalidade": payload.codigo_modalidade,
                "pagina_inicial": payload.pagina,
                "max_paginas": payload.max_paginas,
                "tamanho_pagina": payload.tamanho_pagina,
                "fonte": "local_item_search",
            },
            "stats": base_items.get("stats", {}),
            "itens": [],
        }

    query_groups = _build_query_groups(payload.termo_busca)
    valores = [
        x.get("valor_unitario") or x.get("valor_total") or x.get("valor_global")
        for x in itens
        if isinstance((x.get("valor_unitario") or x.get("valor_total") or x.get("valor_global")), (int, float))
        and (x.get("valor_unitario") or x.get("valor_total") or x.get("valor_global") or 0) > 0
    ]
    median_val = median(valores) if valores else None

    scored: List[Dict[str, Any]] = []
    # Primeiro passa: filtra obviamente ruins (sem texto/valor) e calcula scores.
    for it in itens:
        texto_item = f"{it.get('descricao_item') or ''} {it.get('material_servico') or ''}".strip()
        sem_raw = _compute_match_score(texto_item, query_groups) if query_groups else 0.0
        sem = min(55.0, (min(sem_raw, 3.0) / 3.0) * 55.0) if sem_raw > 0 else 0.0
        if sem <= 0:
            # Nem bate semanticamente com o termo principal.
            continue
        tbl = 8.0  # neutro (sem tabela de itens aqui).
        rec = _score_recency(it)
        coh = _score_value_coherence(it, median_val)
        clar = _score_clarity_and_unit(it, query_groups)
        score_0_100 = max(0, min(100, round(sem + tbl + rec + coh + clar)))
        it2 = dict(it)
        it2["score_aprovacao"] = score_0_100
        it2["confiabilidade"] = _classify_confiabilidade(score_0_100)
        it2["risco"] = _classify_risco(score_0_100)
        it2["status"] = "Aprovado" if score_0_100 >= 55 else "Revisar"
        scored.append(it2)

    scored.sort(
        key=lambda x: (
            float(x.get("score_aprovacao") or 0),
            float(x.get("valor_unitario") or x.get("valor_total") or 0),
        ),
        reverse=True,
    )
    top3 = _select_top3_with_diversity(scored)[:3]

    out_stats = dict(base_items.get("stats") or {})
    out_stats["total_registros_ia"] = len(scored)
    out_stats["total_selecionados_ia"] = len(top3)
    out_stats["regra_selecao"] = "top3_com_diversidade_orgao"

    return {
        "ok": bool(base_items.get("ok", True)),
        "filtros": {
            "termo_busca": payload.termo_busca,
            "uf": payload.uf,
            "codigo_municipio_ibge": payload.codigo_municipio_ibge,
            "codigo_modalidade": payload.codigo_modalidade,
            "pagina_inicial": payload.pagina,
            "max_paginas": payload.max_paginas,
            "tamanho_pagina": payload.tamanho_pagina,
            "fonte": "local_item_search",
        },
        "stats": out_stats,
        "itens": top3,
    }
