from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .pncp_client import PNCPClientError, search_contracts
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

    # Por enquanto usamos apenas user_prompt como termo de busca.
    # Se quiser, pode restringir o tamanho da string ou extrair palavra-chave com LLM.
    query = user_prompt.strip()[:300]

    try:
        refs = await search_contracts(
            query=query,
            municipio=municipio,
            uf=uf,
            modalidade=None,
            limit=limit,
        )
    except PNCPClientError:
        # Integração PNCP é melhor-esforço: se falhar, não deve quebrar a geração.
        return [], ""

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

