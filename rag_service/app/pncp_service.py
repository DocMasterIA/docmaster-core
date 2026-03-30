from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean, median
from typing import Any, Dict, List, Optional, Tuple

from .pncp_client import PNCPClientError
from .pncp_discovery import list_contracts_periodo
from .pncp_types import PNCPContractRef, pncp_contract_to_text


async def get_similar_contracts_for_request(
    user_prompt: str,
    user_context: Optional[Dict[str, Any]] = None,
    limit: int = 5,
) -> Tuple[List[PNCPContractRef], str]:
    """
    Retorna contratações similares no PNCP para um pedido de ETP/TR/DFD.

    - Usa user_prompt + contexto do usuário (município/UF/órgão) para montar a consulta.
    - Retorna:
        - lista de PNCPContractRef
        - texto curto pronto para ser injetado em prompts de LLM.
    """
    if not user_prompt or not user_prompt.strip():
        return [], ""

    ctx = user_context or {}
    usuario = ctx.get("usuario") or {}
    orgao = (usuario.get("orgao") or ctx.get("orgao") or "").strip() or None
    municipio = (ctx.get("municipio") or usuario.get("municipio") or "").strip() or None
    uf = (ctx.get("uf") or usuario.get("uf") or "").strip() or None

    try:
        # Modalidade 8 (dispensa) como padrão inicial para aderência ao fluxo atual.
        refs = await list_contracts_periodo(
            data_inicial=(datetime.utcnow() - timedelta(days=180)).strftime("%Y%m%d"),
            data_final=datetime.utcnow().strftime("%Y%m%d"),
            codigo_modalidade=8,
            codigo_municipio_ibge=municipio,
            uf=uf,
            limite=max(10, limit * 3),
        )
    except PNCPClientError:
        # Integração PNCP é melhor-esforço: se falhar, não deve quebrar a geração.
        return [], ""

    q_tokens = [t for t in user_prompt.lower().split() if len(t) >= 3][:12]
    if q_tokens:
        ranked: List[Tuple[int, PNCPContractRef]] = []
        for ref in refs:
            obj = (ref.objeto_resumido or "").lower()
            score = sum(1 for t in q_tokens if t in obj)
            if score > 0:
                ranked.append((score, ref))
        ranked.sort(key=lambda x: x[0], reverse=True)
        refs = [r for _, r in ranked] if ranked else refs

    refs = refs[:limit]
    if not refs:
        return [], ""

    linhas = []
    if orgao or municipio or uf:
        escopo = ", ".join(p for p in [orgao, municipio, uf] if p)
        if escopo:
            linhas.append(
                "Foram encontradas as seguintes contratações similares no Portal Nacional de Contratações Públicas (PNCP), "
                f"considerando o contexto do solicitante ({escopo}):"
            )
        else:
            linhas.append(
                "Foram encontradas as seguintes contratações similares no Portal Nacional de Contratações Públicas (PNCP):"
            )
    else:
        linhas.append(
            "Foram encontradas as seguintes contratações similares no Portal Nacional de Contratações Públicas (PNCP):"
        )

    for idx, ref in enumerate(refs, start=1):
        resumo = pncp_contract_to_text(ref)
        if not resumo:
            continue
        linhas.append(f"{idx}. {resumo}")

    texto = "\n".join(linhas)
    return refs, texto


async def search_market_prices(
    termo_busca: str,
    uf: Optional[str] = None,
    codigo_municipio_ibge: Optional[str] = None,
    data_inicial: Optional[str] = None,
    data_final: Optional[str] = None,
    codigo_modalidade: int = 8,
    limite: int = 80,
) -> Dict[str, Any]:
    """
    Busca contratações no PNCP e retorna um painel de preços/tendência.
    """
    hoje = datetime.utcnow().strftime("%Y%m%d")
    inicio_padrao = (datetime.utcnow() - timedelta(days=180)).strftime("%Y%m%d")
    di = data_inicial or inicio_padrao
    df = data_final or hoje

    refs = await list_contracts_periodo(
        data_inicial=di,
        data_final=df,
        codigo_modalidade=codigo_modalidade,
        uf=uf,
        codigo_municipio_ibge=codigo_municipio_ibge,
        limite=max(10, min(limite, 300)),
    )

    tokens = [t for t in (termo_busca or "").lower().split() if len(t) >= 3][:16]
    if tokens:
        filtered = []
        for ref in refs:
            obj = (ref.objeto_resumido or "").lower()
            if all(t in obj for t in tokens[:2]) or any(t in obj for t in tokens):
                filtered.append(ref)
        refs = filtered

    valores = [r.valor_global for r in refs if isinstance(r.valor_global, (int, float)) and r.valor_global > 0]
    stats = {
        "total_registros": len(refs),
        "com_valor": len(valores),
        "valor_min": min(valores) if valores else None,
        "valor_max": max(valores) if valores else None,
        "valor_medio": round(mean(valores), 2) if valores else None,
        "valor_mediano": round(median(valores), 2) if valores else None,
    }

    itens = []
    for r in refs[:50]:
        itens.append(
            {
                "numero_pncp": r.numero_pncp,
                "objeto_resumido": r.objeto_resumido,
                "orgao": r.orgao,
                "municipio": r.municipio,
                "uf": r.uf,
                "modalidade": r.modalidade,
                "valor_global": r.valor_global,
                "situacao": r.situacao,
                "tema_objeto": r.tema_objeto,
                "resumo_texto": pncp_contract_to_text(r),
            }
        )

    return {
        "ok": True,
        "filtros": {
            "termo_busca": termo_busca,
            "uf": uf,
            "codigo_municipio_ibge": codigo_municipio_ibge,
            "data_inicial": di,
            "data_final": df,
            "codigo_modalidade": codigo_modalidade,
        },
        "stats": stats,
        "itens": itens,
    }

