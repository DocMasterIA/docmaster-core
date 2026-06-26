from __future__ import annotations

from datetime import date, datetime, timedelta
from statistics import mean, median
from typing import Any, Dict, List, Optional
import json
import re
import unicodedata
import math
import asyncio
from difflib import SequenceMatcher

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
    PNCP_HYBRID_FALLBACK_ENABLED,
    PNCP_HYBRID_BULK_ENABLED,
    PNCP_HYBRID_MAX_LIVE_PAGES,
    PNCP_HYBRID_MIN_LOCAL_RESULTS,
    PNCP_BULK_MAX_TERM_FALLBACKS,
    PNCP_BULK_SEARCH_MAX_SECONDS,
    PNCP_BULK_ENRICH_HOMOLOG_MAX,
    PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX,
    PNCP_LOCAL_AUTO_INGEST,
    PNCP_IA_RERANK_ENABLED,
    PNCP_LOCAL_RERANK_ENABLED,
    PNCP_LOCAL_RERANK_MAX_CANDIDATES,
    PNCP_LOCAL_RERANK_ONLY_AMBIGUOUS,
    PNCP_IA_RERANK_PREFER_LOCAL,
    PNCP_IA_RERANK_BULK_ENABLED,
    PNCP_IA_BULK_MAX_CANDIDATES,
    PNCP_IA_BULK_TIMEOUT_SECONDS,
    PNCP_IA_RERANK_BULK_ONLY_AMBIGUOUS,
    PNCP_IA_BASE_URL,
    PNCP_IA_GENERATE_PATH,
    PNCP_IA_MODEL,
    PNCP_IA_TIMEOUT_SECONDS,
    PNCP_IA_MAX_CANDIDATES,
    PNCP_IA_ITEM_RESUMO_ENABLED,
    PNCP_IA_ITEM_RESUMO_TIMEOUT_SECONDS,
    PNCP_BLOCK_SERVICE_ITEMS,
    PNCP_SERVICE_BLOCK_TERMS,
    PNCP_SEARCH_ENRICH_HOMOLOG_MAX,
    PNCP_SEARCH_MIN_SCORE_APROVACAO,
    PNCP_SEARCH_QUALITY_FIRST,
    PNCP_SEARCH_MAX_SIMILAR_IN_TOP3,
    PNCP_IA_RERANK_MIXED_POOL,
    PNCP_BULK_SEARCH_SQL_LIMIT,
)
from .pncp_client import (
    PNCPClientError,
    create_pncp_http_client,
    search_contracts,
    get_contract_items,
    get_contract_supplier_snapshot,
)
from .local_index import (
    _build_search_tokens,
    build_search_query_tiers,
    derive_anchor_search_term,
    enrich_homolog_items_from_pncp,
    upsert_contracts,
    local_item_search,
)
from .schemas import MarketSearchRequest
from .search_text_clean import apply_item_display_cleanup, normalize_for_search, preprocess_cotacao_search_term
from .pricing_display import (
    filter_items_for_search_display,
    row_display_unit_price,
)
from .pricing_faixa import (
    compute_faixa_regional,
    faixa_regional_ativa,
    format_faixa_prompt_text,
    normalize_variacao_sentido,
)


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
    """Texto normalizado para matching (acentos, ruído, nº, números por extenso comuns)."""
    return normalize_for_search(text or "")


_SERVICE_BLOCK_TERMS_NORM = tuple(
    _normalize_text(t) for t in (PNCP_SERVICE_BLOCK_TERMS or []) if str(t).strip()
)


def _is_service_like_item(item: Dict[str, Any]) -> bool:
    """
    Bloqueio duro para itens de prestação de serviço/locação.
    """
    if not PNCP_BLOCK_SERVICE_ITEMS:
        return False
    if not _SERVICE_BLOCK_TERMS_NORM:
        return False
    text = _normalize_text(
        " ".join(
            [
                str(item.get("descricao_item") or ""),
                str(item.get("material_servico") or ""),
                str(item.get("objeto_resumido") or ""),
                str(item.get("objetoCompra") or ""),
                str(item.get("objeto") or ""),
                str(item.get("descricao") or ""),
                str(item.get("modalidade") or ""),
            ]
        )
    )
    if not text:
        return False
    return any(term in text for term in _SERVICE_BLOCK_TERMS_NORM)


def _normalize_esfera_id(v: Any) -> str:
    s = str(v or "").strip().upper()
    if s in {"F", "E", "M", "D"}:
        return s
    return ""


def _esfera_label(esfera_id: str) -> str:
    if esfera_id == "F":
        return "federal"
    if esfera_id == "E":
        return "estadual"
    if esfera_id == "M":
        return "municipal"
    if esfera_id == "D":
        return "distrital"
    return "nao_definida"


def _extract_esfera_meta(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Extrai esfera/poder com prioridade em campos oficiais do PNCP."""
    org = raw.get("orgaoEntidade") or {}
    sub = raw.get("orgaoSubRogado") or {}
    unidade = raw.get("unidadeOrgao") or {}
    esfera_org = _normalize_esfera_id(org.get("esferaId") or org.get("esfera_id"))
    esfera_sub = _normalize_esfera_id(sub.get("esferaId") or sub.get("esfera_id"))
    esfera_id = esfera_org or esfera_sub
    poder_id = str(org.get("poderId") or sub.get("poderId") or "").strip().upper()
    return {
        "esfera_id": esfera_id or None,
        "esfera_administrativa": _esfera_label(esfera_id),
        "esfera_fonte": "orgao_entidade.esferaId" if esfera_org else ("orgao_sub_rogado.esferaId" if esfera_sub else "nao_informada"),
        "poder_id": poder_id or None,
        "orgao_cnpj": str(org.get("cnpj") or org.get("cnpjOrgaoEntidade") or "").strip() or None,
        "codigo_unidade_administrativa": str(unidade.get("codigoUnidade") or unidade.get("codigoUnidadeAdministrativa") or "").strip() or None,
    }


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


def _compute_match_score(
    text: str,
    query_groups: List[List[str]],
    *,
    variant_groups: bool = False,
) -> float:
    """
    Score de relevância + regra de precisão:
    - precisa casar ao menos 1 token de CADA grupo (AND entre grupos)
    - score favorece maior cobertura e frase completa do grupo.

    ``variant_groups=True``: grupos vindos de ``_build_search_tokens`` (singular/plural
    do mesmo termo) — basta 1 variante por grupo (OR intra-grupo).
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
        if variant_groups:
            required_hits = 1
        elif len(group) == 1:
            required_hits = 1
        elif len(group) == 2:
            required_hits = 2
        elif len(group) == 3:
            required_hits = 2
        else:
            required_hits = max(2, math.ceil(len(group) * 0.5))

        if hits < required_hits:
            return 0.0  # sem cobertura mínima de um grupo -> descarta

        coverage = hits / max(1, len(group)) if not variant_groups else (1.0 if hits else 0.0)
        group_phrase = " ".join(group)
        phrase_bonus = 0.5 if group_phrase and group_phrase in normalized_text else 0.0
        total_score += coverage + phrase_bonus

    return round(total_score, 4)


def _extract_matching_items(raw_items: List[Dict[str, Any]], query_groups: List[List[str]]) -> List[Dict[str, Any]]:
    """Transforma payload bruto do PNCP em itens filtrados/rankeados."""
    matched: List[Dict[str, Any]] = []
    for raw in raw_items:
        if _is_service_like_item(raw):
            continue
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
                **_extract_esfera_meta(raw),
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


def _numero_item_from_best_matching_row(
    rows: List[Dict[str, Any]],
    query_groups: List[List[str]],
) -> str:
    """Número do item PNCP cuja descrição melhor casa com o termo (para fornecedor por linha)."""
    best_score = 0.0
    best_num = ""
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        line = _row_text_for_match(r)
        if not line:
            continue
        sc = _compute_match_score(line, query_groups)
        if sc > best_score:
            best_score = sc
            best_num = str(
                r.get("numeroItem") or r.get("ordemItem") or r.get("sequencialItem") or ""
            ).strip()
    return best_num


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
        if _is_service_like_item(raw):
            return None
        obj = _objeto_compra_text(raw)
        score_obj_bruto = _compute_match_score(obj, query_groups)

        item_table_text = ""
        score_table = 0.0
        rows: List[Dict[str, Any]] = []
        fornecedor_nome = ""
        fornecedor_cnpj = ""
        fornecedor_cadastro: Dict[str, Any] = {}
        fornecedor_fonte_nome = ""
        try:
            cnpj = _extract_cnpj_from_raw(raw)
            ano = raw.get("anoCompra")
            seq = raw.get("sequencialCompra")
            should_fetch = cnpj and ano is not None and seq is not None
            if should_fetch:
                async with sem:
                    if PNCP_FETCH_ITEMS_ALWAYS or score_obj_bruto <= 0:
                        lookup_coro = get_contract_items(cnpj, ano, seq, client=http_client)
                        if PNCP_ITEM_LOOKUP_TIMEOUT_SECONDS > 0:
                            rows = await asyncio.wait_for(lookup_coro, timeout=PNCP_ITEM_LOOKUP_TIMEOUT_SECONDS)
                        else:
                            rows = await lookup_coro
                    numero_item_forn = ""
                    if rows:
                        numero_item_forn = _numero_item_from_best_matching_row(rows, query_groups)
                    fornecedor_coro = get_contract_supplier_snapshot(
                        cnpj,
                        ano,
                        seq,
                        numero_item=numero_item_forn or None,
                        situacao_compra=raw.get("situacaoCompraNome"),
                        client=http_client,
                    )
                    try:
                        fornecedor_data = await asyncio.wait_for(
                            fornecedor_coro,
                            timeout=max(2.0, float(PNCP_ITEM_LOOKUP_TIMEOUT_SECONDS or 0)),
                        )
                    except Exception:
                        fornecedor_data = {}
                    fornecedor_nome = str((fornecedor_data or {}).get("fornecedor") or "").strip()
                    fornecedor_cnpj = str((fornecedor_data or {}).get("cnpj_fornecedor") or "").strip()
                    fornecedor_cadastro = (fornecedor_data or {}).get("fornecedor_cadastro")
                    if not isinstance(fornecedor_cadastro, dict):
                        fornecedor_cadastro = {}
                    fornecedor_fonte_nome = str((fornecedor_data or {}).get("fornecedor_fonte_nome") or "").strip()
                item_table_text = _item_text_from_table_rows(rows)
                score_table = _compute_match_score(item_table_text, query_groups) if item_table_text else 0.0
        except Exception:
            # Não derruba busca por falha pontual na consulta de itens
            score_table = 0.0
            rows = []
            fornecedor_cadastro = {}
            fornecedor_fonte_nome = ""

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
            "fornecedor": fornecedor_nome,
            "cnpj_fornecedor": fornecedor_cnpj,
            "fornecedor_cadastro": fornecedor_cadastro,
            "fornecedor_fonte_nome": fornecedor_fonte_nome,
            **_extract_esfera_meta(raw),
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

    # Penaliza palavras típicas de lote/kit/misturado ou itens onde o alvo é só detalhe.
    bad_tokens = [
        "lote",
        "itens diversos",
        "diversos materiais",
        "kit ",
        "conjunto ",
        "varios itens",
        "cadeira",
        "longarina",
        "placa de regulamentacao",
        "placas de regulamentacao",
    ]
    for tok in bad_tokens:
        if tok.strip() and tok in full:
            return 0.5

    # Requer casamento explícito dos tokens principais da consulta (1 hit por grupo).
    main_query_tokens: set[str] = set()
    if query_groups:
        hits = 0
        needed = 0
        words = set(text_norm.split())
        for group in query_groups:
            needed += 1
            if any(tok in words for tok in group):
                hits += 1
            for tok in group:
                main_query_tokens.add(tok)
        if needed and hits / needed < 0.6:
            return 0.0

    score = 6.0

    # Heurística de unidade / quantidade.
    qtd = item.get("quantidade")
    um = str(item.get("unidade_medida") or "").upper()
    try:
        qtd_f = float(qtd) if qtd is not None else None
    except Exception:
        qtd_f = None

    if um in {"UN", "UND", "UNID", "UNIDADE", "PC", "PÇ"}:
        score += 4.0
    if qtd_f is not None:
        if 0 < qtd_f <= 10_000:
            score += 3.0
        elif qtd_f > 100_000:
            score -= 2.0
    return max(0.0, min(15.0, score))


def _normalize_unit(value: Any) -> str:
    s = _normalize_text(str(value or ""))
    if not s:
        return ""
    unit_map = {
        "unidade": "un",
        "unid": "un",
        "und": "un",
        "un": "un",
        "peca": "pc",
        "pecas": "pc",
        "pc": "pc",
        "kg": "kg",
        "quilo": "kg",
        "quilograma": "kg",
        "g": "g",
        "grama": "g",
        "l": "l",
        "lt": "l",
        "litro": "l",
        "m": "m",
        "metro": "m",
        "m2": "m2",
        "metro quadrado": "m2",
    }
    return unit_map.get(s, s)


def _literal_query_tokens(termo_busca: str) -> List[str]:
    """
    Tokens literais do termo de busca (sem stopwords genéricas).
    Mantém ordem para montar frases contíguas.
    """
    stop = {
        "de", "da", "do", "das", "dos", "para", "com", "sem", "em", "no", "na", "nos", "nas",
        "por", "e", "ou", "a", "o", "as", "os", "um", "uma", "uns", "umas",
    }
    norm = _normalize_text(termo_busca)
    if not norm:
        return []
    return [t for t in norm.split() if len(t) >= 2 and t not in stop]


def _literal_match_score(termo_busca: str, item: Dict[str, Any]) -> float:
    """
    Prioriza correspondência quase literal ao texto pesquisado.
    Não depende de domínio específico: usa apenas o termo + descrição/material.
    """
    toks = _literal_query_tokens(termo_busca)
    if not toks:
        return 0.0
    desc_raw = str(item.get("descricao_item") or "")
    mat_raw = str(item.get("material_servico") or "")
    haystack_norm = _normalize_text(f"{desc_raw} {mat_raw}")
    haystack_compact = haystack_norm.replace(" ", "")
    if not haystack_norm:
        return 0.0

    # Frase compacta do termo (ex.: "parafuso de aço" -> "parafuso aco")
    phrase_compact = "".join(toks)
    phrase_spaced = " ".join(toks)

    score = 0.0
    if phrase_compact and phrase_compact in haystack_compact:
        score += 55.0
    elif phrase_spaced and phrase_spaced in haystack_norm:
        score += 48.0
    else:
        words = haystack_norm.split()
        if not words:
            return 0.0

        def _stem_ok(w: str, t: str) -> bool:
            return w == t or w.startswith(t) or t.startswith(w[: max(1, min(4, len(w))) ])

        # Tokens na ordem, permitindo “ruído” entre eles (típico PNCP: rótulos, pontuação virando espaço).
        idxs: List[int] = []
        cursor = 0
        max_gap = 10 if len(toks) <= 2 else 14
        for t in toks:
            found_at: Optional[int] = None
            start = cursor
            end = min(len(words), cursor + max_gap + 1)
            for j in range(start, end):
                if _stem_ok(words[j], t):
                    found_at = j
                    break
            if found_at is None:
                idxs = []
                break
            idxs.append(found_at)
            cursor = found_at + 1

        if len(idxs) == len(toks) and idxs:
            span = idxs[-1] - idxs[0]
            tight = max(0.0, 1.0 - (span / 40.0))
            early = max(0.0, 1.0 - (idxs[0] / 25.0))
            score += 22.0 + 34.0 * tight + 10.0 * early
        else:
            hits = sum(1 for t in toks if any(_stem_ok(w, t) for w in words))
            score += 14.0 * (hits / max(1, len(toks)))

    # Bônus se o início da descrição segue a ordem dos tokens (objeto principal).
    words = haystack_norm.split()
    if words:
        pos = 0
        matched_in_order = 0
        for t in toks:
            found = False
            for j in range(pos, min(len(words), pos + 6)):
                w = words[j]
                if w == t or w.startswith(t) or t.startswith(w[: max(1, min(4, len(w))) ]):
                    pos = j + 1
                    matched_in_order += 1
                    found = True
                    break
            if not found:
                break
        if matched_in_order >= 2:
            score += 12.0 * (matched_in_order / max(1, len(toks)))

    # Penaliza serviço embutido só quando o usuário não pediu isso no termo.
    term_norm = _normalize_text(termo_busca)
    wants_service = any(
        k in term_norm
        for k in ("instal", "montag", "desmontag", "monta", "desmonta", "fornec", "execuc", "execu")
    )
    if not wants_service:
        if any(
            k in haystack_norm
            for k in ("instalacao", "montagem", "desmontagem", "fornecimento e instalacao", "fornecimento e montagem")
        ):
            score -= 10.0

    return max(0.0, min(80.0, score))


def _query_tokens(query_groups: List[List[str]]) -> set[str]:
    out: set[str] = set()
    for group in query_groups:
        for tok in group:
            t = _normalize_text(tok)
            if t:
                out.add(t)
    return out


def _query_phrase_tokens(query_groups: List[List[str]]) -> List[str]:
    """
    Retorna os tokens do primeiro grupo da consulta (núcleo da frase).
    Ex.: "parafuso de aço sextavado" -> ["parafuso", "aco", "sextavado"].
    """
    if not query_groups:
        return []
    first = [_normalize_text(t) for t in query_groups[0]]
    return [t for t in first if t]


def _is_strict_candidate_match(item: Dict[str, Any], query_groups: List[List[str]]) -> bool:
    """
    Purificação pesada para evitar falso positivo por menção lateral do termo.
    Ex.: "locação de tenda ... parafusos, conexões em aço" não deve passar para "parafuso de aço".
    """
    q_tokens = list(_query_tokens(query_groups))
    if len(q_tokens) < 2:
        # Para consulta curta (1 token), mantém filtro semântico padrão.
        return True

    # Descrições longas de cotação: exige proximidade só no núcleo (1º grupo), não em todos os tokens.
    if len(q_tokens) > 5:
        query_groups = query_groups[:1] if query_groups else query_groups
        q_tokens = list(_query_tokens(query_groups))
        if len(q_tokens) < 2:
            return True

    desc = _normalize_text(str(item.get("descricao_item") or ""))
    mat = _normalize_text(str(item.get("material_servico") or ""))
    if not desc and not mat:
        return False
    full = f"{desc} {mat}".strip()
    words = full.split()
    if not words:
        return False

    token_positions: Dict[str, List[int]] = {t: [] for t in q_tokens}
    for idx, w in enumerate(words):
        for t in q_tokens:
            if w == t or w.startswith(t) or t.startswith(w[: max(1, min(4, len(w))) ]):
                token_positions[t].append(idx)

    # Todos os tokens-chave devem aparecer.
    if any(len(token_positions[t]) == 0 for t in q_tokens):
        return False

    # Tokens-chave devem aparecer perto entre si (janela curta).
    min_pos = min(min(v) for v in token_positions.values())
    max_pos = max(min(v) for v in token_positions.values())
    if (max_pos - min_pos) > 10:
        return False

    # O núcleo do termo deve surgir cedo no texto, não no fim de uma descrição gigante.
    if min_pos > 20:
        return False

    # Regra genérica: os tokens do núcleo da frase devem aparecer cedo e próximos.
    phrase_tokens = _query_phrase_tokens(query_groups)
    if len(phrase_tokens) >= 2:
        lead_window = words[:20]
        lead_hits = sum(
            1
            for tok in phrase_tokens
            if any((w == tok) or w.startswith(tok) or tok.startswith(w[: max(1, min(4, len(w)))]) for w in lead_window)
        )
        if lead_hits < max(2, math.ceil(len(phrase_tokens) * 0.7)):
            return False

    # Bloqueia contextos típicos onde o termo aparece só como componente secundário.
    secondary_context = (
        "locacao", "tenda", "cadeira", "longarina", "placa", "manutencao", "servico",
        "instalacao", "montagem", "desmontagem", "estrutura", "lona", "evento",
        "cinta", "abracadeira", "poste", "suporte",
    )
    secondary_hits = sum(1 for s in secondary_context if s in full)
    if secondary_hits >= 2 and min_pos > 6:
        return False

    return True


def _context_penalty(item: Dict[str, Any], query_groups: List[List[str]]) -> float:
    """
    Penaliza contexto incompatível com o termo pesquisado.
    Exemplo genérico: consulta de item de ferragem retornando item de implante médico.
    """
    desc = _normalize_text(str(item.get("descricao_item") or ""))
    mat = _normalize_text(str(item.get("material_servico") or ""))
    full = f"{desc} {mat}".strip()
    if not full:
        return -8.0

    q_tokens = _query_tokens(query_groups)
    query_is_medical = any(
        t in q_tokens
        for t in {
            "hospitalar",
            "medico",
            "medica",
            "medic",
            "ortopedico",
            "ortopedica",
            "implante",
            "protese",
            "anvisa",
            "canulado",
            "osseo",
        }
    )
    if not query_is_medical:
        medical_hits = 0
        for tok in (
            "osseo",
            "ortoped",
            "anvisa",
            "titani",
            "implante",
            "protese",
            "hospital",
            "canulad",
            "mao",
            "pe",
        ):
            if tok in full:
                medical_hits += 1
        if medical_hits >= 2:
            return -24.0
        if medical_hits == 1:
            return -10.0

    # Penaliza descrições muito longas e pouco objetivas.
    if len(full.split()) > 70:
        return -8.0
    if len(full.split()) > 45:
        return -4.0
    return 0.0


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
    min_ok = int(PNCP_SEARCH_MIN_SCORE_APROVACAO)
    if score >= 80:
        return "Alta"
    if score >= min_ok:
        return "Média"
    return "Baixa"


def _classify_risco(score: float) -> str:
    min_ok = int(PNCP_SEARCH_MIN_SCORE_APROVACAO)
    if score >= 80:
        return "Baixo"
    if score >= min_ok:
        return "Médio"
    return "Alto"


def _is_similaridade_encontrada(item: Dict[str, Any]) -> bool:
    """
    Marca match por similaridade quando a aderência semântica é boa,
    mas o encaixe literal com o termo buscado é baixo.
    """
    if bool(item.get("partial_anchor_match")):
        return True
    literal = _safe_float(item.get("literal_match"))
    aprov = _safe_float(item.get("score_aprovacao"))
    sem_raw = _safe_float(item.get("score_relevancia"))
    # Preserva match vanilla quando o literal está forte o bastante.
    if literal >= 30:
        return False
    # `score_relevancia` > 0 indica match semântico básico; score aprovado evita ruído.
    # Para evitar excesso de "similaridade", limita aos casos de aderência literal realmente baixa.
    return bool(sem_raw > 0 and aprov >= int(PNCP_SEARCH_MIN_SCORE_APROVACAO) and literal < 30)


def _word_like_match(word: str, token: str) -> bool:
    if not word or not token:
        return False
    if word == token:
        return True
    if len(token) >= 4 and word.startswith(token):
        return True
    if len(word) >= 4 and token.startswith(word[:4]):
        return True
    return False


def _has_core_token_overlap(item: Dict[str, Any], query_groups: List[List[str]], min_hits: int = 2) -> bool:
    """
    Fallback semântico: exige pelo menos sobreposição mínima de tokens centrais
    para evitar matches genéricos demais.
    """
    q_tokens = [t for t in _query_phrase_tokens(query_groups) if t]
    if not q_tokens:
        q_tokens = sorted(_query_tokens(query_groups))
    if not q_tokens:
        return False
    text = _normalize_text(
        f"{item.get('descricao_item') or ''} {item.get('material_servico') or ''}"
    )
    words = [w for w in text.split() if w]
    if not words:
        return False
    hits = 0
    for tok in q_tokens:
        if any(_word_like_match(w, tok) for w in words):
            hits += 1
    required = max(1, min(min_hits, len(q_tokens)))
    return hits >= required


def _is_spec_token(tok: str) -> bool:
    t = str(tok or "").strip().lower()
    if not t:
        return False
    # Ex.: 250ml, 500mg, 1l, 2kg, 10cm, 20mm, 30un, 50cp, 100ui.
    return bool(
        re.search(r"\d", t)
        and re.search(r"(ml|mg|g|kg|l|lt|mcg|ui|mm|cm|m|un|und|cp|caps|comprim|amp|fr)$", t)
    )


def _has_partial_anchor_match(item: Dict[str, Any], query_groups: List[List[str]]) -> bool:
    """
    Similaridade parcial literal:
    - exige 1 token textual forte do núcleo (ex.: "remedio"/nome principal)
    - e 1 token de especificação/presentação (ex.: "250ml", "500mg")
    """
    q_tokens = [t for t in _query_phrase_tokens(query_groups) if t]
    if not q_tokens:
        q_tokens = sorted(_query_tokens(query_groups))
    if not q_tokens:
        return False

    text = _normalize_text(f"{item.get('descricao_item') or ''} {item.get('material_servico') or ''}")
    words = [w for w in text.split() if w]
    if not words:
        return False

    spec_tokens = [t for t in q_tokens if _is_spec_token(t)]
    core_tokens = [t for t in q_tokens if not re.search(r"\d", t) and len(t) >= 4]
    if not core_tokens:
        core_tokens = [t for t in q_tokens if len(t) >= 3]

    core_hit = any(any(_word_like_match(w, tok) for w in words) for tok in core_tokens)
    if not core_hit:
        return False

    if spec_tokens:
        return any(any(_word_like_match(w, tok) for w in words) for tok in spec_tokens)

    # Sem token de especificação: exige pelo menos 2 tokens do núcleo.
    core_hits = 0
    for tok in core_tokens:
        if any(_word_like_match(w, tok) for w in words):
            core_hits += 1
    return core_hits >= min(2, len(core_tokens))


def _aggressive_similarity_score(termo_busca: str, item: Dict[str, Any]) -> float:
    """
    Similaridade textual agressiva (0..1) entre o termo e descrição/material.
    """
    q = _normalize_text(termo_busca)
    d = _normalize_text(str(item.get("descricao_item") or ""))
    m = _normalize_text(str(item.get("material_servico") or ""))
    text = f"{d} {m}".strip()
    if not q or not text:
        return 0.0
    ratios = [
        SequenceMatcher(None, q, d).ratio() if d else 0.0,
        SequenceMatcher(None, q, m).ratio() if m else 0.0,
        SequenceMatcher(None, q, text).ratio(),
    ]
    q_toks = [t for t in q.split() if len(t) >= 3]
    words = [w for w in text.split() if len(w) >= 3]
    hit = 0
    for qt in q_toks:
        if any(_word_like_match(w, qt) for w in words):
            hit += 1
    token_cov = (hit / max(1, len(q_toks))) if q_toks else 0.0
    return max(max(ratios), token_cov)


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


def _select_top3_quality_first(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Prioriza qualidade: Alta -> Média -> Baixa.
    Itens de baixa qualidade só entram se não houver itens melhores suficientes.
    """
    if not items:
        return []

    def score_of(it: Dict[str, Any]) -> int:
        return int(max(0, min(100, _safe_float(it.get("score_aprovacao")))))

    min_ok = int(PNCP_SEARCH_MIN_SCORE_APROVACAO)
    high = [it for it in items if score_of(it) >= 80]
    medium = [it for it in items if min_ok <= score_of(it) < 80]
    low = [it for it in items if score_of(it) < min_ok]

    selected: List[Dict[str, Any]] = []
    for bucket in (high, medium, low):
        if len(selected) >= 3:
            break
        if not bucket:
            continue
        federal = [it for it in bucket if str(it.get("esfera_id") or "").strip().upper() == "F"]
        outros = [it for it in bucket if str(it.get("esfera_id") or "").strip().upper() != "F"]
        federal.sort(
            key=lambda it: (float(it.get("literal_match") or 0), score_of(it)),
            reverse=True,
        )
        outros.sort(
            key=lambda it: (float(it.get("literal_match") or 0), score_of(it)),
            reverse=True,
        )
        ordered_bucket = federal + outros
        already = {id(x) for x in selected}
        rest = [x for x in ordered_bucket if id(x) not in already]
        picks = _select_top3_with_diversity(rest)
        for p in picks:
            if len(selected) >= 3:
                break
            if any(p is s for s in selected):
                continue
            selected.append(p)
    return selected[:3]


def _is_federal_item(it: Dict[str, Any]) -> bool:
    esfera_id = str(it.get("esfera_id") or "").strip().upper()
    esfera_adm = _normalize_text(str(it.get("esfera_administrativa") or ""))
    return esfera_id == "F" or esfera_adm == "federal"


def _select_top3_prioritize_federal(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Regra de negócio:
    1) Se houver ao menos 3 federais com score >= 80, seleciona apenas federais;
    2) Caso contrário, seleção geral por qualidade (mescla I/II quando necessário).
    3) Se a regra federal deixar menos de 3, completa com demais esferas (até 3).
    """
    if not items:
        return []

    def _complete_to_three(selected: List[Dict[str, Any]], pool: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(selected) >= 3:
            return selected[:3]
        used = {_ia_item_key(x) for x in selected if _ia_item_key(x)}
        extras = _select_top3_quality_first([x for x in pool if _ia_item_key(x) not in used])
        out = list(selected)
        for row in extras:
            if len(out) >= 3:
                break
            k = _ia_item_key(row)
            if k and k in used:
                continue
            out.append(row)
            if k:
                used.add(k)
        return out[:3]

    federais = [it for it in items if _is_federal_item(it)]
    federais_80 = [it for it in federais if _safe_float(it.get("score_aprovacao")) >= 80.0]

    # Priorização total de Inciso I só quando há 3 federais "fortes" (>=80).
    if len(federais_80) >= 3:
        selected_federal = _select_top3_quality_first(federais)
        return _complete_to_three(selected_federal, items)

    # Sem 3 federais fortes, usa ranking geral (pode cair em II ou mesclar I/II).
    selected_all = _select_top3_quality_first(items)
    return selected_all[:3]


def _merge_unique_items(primary: List[Dict[str, Any]], secondary: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Junta listas preservando ordem e evitando duplicados do mesmo item PNCP.
    """
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()

    def key_of(it: Dict[str, Any]) -> str:
        return "|".join(
            [
                str(it.get("numero_pncp") or "").strip(),
                str(it.get("numero_item") or "").strip(),
                str(it.get("descricao_item") or "").strip().lower(),
                str(it.get("orgao") or "").strip().lower(),
            ]
        )

    for arr in (primary, secondary):
        for row in arr:
            k = key_of(row)
            if not k:
                continue
            if k in seen:
                continue
            seen.add(k)
            out.append(row)
    return out


def _safe_float(value: Any) -> float:
    try:
        out = float(value)
    except Exception:
        return 0.0
    if math.isnan(out) or math.isinf(out):
        return 0.0
    return out


def _row_price_for_faixa(it: Dict[str, Any]) -> float:
    return row_display_unit_price(it)


def _iter_search_term_fallbacks(termo_busca: str) -> List[str]:
    """
    Termos alternativos alinhados à busca manual (prefixos / núcleo / âncora).
    """
    raw = (termo_busca or "").strip()
    if not raw:
        return []
    out: List[str] = []
    seen: set[str] = set()

    def push(t: str) -> None:
        s = (t or "").strip()
        if len(s) < 4:
            return
        key = s.lower()
        if key in seen:
            return
        seen.add(key)
        out.append(s)

    push(raw)
    push(preprocess_cotacao_search_term(raw) or raw)
    eff, _meta = derive_anchor_search_term(raw)
    push(eff)
    for tier in build_search_query_tiers(raw):
        if tier.label in ("strict", "core"):
            push(tier.termo)
    tokens = raw.split()
    if len(tokens) >= 4:
        for cut in range(1, min(6, len(tokens) - 2)):
            push(" ".join(tokens[: len(tokens) - cut]))
    return out


def _local_item_dedupe_key(it: Dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(it.get("numero_pncp") or ""),
        str(it.get("numero_item") or ""),
        str(it.get("descricao_item") or "")[:120],
    )


def _merge_local_item_batches(existing: List[Dict[str, Any]], new_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = {_local_item_dedupe_key(x) for x in existing}
    out = list(existing)
    for it in new_batch:
        key = _local_item_dedupe_key(it)
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def _build_manual_parity_top3(
    itens: List[Dict[str, Any]],
    termo_busca: str,
    *,
    faixa_min: Optional[float] = None,
    faixa_max: Optional[float] = None,
    target: int = 3,
) -> List[Dict[str, Any]]:
    """
    Fallback da busca inteligente: mesma base da busca manual (índice local + preço).
    Com faixa ativa, nunca relaxa — retorna menos de 3 se necessário.
    """
    tier_rank = {"strict": 0, "core": 1, "flex": 2, "anchor": 3}
    min_ok = int(PNCP_SEARCH_MIN_SCORE_APROVACAO)
    pool: List[Dict[str, Any]] = []
    for it in itens:
        if _row_price_for_faixa(it) <= 0.0:
            continue
        if faixa_min is not None and faixa_max is not None:
            if not _preco_dentro_faixa(it, faixa_min, faixa_max):
                continue
        tier = str(it.get("search_tier") or "").lower()
        lit = round(_literal_match_score(termo_busca, it), 3)
        score_base = 78 if tier == "strict" else 72 if tier == "core" else 65 if tier == "flex" else 58
        row = dict(it)
        row["literal_match"] = lit
        row["score_bruto"] = float(score_base)
        row["score_aprovacao"] = score_base
        row["confiabilidade"] = _classify_confiabilidade(score_base)
        row["risco"] = _classify_risco(score_base)
        row["status"] = "Aprovado" if score_base >= min_ok else "Revisar"
        row["similaridade_encontrada"] = tier in ("flex", "anchor") or lit < 6.0
        row["match_manual_parity"] = True
        row["origem"] = row.get("origem") or "base_local_itens"
        row["_manual_rank"] = (tier_rank.get(tier, 4), -lit, -_row_price_for_faixa(it))
        pool.append(row)
    pool.sort(key=lambda x: x["_manual_rank"])
    for row in pool:
        row.pop("_manual_rank", None)
    return _select_top3_prioritize_federal(pool)[: max(1, int(target))]


def _ia_item_key(it: Dict[str, Any]) -> str:
    return "|".join(
        [
            str(it.get("numero_pncp") or "").strip(),
            str(it.get("numero_item") or "").strip(),
            str(it.get("descricao_item") or "").strip().lower(),
            str(it.get("orgao") or "").strip().lower(),
        ]
    )


def _preco_dentro_faixa(it: Dict[str, Any], lo: float, hi: float) -> bool:
    v = _row_price_for_faixa(it)
    return v > 0.0 and lo <= v <= hi


def _ensure_top3_from_pool(
    current: List[Dict[str, Any]],
    pool: List[Dict[str, Any]],
    *,
    target: int = 3,
    termo_busca: str = "",
    faixa_min: Optional[float] = None,
    faixa_max: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Garante até ``target`` preços distintos quando o pool tiver candidatos elegíveis.
    Regra de negócio: busca inteligente deve tentar sempre 3 cotações por item.
    """
    target = max(1, int(target))
    out: List[Dict[str, Any]] = []
    used: set[str] = set()

    def eligible(it: Dict[str, Any]) -> bool:
        if _row_price_for_faixa(it) <= 0.0:
            return False
        if faixa_min is not None and faixa_max is not None:
            return _preco_dentro_faixa(it, faixa_min, faixa_max)
        return True

    def rank_key(it: Dict[str, Any]) -> tuple[float, float]:
        return (
            float(it.get("literal_match") or _literal_match_score(termo_busca, it)),
            float(it.get("score_aprovacao") or 0),
        )

    for row in current:
        if not eligible(row):
            continue
        k = _ia_item_key(row)
        if k and k in used:
            continue
        out.append(dict(row))
        if k:
            used.add(k)
        if len(out) >= target:
            return out[:target]

    candidates = [dict(x) for x in pool if eligible(x)]
    candidates.sort(key=rank_key, reverse=True)
    for cand in candidates:
        if len(out) >= target:
            break
        k = _ia_item_key(cand)
        if k and k in used:
            continue
        out.append(cand)
        if k:
            used.add(k)
    return out[:target]


def _enforce_faixa_no_top3(
    top3: List[Dict[str, Any]],
    pool: List[Dict[str, Any]],
    *,
    lo: float,
    hi: float,
    termo_busca: str,
) -> List[Dict[str, Any]]:
    """
    Substitui escolhas fora da faixa regional (valor base ± %) por candidatos dentro da faixa,
    preservando ordem de preferência por literal_match + score.
    """
    if not top3 or not pool:
        return top3
    in_band = [dict(x) for x in pool if _preco_dentro_faixa(x, lo, hi)]
    in_band.sort(
        key=lambda it: (
            float(it.get("literal_match") or _literal_match_score(termo_busca, it)),
            float(it.get("score_aprovacao") or 0),
        ),
        reverse=True,
    )
    used: set[str] = set()
    out: List[Dict[str, Any]] = []
    for it in top3:
        row = dict(it)
        if _preco_dentro_faixa(row, lo, hi):
            k = _ia_item_key(row) or f"id:{id(row)}"
            used.add(k)
            out.append(row)
            continue
        replaced = False
        for cand in in_band:
            k2 = _ia_item_key(cand) or f"id:{id(cand)}"
            if k2 in used:
                continue
            out.append(dict(cand))
            used.add(k2)
            replaced = True
            break
        if not replaced:
            k = _ia_item_key(row) or f"id:{id(row)}"
            if k not in used:
                used.add(k)
            out.append(row)
    return out[:3]


def _effective_min_score_aprovacao() -> int:
    """Score mínimo; modo qualidade exige pelo menos 55."""
    min_ok = int(PNCP_SEARCH_MIN_SCORE_APROVACAO)
    if PNCP_SEARCH_QUALITY_FIRST and min_ok < 55:
        return 55
    return min_ok


def _ia_rerank_pool_allowed(pool_mode: str) -> bool:
    """Quando o pool é mix literal+similar, rerank IA ainda pode rodar (modo qualidade + Qwen)."""
    if pool_mode in {"literal_only", "similar_only"}:
        return True
    if pool_mode == "mixed_fallback" and PNCP_IA_RERANK_MIXED_POOL:
        return True
    return False


def _ia_rerank_on_for_request(busca_lote: bool) -> bool:
    from . import config as _cfg

    if not _cfg.PNCP_IA_RERANK_ENABLED:
        return False
    if busca_lote:
        return bool(_cfg.PNCP_IA_RERANK_BULK_ENABLED)
    return True


def _ia_resumo_on_for_request(busca_lote: bool) -> bool:
    from . import config as _cfg

    if not _cfg.PNCP_IA_ITEM_RESUMO_ENABLED:
        return False
    return not busca_lote


def _ia_bulk_rerank_worth_it(pool_mode: str, selection_pool: List[Dict[str, Any]]) -> bool:
    """Delega à heurística compartilhada (local + LLM)."""
    from .local_rerank import rerank_worth_it_ambiguous

    return rerank_worth_it_ambiguous(pool_mode, selection_pool)


def _filter_ia_rerank_candidates(pool: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Prioriza candidatos fortes; em modo qualidade descarta fallback agressivo do scoring."""
    rows = list(pool or [])
    if PNCP_SEARCH_QUALITY_FIRST:
        rows = [x for x in rows if not bool(x.get("match_agressivo"))]
    rows.sort(
        key=lambda x: (
            0 if bool(x.get("match_agressivo")) else 1,
            float(x.get("literal_match") or 0),
            float(x.get("score_aprovacao") or 0),
        ),
        reverse=True,
    )
    return rows


def _select_top3_mixed_literal_similar(
    literal_scored: List[Dict[str, Any]],
    similar_scored: List[Dict[str, Any]],
    *,
    max_similar: int,
) -> List[Dict[str, Any]]:
    """Completa top 3 com no máximo N slots de similaridade (resto literal)."""
    base_literal = _select_top3_prioritize_federal(literal_scored)[:3]
    cap = max(0, int(max_similar))
    if cap <= 0:
        return base_literal
    faltantes = max(0, 3 - len(base_literal))
    if faltantes <= 0:
        return base_literal
    usados = {id(x) for x in base_literal}
    complemento = [x for x in similar_scored if id(x) not in usados]
    take_similar = min(faltantes, cap)
    base_similar = _select_top3_prioritize_federal(complemento)[:take_similar]
    merged = base_literal + base_similar
    if len(merged) < 3:
        restantes = max(0, 3 - len(merged))
        extra_literal = [
            x for x in literal_scored if id(x) not in {id(y) for y in merged}
        ]
        merged = _merge_unique_items(merged, _select_top3_prioritize_federal(extra_literal)[:restantes])
    return merged[:3]


def _build_ia_rerank_prompt(
    termo_busca: str,
    candidatos: List[Dict[str, Any]],
    *,
    faixa_min: Optional[float] = None,
    faixa_max: Optional[float] = None,
    valor_base_ref: Optional[float] = None,
    variacao_pct_ref: Optional[float] = None,
    variacao_sentido_ref: Optional[str] = None,
    bulk_mode: bool = False,
) -> str:
    desc_limit = 140 if bulk_mode else 500
    linhas: List[str] = []
    for c in candidatos:
        desc = str(c.get("descricao_item") or "").strip()
        if len(desc) > desc_limit:
            desc = desc[:desc_limit].rstrip() + "…"
        mat = str(c.get("material_servico") or "").strip()
        if bulk_mode and len(mat) > 80:
            mat = mat[:80].rstrip() + "…"
        linhas.append(
            f"- id={c.get('_ia_id')} | desc={desc} | mat={mat} "
            f"| qtd={c.get('quantidade') or ''} {c.get('unidade_medida') or ''} | valor={c.get('valor_unitario') or c.get('valor_total') or ''} "
            f"| orgao={c.get('orgao') or ''} | uf={c.get('uf') or ''}"
        )
    itens_txt = "\n".join(linhas)
    faixa_txt = ""
    if (
        faixa_min is not None
        and faixa_max is not None
        and valor_base_ref is not None
        and valor_base_ref > 0
        and variacao_pct_ref is not None
        and variacao_pct_ref >= 0
    ):
        faixa_txt = format_faixa_prompt_text(
            valor_base=valor_base_ref,
            variacao_pct=variacao_pct_ref,
            faixa_min=faixa_min,
            faixa_max=faixa_max,
            sentido=variacao_sentido_ref,
        )
    return (
        "Você é um avaliador técnico de cotações PNCP para pesquisa de preços públicos (Lei 14.133/2021).\n"
        f"Termo de busca do usuário: {termo_busca}\n\n"
        "Tarefa: escolha EXATAMENTE 3 candidatos mais aderentes ao termo — produto/serviço principal, "
        "não acessório genérico nem item de outro domínio.\n\n"
        "REGRAS OBRIGATÓRIAS:\n"
        "- Rejeite itens claramente de outra categoria (ex.: hospitalar se o termo não for médico).\n"
        "- Prefira descrição que nomeie o núcleo material do termo (substância, objeto, especificação).\n"
        "- Penalize descrições vagas, kits heterogêneos ou «diversos» sem vínculo com o termo.\n"
        "- Considere unidade e quantidade quando relevantes.\n"
        "- Diversifique órgãos quando possível (evite 3 linhas idênticas do mesmo contrato).\n"
        "- score_aprovacao: use faixa real 40–95; não dê 90+ a item fraco só para preencher.\n"
        f"{faixa_txt}\n"
        "Responda APENAS JSON válido:\n"
        '{"selected":[{"id":"...","score_aprovacao":75,"confiabilidade":"Alta|Média|Baixa",'
        '"risco":"Baixo|Médio|Alto","justificativa":"1 frase objetiva"}]}\n\n'
        f"Candidatos:\n{itens_txt}\n"
    )


def _parse_ia_rerank_response(raw_text: str) -> List[Dict[str, Any]]:
    txt = (raw_text or "").strip()
    if not txt:
        return []
    start = txt.find("{")
    end = txt.rfind("}")
    if start >= 0 and end > start:
        txt = txt[start : end + 1]
    try:
        data = json.loads(txt)
    except Exception:
        return []
    selected = data.get("selected")
    if not isinstance(selected, list):
        return []
    out: List[Dict[str, Any]] = []
    for entry in selected:
        if not isinstance(entry, dict):
            continue
        item_id = str(entry.get("id") or "").strip()
        if not item_id:
            continue
        score_raw = entry.get("score_aprovacao")
        score_val: Optional[int] = None
        if score_raw is not None and str(score_raw).strip() != "":
            score_val = int(max(0, min(100, _safe_float(score_raw))))
        out.append(
            {
                "id": item_id,
                "score_aprovacao": score_val,
                "confiabilidade": str(entry.get("confiabilidade") or "").strip() or None,
                "risco": str(entry.get("risco") or "").strip() or None,
                "justificativa": str(entry.get("justificativa") or "").strip() or None,
            }
        )
    return out


async def _ia_post_generate(prompt: str, *, timeout_seconds: float) -> str:
    """POST /api/llm/generate (llm_api ou qwen_llm_service) — rerank e resumo de item."""
    payload: Dict[str, Any] = {"prompt": prompt, "stream": False}
    if PNCP_IA_MODEL:
        payload["model"] = PNCP_IA_MODEL
    url = f"{PNCP_IA_BASE_URL}{PNCP_IA_GENERATE_PATH}"
    timeout = httpx.Timeout(max(1.0, float(timeout_seconds)))
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            body = resp.json()
    except Exception:
        return ""
    if not isinstance(body, dict):
        return ""
    data = body.get("data")
    if isinstance(data, dict):
        return str(data.get("response") or data.get("text") or "").strip()
    return str(body.get("response") or body.get("text") or "").strip()


async def _ia_post_generate_plain(prompt: str) -> str:
    """Resumo curto de item — timeout PNCP_IA_ITEM_RESUMO_TIMEOUT_SECONDS."""
    return await _ia_post_generate(prompt, timeout_seconds=PNCP_IA_ITEM_RESUMO_TIMEOUT_SECONDS)


def _sanitize_ia_interpretacao_item(text: str) -> str:
    """Remove rótulos metafóricos e meta-comentários de confiança que o modelo às vezes insere."""
    s = re.sub(r"\s+", " ", (text or "").strip())
    if not s:
        return s
    s = re.sub(
        r"^(n[úu]cleo do bem|ess[êe]ncia|foco|resumo|categoria|classifica[çc][ãa]o)\s*:\s*",
        "",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(
        r"^(infer[êe]ncia\s+(?:confiante|moderada|incerta)|confian[çc]a\s*(?:alta|m[ée]dia|baixa|moderada))\s*[.:,;]\s*",
        "",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(
        r"\s*[.;]?\s*(infer[êe]ncia\s+(?:confiante|moderada|incerta)|"
        r"confian[çc]a\s*(?:alta|m[ée]dia|baixa|moderada))\s*\.?\s*$",
        "",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(r"\s+", " ", s).strip(" ,.;:")
    return s


async def _ia_interpret_item_leve(termo_busca: str, item: Dict[str, Any]) -> str:
    """
    Uma linha curta identificando o bem/serviço (estilo catálogo), para títulos ambíguos ou descrições agregadas.
    """
    desc_full = str(
        item.get("descricao_item_original")
        or item.get("descricao_item")
        or item.get("material_servico_original")
        or item.get("material_servico")
        or ""
    ).strip()
    if len(desc_full) > 4500:
        desc_full = desc_full[:4500].rstrip() + "…"
    mat = str(item.get("material_servico_original") or item.get("material_servico") or "").strip()
    if len(mat) > 800:
        mat = mat[:800].rstrip() + "…"
    org = str(item.get("orgao") or "").strip()
    uf = str(item.get("uf") or "").strip()
    prompt = (
        "Você apoia pesquisa de preços na contratação pública brasileira (PNCP).\n"
        "O título/descrição PNCP pode ser genérico ou agregar vários produtos; o usuário precisa de uma leitura rápida.\n\n"
        f"Termo ou item de referência do usuário:\n{termo_busca.strip()}\n\n"
        "Descrição do item retornada pelo PNCP:\n"
        f"{desc_full}\n\n"
    )
    if mat:
        prompt += f"Material / serviço (campo auxiliar):\n{mat}\n\n"
    if org or uf:
        prompt += f"Órgão / UF (contexto): {org or '—'} / {uf or '—'}\n\n"
    prompt += (
        "Tarefa: em UMA ÚNICA frase curta em português do Brasil, diga o que o item parece ser, "
        "como rótulo de produto/serviço (ex.: 'Abacate in natura', 'Parafuso de aço inox, cabeça sextavada').\n"
        "Use o termo do usuário só para desambiguar quando a descrição PNCP for genérica ou misturar vários bens.\n"
        "PROIBIDO: expressões como 'núcleo do bem', 'essência', 'categoria', 'resumo'; "
        "dois pontos seguidos de rótulo vazio (ex.: 'Núcleo: ...'); "
        "qualquer comentário sobre confiança, certeza ou 'inferência confiante/moderada/incerta'.\n"
        "Regras: não invente marca, lote ou norma que não apareça no texto; não copie a descrição inteira nem liste tudo.\n"
        "Responda só com essa frase, em texto plano (sem markdown, sem JSON)."
    )
    raw = await _ia_post_generate_plain(prompt)
    return _sanitize_ia_interpretacao_item(raw)


async def _enriquecer_interpretacao_ia_itens(termo_busca: str, itens: List[Dict[str, Any]]) -> None:
    if not PNCP_IA_ITEM_RESUMO_ENABLED or not itens:
        return

    async def _one(it: Dict[str, Any]) -> None:
        try:
            out = await asyncio.wait_for(
                _ia_interpret_item_leve(termo_busca, it),
                timeout=max(1.0, float(PNCP_IA_ITEM_RESUMO_TIMEOUT_SECONDS)),
            )
            s = re.sub(r"\s+", " ", (out or "").strip())
            if len(s) > 420:
                s = s[:420].rstrip(" ,.;") + "…"
            it["ia_interpretacao_item"] = s or None
        except Exception:
            it["ia_interpretacao_item"] = None

    await asyncio.gather(*(_one(it) for it in itens))


async def _rerank_top3_with_ia(
    termo_busca: str,
    candidatos: List[Dict[str, Any]],
    *,
    faixa_min: Optional[float] = None,
    faixa_max: Optional[float] = None,
    valor_base_ref: Optional[float] = None,
    variacao_pct_ref: Optional[float] = None,
    variacao_sentido_ref: Optional[str] = None,
    bulk_mode: bool = False,
    timeout_seconds: Optional[float] = None,
) -> List[Dict[str, Any]]:
    if not PNCP_IA_RERANK_ENABLED or not candidatos:
        return []
    prompt = _build_ia_rerank_prompt(
        termo_busca,
        candidatos,
        faixa_min=faixa_min,
        faixa_max=faixa_max,
        valor_base_ref=valor_base_ref,
        variacao_pct_ref=variacao_pct_ref,
        variacao_sentido_ref=variacao_sentido_ref,
        bulk_mode=bulk_mode,
    )
    tmo = float(timeout_seconds) if timeout_seconds is not None else float(PNCP_IA_TIMEOUT_SECONDS)
    text = await _ia_post_generate(prompt, timeout_seconds=tmo)
    if not text:
        return []
    return _parse_ia_rerank_response(text)


def _infer_search_bottleneck(funil: Dict[str, Any], top3_n: int) -> str:
    """Heurística: índice vazio vs trava de filtro (token, homolog, faixa, scoring)."""
    if top3_n >= 1:
        return "ok"
    sql_rows = int(funil.get("sql_rows_fetched") or 0)
    local = int(funil.get("local_homologados") or 0)
    tok = int(funil.get("filtrados_token_match") or 0)
    hom = int(funil.get("filtrados_nao_homologados") or 0)
    faixa_rm = int(funil.get("eliminados_faixa_preco") or 0)
    scored = int(funil.get("scored_final_pool") or 0)
    if sql_rows == 0:
        return "indice_sem_match_fts"
    if local == 0 and tok > 0 and hom == 0:
        return "token_match_and"
    if local == 0 and hom > 0:
        return "filtro_homologados"
    if local > 0 and scored == 0 and faixa_rm > 0:
        return "faixa_preco"
    if local > 0 and scored == 0:
        return "scoring_inteligente"
    if scored > 0 and top3_n == 0:
        return "selecao_top3"
    return "indice_ou_termo"


def _bulk_search_timeout_response(payload: MarketSearchRequest) -> Dict[str, Any]:
    """Resposta vazia rápida quando o lote estoura o teto de tempo (não trava a fila)."""
    tmo = max(1.0, float(PNCP_BULK_SEARCH_MAX_SECONDS or 40))
    return {
        "ok": True,
        "filtros": {
            "termo_busca": payload.termo_busca,
            "uf": payload.uf,
            "municipio": payload.municipio,
            "recortes_geograficos": (
                [r.model_dump() for r in payload.recortes_geograficos]
                if payload.recortes_geograficos
                else None
            ),
            "codigo_municipio_ibge": payload.codigo_municipio_ibge,
            "codigo_modalidade": payload.codigo_modalidade,
            "pagina_inicial": payload.pagina,
            "max_paginas": payload.max_paginas,
            "tamanho_pagina": payload.tamanho_pagina,
            "fonte": "local_item_search",
        },
        "stats": {
            "total_registros_ia": 0,
            "total_selecionados_ia": 0,
            "busca_lote_timeout": True,
            "bulk_timeout_seconds": tmo,
            "funil_busca": {"bulk_timeout": True},
            "provavel_gargalo": "bulk_timeout",
        },
        "itens": [],
    }


async def market_search_intelligent(payload: MarketSearchRequest) -> Dict[str, Any]:
    """
    Versão inteligente da busca manual:
    - usa o mesmo índice local de itens PNCP (local_item_search);
    - aplica score 0-100 por item;
    - retorna exatamente 3 cotações com diversidade de órgão.
    """
    # Reutiliza a mesma fonte da busca manual (itens PNCP normalizados)
    busca_lote = bool(getattr(payload, "busca_lote", False))
    # Lote: relaxa homolog estrito, mas mantém faixa de preço por item quando informada.
    search_payload = payload
    if busca_lote:
        search_payload = payload.model_copy(update={"somente_homologados": False})
    ia_rerank_on = _ia_rerank_on_for_request(busca_lote)
    ia_resumo_on = _ia_resumo_on_for_request(busca_lote)
    limit = max(50, search_payload.max_paginas * search_payload.tamanho_pagina)
    if busca_lote:
        limit = min(limit, max(80, int(PNCP_BULK_SEARCH_SQL_LIMIT)))
    termo_busca_raw = search_payload.termo_busca
    termo_efetivo, term_meta = derive_anchor_search_term(termo_busca_raw)
    itens: List[Dict[str, Any]] = []
    base_stats: Dict[str, Any] = {}
    terms_tried: List[str] = []
    bulk_term_cap = max(2, int(PNCP_BULK_MAX_TERM_FALLBACKS)) if busca_lote else 0
    for i, term_try in enumerate(_iter_search_term_fallbacks(termo_busca_raw)):
        if busca_lote and i >= bulk_term_cap:
            break
        terms_tried.append(term_try)
        batch_result = local_item_search(
            term_try,
            uf=search_payload.uf,
            municipio=search_payload.municipio,
            recortes_geograficos=search_payload.recortes_geograficos,
            codigo_modalidade=search_payload.codigo_modalidade,
            limit=limit,
            cleanup_for_display=False,
            somente_homologados=search_payload.somente_homologados,
            filtrar_fornecedor_para_exibicao=not busca_lote,
            enrich_homolog_max=(
                max(0, int(PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX)) if busca_lote else None
            ),
        )
        if not base_stats:
            base_stats = dict(batch_result.get("stats") or {})
        batch = list(batch_result.get("itens") or [])
        itens = _merge_local_item_batches(itens, batch)
        if busca_lote and batch and int(PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX) > 0:
            from .supplier_resolver import item_fornecedor_valido_para_busca

            local_cap = max(0, int(PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX))
            enrich_pool = [
                x
                for x in itens
                if x.get("item_homologado") and not item_fornecedor_valido_para_busca(x)
            ]
            if enrich_pool:
                local_enriched = await enrich_homolog_items_from_pncp(
                    enrich_pool,
                    max_n=min(local_cap, len(enrich_pool)),
                )
                funil_local_enrich = int(base_stats.get("enriquecidos_pncp_local_lote") or 0)
                base_stats["enriquecidos_pncp_local_lote"] = funil_local_enrich + int(local_enriched or 0)
        priced_n = sum(1 for x in itens if _row_price_for_faixa(x) > 0.0)
        if priced_n >= 3:
            break
        # Lote: se o índice já tem preço, não varre 6 termos (top3 + enrich PNCP fecha o resto).
        if busca_lote and priced_n >= 1:
            break
        # Lote sem preço: no máximo 3 termos antes do híbrido (evita ~6× SQL/item vazio).
        if busca_lote and priced_n == 0 and i >= 2:
            break
        if len(itens) >= limit:
            break
    base_items = {"ok": True, "itens": itens, "stats": base_stats}
    base_stats = dict(base_items.get("stats") or {})
    funil: Dict[str, Any] = {
        "termo_busca": term_meta,
        "local_homologados": len(itens),
        "local_com_preco": sum(1 for x in itens if _row_price_for_faixa(x) > 0.0),
        "sql_rows_fetched": int(base_stats.get("sql_rows_fetched") or 0),
        "filtrados_token_match": int(base_stats.get("filtrados_token_match") or 0),
        "filtrados_nao_homologados": int(base_stats.get("filtrados_nao_homologados") or 0),
        "busca_lote_relaxada": bool(busca_lote),
        "busca_lote_fornecedor_filter_final_only": bool(busca_lote),
        "hybrid_bulk_disabled": bool(busca_lote and not PNCP_HYBRID_BULK_ENABLED),
        "bulk_max_term_fallbacks": int(PNCP_BULK_MAX_TERM_FALLBACKS) if busca_lote else None,
        "bulk_local_enrich_max": int(PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX) if busca_lote else None,
        "search_terms_tried": terms_tried,
    }
    hybrid_used = False
    hybrid_live_count = 0
    hybrid_min = max(1, int(PNCP_HYBRID_MIN_LOCAL_RESULTS))
    local_priced = sum(1 for x in itens if _row_price_for_faixa(x) > 0.0)
    hybrid_allowed = PNCP_HYBRID_FALLBACK_ENABLED and (not busca_lote or PNCP_HYBRID_BULK_ENABLED)
    if busca_lote:
        # Lote: só PNCP ao vivo se o índice local não trouxe nada com preço (evita 6 páginas/item).
        need_hybrid = local_priced == 0
    else:
        need_hybrid = len(itens) < hybrid_min or local_priced < hybrid_min
    if hybrid_allowed and need_hybrid:
        live_pages = max(1, min(int(PNCP_HYBRID_MAX_LIVE_PAGES), int(search_payload.max_paginas or 1)))
        if busca_lote:
            live_pages = min(live_pages, 2)
        live_payload = search_payload.model_copy(update={"max_paginas": live_pages})
        try:
            live_result = await market_search(live_payload)
            live_itens = list(live_result.get("itens") or [])
            hybrid_used = True
            hybrid_live_count = len(live_itens)
            seen = {
                (
                    str(it.get("numero_pncp") or ""),
                    str(it.get("numero_item") or ""),
                    str(it.get("descricao_item") or "")[:120],
                )
                for it in itens
            }
            for lit in live_itens:
                key = (
                    str(lit.get("numero_pncp") or ""),
                    str(lit.get("numero_item") or ""),
                    str(lit.get("descricao_item") or "")[:120],
                )
                if key in seen:
                    live_cnpj = str(lit.get("cnpj_fornecedor") or "").strip()
                    if live_cnpj:
                        for loc in itens:
                            loc_key = (
                                str(loc.get("numero_pncp") or ""),
                                str(loc.get("numero_item") or ""),
                                str(loc.get("descricao_item") or "")[:120],
                            )
                            if loc_key != key:
                                continue
                            if str(loc.get("cnpj_fornecedor") or "").strip():
                                break
                            loc["cnpj_fornecedor"] = live_cnpj
                            if str(lit.get("fornecedor") or "").strip():
                                loc["fornecedor"] = lit.get("fornecedor")
                            if lit.get("fornecedor_cadastro"):
                                loc["fornecedor_cadastro"] = lit.get("fornecedor_cadastro")
                            if lit.get("fornecedor_fonte_nome"):
                                loc["fornecedor_fonte_nome"] = lit.get("fornecedor_fonte_nome")
                            loc["fornecedor_hibrido_live"] = True
                            break
                    continue
                seen.add(key)
                lit = dict(lit)
                lit["origem"] = lit.get("origem") or "pncp_live_fallback"
                itens.append(lit)
        except PNCPClientError:
            pass
    service_blocked_count = 0
    if PNCP_BLOCK_SERVICE_ITEMS and itens:
        filtered_items: List[Dict[str, Any]] = []
        for it in itens:
            if _is_service_like_item(it):
                service_blocked_count += 1
                continue
            filtered_items.append(it)
        itens = filtered_items
    if not itens:
        return {
            "ok": True,
            "filtros": {
                "termo_busca": payload.termo_busca,
                "uf": payload.uf,
                "municipio": payload.municipio,
                "recortes_geograficos": (
                    [r.model_dump() for r in payload.recortes_geograficos]
                    if payload.recortes_geograficos
                    else None
                ),
                "codigo_municipio_ibge": payload.codigo_municipio_ibge,
                "codigo_modalidade": payload.codigo_modalidade,
                "pagina_inicial": payload.pagina,
                "max_paginas": payload.max_paginas,
                "tamanho_pagina": payload.tamanho_pagina,
                "fonte": "local_item_search",
            },
            "stats": {
                **base_stats,
                "servico_bloqueio_ativo": bool(PNCP_BLOCK_SERVICE_ITEMS),
                "servico_bloqueados": int(service_blocked_count),
                "hybrid_fallback_used": hybrid_used,
                "hybrid_live_count": hybrid_live_count,
                "funil_busca": {**funil, "top3_final": 0},
                "provavel_gargalo": _infer_search_bottleneck(funil, 0),
            },
            "itens": [],
        }

    termo_tokens = preprocess_cotacao_search_term(termo_busca_raw) or termo_busca_raw
    query_groups = _build_search_tokens(termo_tokens)
    ref_qty = _safe_float(search_payload.quantidade_referencia)
    ref_unit = _normalize_unit(search_payload.unidade_medida_referencia)
    ref_val_set = search_payload.valor_base_referencia is not None
    ref_var_set = search_payload.variacao_percentual_referencia is not None
    ref_sentido = normalize_variacao_sentido(
        getattr(search_payload, "variacao_sentido_referencia", None)
    )
    funil["faixa_ativa"] = faixa_regional_ativa(
        search_payload.valor_base_referencia if ref_val_set else None,
        search_payload.variacao_percentual_referencia if ref_var_set else None,
    )
    try:
        ref_value = float(search_payload.valor_base_referencia) if ref_val_set else 0.0
    except (TypeError, ValueError):
        ref_value = 0.0
    try:
        ref_var_pct = float(search_payload.variacao_percentual_referencia) if ref_var_set else 0.0
    except (TypeError, ValueError):
        ref_var_pct = 0.0
    faixa_min: Optional[float] = None
    faixa_max: Optional[float] = None
    if funil["faixa_ativa"]:
        faixa_min, faixa_max = compute_faixa_regional(ref_value, ref_var_pct, sentido=ref_sentido)
        funil["variacao_sentido"] = ref_sentido
    valores = [
        _row_price_for_faixa(x)
        for x in itens
        if _row_price_for_faixa(x) > 0.0
    ]
    median_val = median(valores) if valores else None
    min_ok = _effective_min_score_aprovacao()

    def _score_candidates(candidates: List[Dict[str, Any]], *, mode: str) -> List[Dict[str, Any]]:
        out_rows: List[Dict[str, Any]] = []
        # Limiares de literal alinhados ao termo_efetivo (não à descrição inteira da cotação).
        lit_strict = 6.0
        lit_relaxed = 3.0
        lit_aggressive = 1.0
        for it in candidates:
            relaxed = mode != "strict"
            aggressive = mode == "aggressive"
            partial_anchor = _has_partial_anchor_match(it, query_groups)
            origem = str(it.get("origem") or "")
            from_local_index = origem in ("base_local_itens", "") or origem.startswith("base_local")
            if not relaxed and not _is_strict_candidate_match(it, query_groups):
                # Índice local já exigiu match AND nos mesmos token groups — não refiltrar por proximidade.
                if not from_local_index:
                    if not _has_core_token_overlap(it, query_groups, min_hits=1):
                        continue
            if mode == "relaxed" and not _has_core_token_overlap(it, query_groups, min_hits=2):
                if not partial_anchor:
                    continue
            if aggressive and not _has_core_token_overlap(it, query_groups, min_hits=1):
                sim = _aggressive_similarity_score(termo_efetivo, it)
                if sim < 0.62 and not partial_anchor:
                    continue
            elif aggressive:
                sim = _aggressive_similarity_score(termo_efetivo, it)
                if sim < 0.50 and not partial_anchor:
                    continue
            if aggressive:
                # Mesmo agressivo: impede itens muito desconexos.
                if _context_penalty(it, query_groups) <= -14.0:
                    continue
            elif relaxed and not _has_core_token_overlap(it, query_groups, min_hits=2):
                continue
            # Contexto totalmente incompatível continua bloqueado mesmo em fallback.
            pen_probe = _context_penalty(it, query_groups)
            if pen_probe <= -20.0:
                continue

            texto_item = f"{it.get('descricao_item') or ''} {it.get('material_servico') or ''}".strip()
            sem_raw = (
                _compute_match_score(texto_item, query_groups, variant_groups=True)
                if query_groups
                else 0.0
            )
            if sem_raw <= 0.0 and from_local_index:
                # Índice local já validou AND de tokens (variante OR intra-grupo).
                sem_raw = 1.0
            sem = min(55.0, (min(sem_raw, 3.0) / 3.0) * 55.0) if sem_raw > 0 else 0.0
            if sem <= 0 and partial_anchor:
                # Permite "match parcial literal" (núcleo + apresentação), mesmo sem frase completa.
                sem = 18.0
            if sem <= 0:
                continue
            literal_match = round(_literal_match_score(termo_efetivo, it), 3)
            # Índice local já validou tokens: literal baixo não descarta se houve match semântico.
            if not relaxed and literal_match < lit_strict:
                if sem_raw <= 0.0 and not partial_anchor:
                    continue
            if mode == "relaxed" and literal_match < lit_relaxed:
                if not partial_anchor:
                    continue
            if aggressive and literal_match < lit_aggressive:
                if not partial_anchor:
                    continue
            tbl = 8.0
            rec = _score_recency(it)
            coh = _score_value_coherence(it, median_val)
            clar = _score_clarity_and_unit(it, query_groups)
            pen = pen_probe
            ref_fit = 0.0
            row_unit = _normalize_unit(it.get("unidade_medida"))
            if ref_unit and row_unit:
                ref_fit += 6.0 if ref_unit == row_unit else -4.0
            row_qty = _safe_float(it.get("quantidade"))
            if ref_qty > 0 and row_qty > 0:
                q_dev = abs(row_qty - ref_qty) / max(ref_qty, 1e-9)
                if q_dev <= 0.2:
                    ref_fit += 5.0
                elif q_dev <= 0.5:
                    ref_fit += 2.0
                else:
                    ref_fit -= 2.0
            supplier_pen = 0.0
            cnpj_f = str(it.get("cnpj_fornecedor") or "").strip()
            if not cnpj_f:
                homolog_flag = it.get("item_homologado")
                tem_res = it.get("temResultado")
                if tem_res is False or homolog_flag is False:
                    supplier_pen = -35.0
                else:
                    supplier_pen = -18.0
            row_value = _row_price_for_faixa(it)
            # Regra rígida: nunca considerar item com preço zerado/ausente.
            if row_value <= 0:
                continue
            if faixa_min is not None and faixa_max is not None:
                # Regra de negócio: com valor base + variação informados, faixa é obrigatória.
                if not _preco_dentro_faixa(it, faixa_min, faixa_max):
                    continue
            if ref_value > 0 and row_value > 0:
                v_dev = abs(row_value - ref_value) / max(ref_value, 1e-9)
                if v_dev <= 0.25:
                    ref_fit += 6.0
                elif v_dev <= 0.5:
                    ref_fit += 3.0
                else:
                    ref_fit -= 2.0
            tier_bonus = 0.0
            search_tier = str(it.get("search_tier") or "").strip().lower()
            if search_tier == "strict":
                tier_bonus = 10.0
            elif search_tier == "core":
                tier_bonus = 6.0
            elif search_tier == "flex":
                tier_bonus = 2.0
            try:
                from .product_category_match import product_category_strict_reject
                from .product_spec_match import product_spec_rerank_adjustment, product_spec_strict_reject

                if product_category_strict_reject(termo_busca_raw, it):
                    continue
                if product_spec_strict_reject(termo_busca_raw, it):
                    continue
                spec_adj = product_spec_rerank_adjustment(termo_busca_raw, it)
            except Exception:
                spec_adj = 0.0
            raw_score = sem + tbl + rec + coh + clar + pen + ref_fit + supplier_pen + tier_bonus + spec_adj
            score_0_100 = max(0, min(100, round(raw_score)))
            it2 = dict(it)
            it2["score_bruto"] = round(raw_score, 3)
            it2["score_ref_fit"] = round(ref_fit, 3)
            it2["literal_match"] = literal_match
            it2["score_aprovacao"] = score_0_100
            it2["confiabilidade"] = _classify_confiabilidade(score_0_100)
            it2["risco"] = _classify_risco(score_0_100)
            it2["status"] = "Aprovado" if score_0_100 >= min_ok else "Revisar"
            it2["partial_anchor_match"] = bool(partial_anchor)
            # Itens do índice local em modo estrito já passaram no match de tokens — não
            # reclassificar como "similaridade" só por partial_anchor (quebrava top3 literal).
            if from_local_index and not relaxed and sem_raw > 0 and literal_match >= lit_strict:
                it2["similaridade_encontrada"] = False
            else:
                it2["similaridade_encontrada"] = (
                    _is_similaridade_encontrada(it2) or relaxed or partial_anchor
                )
            if relaxed:
                it2["match_relaxado"] = True
            if aggressive:
                it2["match_agressivo"] = True
            out_rows.append(it2)
        return out_rows

    scored: List[Dict[str, Any]] = _score_candidates(itens, mode="strict")
    funil["scored_estrito"] = len(scored)
    fallback_relaxado_usado = False
    fallback_agressivo_usado = False
    relaxed_threshold = 2 if PNCP_SEARCH_QUALITY_FIRST else 3
    aggressive_threshold = 1 if PNCP_SEARCH_QUALITY_FIRST else 2
    # Fallback: se a busca estrita não atingir massa crítica, abre variações claras.
    if len(scored) < relaxed_threshold:
        fallback_rows = _score_candidates(itens, mode="relaxed")
        funil["scored_relaxado"] = len(fallback_rows)
        fallback_relaxado_usado = bool(fallback_rows)
        scored = _merge_unique_items(scored, fallback_rows)
    # Fallback agressivo: só quando pool ainda está muito fraco (desligado cedo em modo qualidade).
    if len(scored) < aggressive_threshold and not PNCP_SEARCH_QUALITY_FIRST:
        fallback_agressivo = _score_candidates(itens, mode="aggressive")
        funil["scored_agressivo"] = len(fallback_agressivo)
        fallback_agressivo_usado = bool(fallback_agressivo)
        scored = _merge_unique_items(scored, fallback_agressivo)
    elif len(scored) < aggressive_threshold and PNCP_SEARCH_QUALITY_FIRST:
        funil["scored_agressivo"] = 0
        funil["fallback_agressivo_desligado"] = True

    # Blindagem final: remove qualquer item sem preço válido e, quando houver faixa, mantém só itens dentro.
    scored_pre_preco = len(scored)
    scored = [x for x in scored if _row_price_for_faixa(x) > 0.0]
    funil["eliminados_sem_preco"] = max(0, scored_pre_preco - len(scored))
    if faixa_min is not None and faixa_max is not None:
        before_faixa = len(scored)
        scored = [x for x in scored if _preco_dentro_faixa(x, faixa_min, faixa_max)]
        funil["eliminados_faixa_preco"] = max(0, before_faixa - len(scored))
        funil["faixa_min"] = faixa_min
        funil["faixa_max"] = faixa_max
    else:
        funil["eliminados_faixa_preco"] = 0
    funil["scored_final_pool"] = len(scored)

    # Rede de segurança: índice achou homologados com preço, mas scoring zerou tudo (sem faixa).
    if not scored and itens and faixa_min is None and faixa_max is None:
        priced_local = [x for x in itens if _row_price_for_faixa(x) > 0.0]
        if priced_local:
            scored = []
            for it in priced_local:
                lit = round(_literal_match_score(termo_efetivo, it), 3)
                row = dict(it)
                row["literal_match"] = lit
                row["score_bruto"] = round(35.0 + min(lit, 55.0), 3)
                row["score_aprovacao"] = int(max(0, min(100, round(row["score_bruto"]))))
                row["confiabilidade"] = _classify_confiabilidade(row["score_aprovacao"])
                row["risco"] = _classify_risco(row["score_aprovacao"])
                row["status"] = "Aprovado" if row["score_aprovacao"] >= min_ok else "Revisar"
                row["similaridade_encontrada"] = False
                row["origem"] = row.get("origem") or "base_local_itens"
                scored.append(row)
            funil["scored_fallback_local_preco"] = len(scored)
            funil["scored_final_pool"] = len(scored)

    # Reescala para ampliar separação entre bons e ruins no conjunto atual.
    # Modo qualidade: mantém scores absolutos (evita inflar itens fracos para o top 3).
    if scored and not PNCP_SEARCH_QUALITY_FIRST:
        raw_values = [_safe_float(x.get("score_bruto")) for x in scored]
        lo = min(raw_values)
        hi = max(raw_values)
        span = hi - lo
        for row in scored:
            raw = _safe_float(row.get("score_bruto"))
            if span <= 1e-9:
                norm = 65.0
            else:
                norm = 35.0 + 65.0 * ((raw - lo) / span)
            score_adj = int(max(0, min(100, round(norm))))
            row["score_aprovacao"] = score_adj
            row["confiabilidade"] = _classify_confiabilidade(score_adj)
            row["risco"] = _classify_risco(score_adj)
            row["status"] = "Aprovado" if score_adj >= min_ok else "Revisar"
            # Não sobrescrever classificação literal/similaridade definida no scoring.
            if not row.get("match_relaxado") and not row.get("match_agressivo"):
                if row.get("similaridade_encontrada") is None:
                    row["similaridade_encontrada"] = _is_similaridade_encontrada(row)

    scored.sort(
        key=lambda x: (
            float(x.get("literal_match") or 0),
            float(x.get("score_aprovacao") or 0),
            float(x.get("valor_unitario") or x.get("valor_total") or 0),
        ),
        reverse=True,
    )

    def _is_literal_candidate(it: Dict[str, Any]) -> bool:
        # Literal "de verdade": veio do fluxo estrito e não está marcado como similaridade/fallback.
        if bool(it.get("match_relaxado")) or bool(it.get("match_agressivo")):
            return False
        tier = str(it.get("search_tier") or "").lower()
        origem = str(it.get("origem") or "")
        if tier in ("strict", "core") and origem.startswith("base_local"):
            return True
        if bool(it.get("similaridade_encontrada")):
            return False
        return float(it.get("literal_match") or 0) >= 6.0

    literal_scored = [x for x in scored if _is_literal_candidate(x)]
    similar_scored = [x for x in scored if not _is_literal_candidate(x)]
    funil["literal_pool"] = len(literal_scored)
    funil["similar_pool"] = len(similar_scored)
    pool_mode = "mixed_fallback"
    if len(literal_scored) >= 3:
        selection_pool = list(literal_scored)
        pool_mode = "literal_only"
    elif len(literal_scored) == 0:
        selection_pool = list(similar_scored)
        pool_mode = "similar_only"
    else:
        # Regra do cliente: similaridade só complementa quando faltar literal.
        selection_pool = _merge_unique_items(literal_scored, similar_scored)

    top3: List[Dict[str, Any]] = []
    ia_used = False
    local_rerank_used = False
    ia_rerank_allowed = _ia_rerank_pool_allowed(pool_mode)
    funil["ia_rerank_pool_mode"] = pool_mode
    funil["ia_rerank_allowed"] = bool(ia_rerank_allowed)
    funil["ia_rerank_bulk"] = bool(busca_lote)
    funil["search_quality_first"] = bool(PNCP_SEARCH_QUALITY_FIRST)
    rerank_worth = _ia_bulk_rerank_worth_it(pool_mode, selection_pool)
    try:
        from .pack_size_match import extract_pack_hints_from_term
        from .product_spec_match import product_spec_has_constraints

        if extract_pack_hints_from_term(termo_busca_raw).pack_units is not None:
            rerank_worth = True
        if product_spec_has_constraints(termo_busca_raw):
            rerank_worth = True
    except Exception:
        pass
    funil["rerank_worth_ambiguous"] = bool(rerank_worth)
    funil["ia_rerank_bulk_skipped_clear"] = bool(
        busca_lote and ia_rerank_on and ia_rerank_allowed and selection_pool and not rerank_worth
    )
    funil["local_rerank_skipped_clear"] = bool(
        PNCP_LOCAL_RERANK_ENABLED and ia_rerank_allowed and selection_pool and not rerank_worth
    )

    if PNCP_LOCAL_RERANK_ENABLED and ia_rerank_allowed and selection_pool and rerank_worth:
        from .local_rerank import apply_local_rerank_top3
        from .pack_size_match import extract_pack_hints_from_term

        pack_term = extract_pack_hints_from_term(termo_busca_raw)
        if pack_term.pack_units is not None:
            funil["pack_units_referencia"] = pack_term.pack_units

        top3_local, local_ok = apply_local_rerank_top3(
            termo_efetivo,
            selection_pool,
            query_groups=query_groups,
            min_ok=min_ok,
            max_candidates=PNCP_LOCAL_RERANK_MAX_CANDIDATES,
            faixa_min=faixa_min,
            faixa_max=faixa_max,
            termo_raw=termo_busca_raw,
        )
        if local_ok and top3_local:
            top3 = top3_local
            local_rerank_used = True

    skip_qwen_after_local = local_rerank_used and PNCP_IA_RERANK_PREFER_LOCAL and len(top3) >= 1
    if (
        ia_rerank_on
        and ia_rerank_allowed
        and selection_pool
        and rerank_worth
        and not skip_qwen_after_local
    ):
        pool_ia_source = _filter_ia_rerank_candidates(selection_pool)
        max_cands = PNCP_IA_BULK_MAX_CANDIDATES if busca_lote else PNCP_IA_MAX_CANDIDATES
        limite_candidatos = max(6, min(max_cands, len(pool_ia_source)))
        rerank_timeout = PNCP_IA_BULK_TIMEOUT_SECONDS if busca_lote else PNCP_IA_TIMEOUT_SECONDS
        pool_ia = list(pool_ia_source)
        if faixa_min is not None and faixa_max is not None:
            in_band_ia = [x for x in pool_ia if _preco_dentro_faixa(x, faixa_min, faixa_max)]
            if len(in_band_ia) >= 3:
                pool_ia = in_band_ia
        candidatos_ia: List[Dict[str, Any]] = []
        for idx, base_item in enumerate(pool_ia[:limite_candidatos]):
            row = dict(base_item)
            row["_ia_id"] = f"cand-{idx}"
            candidatos_ia.append(row)
        ia_selected = await _rerank_top3_with_ia(
            payload.termo_busca,
            candidatos_ia,
            faixa_min=faixa_min,
            faixa_max=faixa_max,
            valor_base_ref=ref_value if ref_val_set else None,
            variacao_pct_ref=ref_var_pct if ref_var_set else None,
            variacao_sentido_ref=ref_sentido if funil.get("faixa_ativa") else None,
            bulk_mode=busca_lote,
            timeout_seconds=rerank_timeout,
        )
        if ia_selected:
            by_id = {str(c.get("_ia_id")): c for c in candidatos_ia}
            chosen: List[Dict[str, Any]] = []
            for picked in ia_selected:
                cid = str(picked.get("id") or "")
                row = by_id.get(cid)
                if not row:
                    continue
                if faixa_min is not None and faixa_max is not None:
                    if not _preco_dentro_faixa(row, faixa_min, faixa_max):
                        continue
                out = dict(row)
                out.pop("_ia_id", None)
                if picked.get("score_aprovacao") is not None:
                    ia_score = int(max(0, min(100, _safe_float(picked["score_aprovacao"]))))
                    base_score = int(max(0, min(100, _safe_float(row.get("score_aprovacao")))))
                    literal = float(out.get("literal_match") or 0.0)
                    # Blindagem: não deixa o rerank da IA colapsar score forte para ~0.
                    if not (ia_score <= 15 and base_score >= min_ok and literal >= 45):
                        out["score_aprovacao"] = ia_score
                # Mantém consistência: confiabilidade/risco sempre derivados do score final.
                final_score = int(max(0, min(100, _safe_float(out.get("score_aprovacao")))))
                out["score_aprovacao"] = final_score
                out["confiabilidade"] = _classify_confiabilidade(final_score)
                out["risco"] = _classify_risco(final_score)
                out["status"] = "Aprovado" if final_score >= min_ok else "Revisar"
                if picked.get("justificativa"):
                    out["ia_justificativa"] = picked["justificativa"]
                chosen.append(out)
                if len(chosen) >= 3:
                    break
            if chosen:
                chosen.sort(
                    key=lambda it: (
                        float(it.get("literal_match") or _literal_match_score(termo_efetivo, it)),
                        float(it.get("score_aprovacao") or 0),
                    ),
                    reverse=True,
                )
                # Regra de negócio: prioriza esfera federal; se faltar, completa com demais esferas.
                merged = _merge_unique_items(chosen, selection_pool)
                top3 = _select_top3_prioritize_federal(merged)[:3]
                ia_used = True

    if not top3:
        if pool_mode == "literal_only":
            top3 = _select_top3_prioritize_federal(literal_scored)[:3]
        elif pool_mode == "similar_only":
            top3 = _select_top3_prioritize_federal(similar_scored)[:3]
        else:
            max_sim = int(PNCP_SEARCH_MAX_SIMILAR_IN_TOP3) if PNCP_SEARCH_QUALITY_FIRST else 3
            top3 = _select_top3_mixed_literal_similar(
                literal_scored,
                similar_scored,
                max_similar=max_sim,
            )

    funil["top3_antes_completar"] = len(top3)
    top3 = _ensure_top3_from_pool(
        top3,
        scored,
        target=3,
        termo_busca=termo_efetivo,
        faixa_min=faixa_min,
        faixa_max=faixa_max,
    )
    if not top3 and itens:
        top3 = _build_manual_parity_top3(
            itens,
            termo_efetivo,
            faixa_min=faixa_min,
            faixa_max=faixa_max,
        )
        funil["manual_parity_fallback"] = len(top3)
    elif len(top3) < 3 and itens:
        extra = _build_manual_parity_top3(
            itens,
            termo_efetivo,
            faixa_min=faixa_min,
            faixa_max=faixa_max,
            target=3,
        )
        top3 = _merge_unique_items(top3, extra)[:3]
        if extra:
            funil["manual_parity_topup"] = len(extra)
    if faixa_min is not None and faixa_max is not None and top3:
        top3 = [x for x in top3 if _preco_dentro_faixa(x, faixa_min, faixa_max)]
    funil["top3_final"] = len(top3)
    if len(top3) < 3 and funil.get("scored_final_pool", 0) >= 3:
        funil["provavel_gargalo_top3"] = "selecao_top3_incompleta"
    elif len(top3) < 3 and funil.get("local_com_preco", 0) >= 3 and funil.get("scored_final_pool", 0) < 3:
        funil["provavel_gargalo_top3"] = "scoring_ou_faixa_reduziu_pool"
    elif len(top3) == 0 and funil.get("local_homologados", 0) == 0 and funil.get("sql_rows_fetched", 0) > 0:
        funil["provavel_gargalo_top3"] = "token_match_pos_fts"
    elif len(top3) == 0 and funil.get("local_homologados", 0) > 0 and funil.get("local_com_preco", 0) == 0:
        funil["provavel_gargalo_top3"] = "homologados_sem_preco_indice"

    enrich_n_top3 = 0
    top3_antes_filtro_fornecedor = len(top3)
    if top3:
        enrich_cap = max(0, min(int(PNCP_SEARCH_ENRICH_HOMOLOG_MAX), len(top3)))
        if busca_lote:
            enrich_cap = min(enrich_cap, max(0, int(PNCP_BULK_ENRICH_HOMOLOG_MAX)))
        funil["enrich_homolog_cap"] = enrich_cap
        if enrich_cap:
            enrich_n_top3 = await enrich_homolog_items_from_pncp(top3, max_n=enrich_cap)

    for row in top3:
        apply_item_display_cleanup(row)

    top3 = filter_items_for_search_display(top3)
    funil["top3_antes_filtro_fornecedor"] = top3_antes_filtro_fornecedor
    funil["top3_apos_filtro_fornecedor"] = len(top3)
    funil["top3_com_preco_positivo"] = len(top3)

    ia_resumo_ok = False
    if ia_resumo_on and top3:
        await _enriquecer_interpretacao_ia_itens(payload.termo_busca, top3)
        ia_resumo_ok = any(bool(str(x.get("ia_interpretacao_item") or "").strip()) for x in top3)

    out_stats = dict(base_items.get("stats") or {})
    total_federais = sum(1 for x in scored if _is_federal_item(x))
    federais_score_80 = sum(1 for x in scored if _is_federal_item(x) and _safe_float(x.get("score_aprovacao")) >= 80.0)
    out_stats["total_registros_ia"] = len(scored)
    out_stats["total_selecionados_ia"] = len(top3)
    out_stats["regra_selecao"] = "top3_federal_primeiro_depois_inciso_ii"
    out_stats["federais_encontrados"] = total_federais
    out_stats["federais_score_maior_igual_80"] = federais_score_80
    out_stats["ia_rerank_ativo"] = bool(ia_rerank_on)
    out_stats["ia_rerank_usado"] = ia_used
    out_stats["ia_rerank_bulk_ativo"] = bool(busca_lote and ia_rerank_on)
    out_stats["local_rerank_ativo"] = bool(PNCP_LOCAL_RERANK_ENABLED)
    out_stats["local_rerank_usado"] = bool(local_rerank_used)
    out_stats["search_quality_first"] = bool(PNCP_SEARCH_QUALITY_FIRST)
    out_stats["ia_interpretacao_item_ativo"] = bool(ia_resumo_on)
    out_stats["ia_interpretacao_item_usado"] = bool(ia_resumo_ok)
    out_stats["fallback_similaridade_ativo"] = True
    out_stats["fallback_similaridade_usado"] = bool(fallback_relaxado_usado)
    out_stats["fallback_similaridade_agressivo_usado"] = bool(fallback_agressivo_usado)
    out_stats["literal_encontrados"] = len(literal_scored)
    out_stats["similaridade_encontrados"] = len(similar_scored)
    out_stats["modo_selecao_literal_similaridade"] = pool_mode
    out_stats["servico_bloqueio_ativo"] = bool(PNCP_BLOCK_SERVICE_ITEMS)
    out_stats["servico_bloqueados"] = int(service_blocked_count)
    out_stats["hybrid_fallback_used"] = hybrid_used
    out_stats["hybrid_live_count"] = hybrid_live_count
    out_stats["enriquecidos_pncp_na_busca"] = enrich_n_top3
    out_stats["itens_com_cnpj_fornecedor"] = sum(
        1 for x in top3 if str(x.get("cnpj_fornecedor") or "").strip()
    )
    out_stats["funil_busca"] = funil
    out_stats["provavel_gargalo"] = (
        funil.get("provavel_gargalo_top3")
        or _infer_search_bottleneck(funil, len(top3))
    )
    out_stats["min_score_aprovacao"] = min_ok

    return {
        "ok": bool(base_items.get("ok", True)),
        "filtros": {
            "termo_busca": payload.termo_busca,
            "uf": payload.uf,
            "municipio": payload.municipio,
            "recortes_geograficos": (
                [r.model_dump() for r in payload.recortes_geograficos]
                if payload.recortes_geograficos
                else None
            ),
            "codigo_municipio_ibge": payload.codigo_municipio_ibge,
            "codigo_modalidade": payload.codigo_modalidade,
            "pagina_inicial": payload.pagina,
            "max_paginas": payload.max_paginas,
            "tamanho_pagina": payload.tamanho_pagina,
            "fonte": "local_item_search",
            "quantidade_referencia": payload.quantidade_referencia,
            "unidade_medida_referencia": payload.unidade_medida_referencia,
            "valor_base_referencia": payload.valor_base_referencia,
            "variacao_percentual_referencia": payload.variacao_percentual_referencia,
            "variacao_sentido_referencia": (
                ref_sentido if funil.get("faixa_ativa") else None
            ),
            "faixa_regional_min": faixa_min,
            "faixa_regional_max": faixa_max,
        },
        "stats": out_stats,
        "itens": top3,
    }
