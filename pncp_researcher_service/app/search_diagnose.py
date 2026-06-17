from __future__ import annotations

from typing import Any, Dict

from .local_index import derive_anchor_search_term, local_item_search
from .schemas import MarketSearchRequest
from .service import _infer_search_bottleneck, market_search_intelligent


async def diagnose_intelligent_search(payload: MarketSearchRequest) -> Dict[str, Any]:
    """
    Compara disponibilidade no índice vs travas de filtro (homolog, faixa, scoring).
    Não persiste dados; útil para auditar cotações grandes (125+ itens).
    """
    limit = max(50, payload.max_paginas * payload.tamanho_pagina)
    termo_busca_raw = payload.termo_busca
    termo_efetivo, term_meta = derive_anchor_search_term(termo_busca_raw)

    common = dict(
        uf=payload.uf,
        municipio=payload.municipio,
        recortes_geograficos=payload.recortes_geograficos,
        codigo_modalidade=payload.codigo_modalidade,
        limit=limit,
        cleanup_for_display=False,
    )

    homolog = local_item_search(termo_busca_raw, somente_homologados=True, **common)
    qualquer = local_item_search(termo_busca_raw, somente_homologados=False, **common)

    payload_sem_faixa = payload.model_copy(
        update={
            "valor_base_referencia": None,
            "variacao_percentual_referencia": None,
        }
    )

    com_faixa = await market_search_intelligent(payload)
    sem_faixa = await market_search_intelligent(payload_sem_faixa)

    h_stats = homolog.get("stats") or {}
    q_stats = qualquer.get("stats") or {}
    cf_stats = com_faixa.get("stats") or {}
    sf_stats = sem_faixa.get("stats") or {}

    indice = {
        "homologados": int(h_stats.get("total_registros") or 0),
        "qualquer_situacao": int(q_stats.get("total_registros") or 0),
        "sql_rows_fetched": int(h_stats.get("sql_rows_fetched") or 0),
        "filtrados_token_match": int(h_stats.get("filtrados_token_match") or 0),
        "filtrados_nao_homologados": int(h_stats.get("filtrados_nao_homologados") or 0),
    }
    indice["perdidos_so_homolog"] = max(0, indice["qualquer_situacao"] - indice["homologados"])

    cf_funil = cf_stats.get("funil_busca") or {}
    sf_funil = sf_stats.get("funil_busca") or {}
    top3_com = len(com_faixa.get("itens") or [])
    top3_sem = len(sem_faixa.get("itens") or [])

    gargalo = cf_stats.get("provavel_gargalo") or _infer_search_bottleneck(cf_funil, top3_com)
    if top3_com == 0 and top3_sem > 0:
        gargalo = "faixa_preco"

    return {
        "ok": True,
        "termo": term_meta,
        "indice": indice,
        "inteligente_com_faixa": {
            "itens": top3_com,
            "funil": cf_funil,
            "gargalo": cf_stats.get("provavel_gargalo"),
        },
        "inteligente_sem_faixa": {
            "itens": top3_sem,
            "funil": sf_funil,
            "gargalo": sf_stats.get("provavel_gargalo"),
        },
        "provavel_gargalo": gargalo,
        "interpretacao": _interpret_diagnosis(gargalo, indice, top3_com, top3_sem),
    }


def _interpret_diagnosis(gargalo: str, indice: Dict[str, Any], top3_com: int, top3_sem: int) -> str:
    if top3_com >= 1:
        return "Item encontrado com filtros atuais."
    if gargalo == "faixa_preco" or (top3_sem > top3_com and top3_sem > 0):
        return (
            "Trava provável: faixa de preço (±% sobre valor base). "
            "Há candidatos no índice, mas preços PNCP ficam fora da faixa."
        )
    if gargalo == "indice_sem_match_fts":
        return "Termo não casa no índice (FTS/LIKE) — item pode não existir ou descrição muito específica."
    if gargalo == "token_match_and":
        return "Trava: match AND de tokens (descrição longa exige todas as palavras no item PNCP)."
    if gargalo == "filtro_homologados":
        return (
            "Trava: filtro homologados — há itens no índice, mas nenhum homologado/adjudicado para o termo."
        )
    if gargalo == "scoring_inteligente":
        return (
            "Trava: scoring da busca inteligente (proximidade de tokens / literal_match) "
            "após passar no índice local."
        )
    if indice.get("homologados", 0) == 0 and indice.get("qualquer_situacao", 0) == 0:
        return "Item provavelmente ausente no índice para este termo/recorte geográfico."
    return "Ver funil_busca nos stats da busca inteligente para detalhe por etapa."
