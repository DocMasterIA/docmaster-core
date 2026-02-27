"""
Recuperação de trechos relevantes e geração de resposta via LLM.

Usa LangChain para retriever + chain.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from .chroma_client import get_chroma_client
from .config import (
    CHROMA_COLLECTION,
    LLM_ORCHESTRATION_BASE_URL,
    LLM_ORCHESTRATION_GENERATE_PATH,
    OLLAMA_BASE_URL,
    RAG_TOP_K,
    RAG_HTTP_TIMEOUT,
)


def _get_embedding_function():
    """Retorna função de embeddings (Ollama)."""
    from langchain_community.embeddings import OllamaEmbeddings

    return OllamaEmbeddings(
        base_url=OLLAMA_BASE_URL,
        model="nomic-embed-text",
    )


def retrieve(
    query: str,
    collection_name: Optional[str] = None,
    top_k: Optional[int] = None,
    where: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Recupera trechos relevantes para a query.

    Args:
        query: Pergunta ou busca textual.
        collection_name: Coleção a consultar.
        top_k: Quantidade de trechos (None = usar config).
        where: Filtro ChromaDB por metadata (ex: {"document_type": "lei"}).

    Returns:
        Lista de dicts com content, score e metadata.
    """
    from langchain_chroma import Chroma

    k = top_k or RAG_TOP_K
    client = get_chroma_client()
    coll_name = collection_name or CHROMA_COLLECTION
    embeddings = _get_embedding_function()
    vectorstore = Chroma(
        collection_name=coll_name,
        embedding_function=embeddings,
        client=client,
    )
    search_kwargs: Dict[str, Any] = {"k": k}
    if where:
        search_kwargs["filter"] = where
    retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)
    docs = retriever.invoke(query)

    result = []
    for doc in docs:
        item: Dict[str, Any] = {"content": doc.page_content, "metadata": doc.metadata or {}}
        if hasattr(doc, "metadata") and isinstance(doc.metadata, dict):
            score = doc.metadata.get("score")
            if score is not None:
                item["score"] = float(score)
        result.append(item)
    return result


async def generate_answer(
    query: str,
    context_docs: List[Dict[str, Any]],
) -> str:
    """
    Gera resposta via llm_api usando o contexto recuperado.

    Args:
        query: Pergunta do usuário.
        context_docs: Trechos recuperados do RAG.

    Returns:
        Resposta gerada pelo LLM.
    """
    context = "\n\n".join(d.get("content", "") for d in context_docs)
    prompt = f"""Com base no contexto abaixo, responda à pergunta do usuário de forma objetiva e relevante.

Contexto:
{context}

Pergunta: {query}

Resposta:"""

    url = f"{LLM_ORCHESTRATION_BASE_URL}{LLM_ORCHESTRATION_GENERATE_PATH}"
    payload = {
        "prompt": prompt,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=RAG_HTTP_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        body = resp.json()
        # llm_api retorna {"ok": True, "data": {...}}; Ollama coloca o texto em "response"
        data = body.get("data", body) if isinstance(body, dict) else {}
        text = data.get("response", data.get("text", ""))
        return (text or "").strip()


async def check_compliance(
    text: str,
    collection_name: Optional[str] = None,
    top_k: Optional[int] = 5,
) -> Dict[str, Any]:
    """
    Verifica se o texto gerado está em conformidade com a Lei 14.133.

    Fluxo:
    1. Busca trechos da lei (document_type=lei) relevantes ao texto
    2. Envia texto + trechos da lei ao LLM
    3. LLM responde SIM/NÃO + observação breve

    Args:
        text: Texto gerado (cláusula, documento) a validar.
        collection_name: Coleção (default: config).
        top_k: Quantos trechos da lei recuperar.

    Returns:
        Dict com compliant (bool), observations (str), relevant_articles (list).
    """
    # Limita tamanho para não estourar contexto
    MAX_TEXT = 4000
    text_trimmed = (text or "").strip()[:MAX_TEXT]

    # 1. Busca trechos da lei relevantes (document_type=lei)
    docs = retrieve(
        query=text_trimmed,
        collection_name=collection_name,
        top_k=top_k,
        where={"document_type": "lei"},
    )

    # Fallback: se não encontrou "lei", tenta sem filtro (lei pode estar como "outro")
    if not docs:
        docs = retrieve(
            query=text_trimmed,
            collection_name=collection_name,
            top_k=top_k,
            where={"document_type": "outro"},
        )
        if docs:
            # Filtra só docs que parecem ser lei (arquivo contém lei/14133)
            law_docs = [
                d for d in docs
                if "lei" in (d.get("metadata") or {}).get("source_file", "").lower()
                or "14133" in (d.get("metadata") or {}).get("source_file", "")
            ]
            docs = law_docs if law_docs else docs[:1]  # usa ao menos 1 para não ficar vazio

    # Sem trechos da lei indexados
    if not docs:
        return {
            "compliant": None,
            "observations": "Nenhum trecho da Lei 14.133 encontrado. Ingeste a lei em /data/treinamento/LEI_14_133/ com document_type=lei.",
            "relevant_articles": [],
        }

    # 2. Monta prompt para o LLM
    context = "\n\n---\n\n".join(d.get("content", "")[:800] for d in docs)
    query_for_llm = f"""Você é um parecerista jurídico especializado na Lei 14.133/2021.

Você DEVE basear suas conclusões EXCLUSIVAMENTE:
- no texto a analisar fornecido abaixo; e
- nos trechos da Lei 14.133/2021 listados em "TRECHOS RELEVANTES DA LEI".

Regras rígidas:
- NÃO invente artigos, parágrafos, incisos ou decretos que não apareçam nos trechos fornecidos.
- Se precisar citar a lei, use apenas o que está em "TRECHOS RELEVANTES DA LEI" (mesmo que você conheça outros dispositivos).
- Se os trechos não forem suficientes para uma conclusão segura, diga explicitamente que não há base suficiente nos dispositivos apresentados, em vez de supor.
- Sempre explique, em linguagem clara, COMO o texto legal se relaciona com o caso concreto (passo a passo).
- Sua resposta deve ser técnica, mas sem copiar longos trechos da lei; resuma e aplique.

TRECHOS RELEVANTES DA LEI (Lei 14.133/2021):
{context}

TEXTO A ANALISAR:
{text_trimmed}

Pergunta: O texto acima está em conformidade com os trechos da Lei 14.133/2021 apresentados?

Formato da resposta (obrigatório):
1. Primeira linha: exatamente "SIM" ou "NÃO" (com base APENAS nos trechos da lei fornecidos).
2. Segunda linha: uma frase com a justificativa, mencionando quais trechos da lei suportam a conclusão ou por que não há base suficiente."""

    # 3. Chama LLM
    response_text = await generate_answer(query=query_for_llm, context_docs=docs)

    # 4. Extrai compliant (SIM/NÃO)
    resp_lower = (response_text or "").strip().lower()
    compliant = None
    first_line = resp_lower.split("\n")[0] if resp_lower else ""
    if "sim" in first_line and "não" not in first_line and "nao" not in first_line:
        compliant = True
    elif "não" in first_line or "nao" in first_line:
        compliant = False
    elif "sim" in resp_lower and ("não" in resp_lower or "nao" in resp_lower):
        compliant = False  # provavelmente "não está em conformidade"
    elif "sim" in resp_lower:
        compliant = True

    relevant_articles = [
        {"content": (d.get("content", "") or "")[:500], "metadata": d.get("metadata") or {}}
        for d in docs
    ]

    return {
        "compliant": compliant,
        "observations": (response_text or "").strip(),
        "relevant_articles": relevant_articles,
    }
