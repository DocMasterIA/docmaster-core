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
    RAG_TIMEOUT,
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
) -> List[Dict[str, Any]]:
    """
    Recupera trechos relevantes para a query.

    Args:
        query: Pergunta ou busca textual.
        collection_name: Coleção a consultar.
        top_k: Quantidade de trechos (None = usar config).

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
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
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

    async with httpx.AsyncClient(timeout=RAG_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        body = resp.json()
        # llm_api retorna {"ok": True, "data": {...}}; Ollama coloca o texto em "response"
        data = body.get("data", body) if isinstance(body, dict) else {}
        text = data.get("response", data.get("text", ""))
        return (text or "").strip()
