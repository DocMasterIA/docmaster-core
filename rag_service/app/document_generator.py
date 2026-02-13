"""
Geração de documento completo: estrutura + textos de cláusulas.

Fluxo:
1. Interpreta prompt do usuário e obtém estrutura via llm_agent
2. Para cada seção: recupera exemplos do RAG e gera texto via LLM
3. Retorna estrutura + textos de cláusulas robustos e completos
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from .config import (
    CHROMA_COLLECTION,
    LLM_AGENT_BASE_URL,
    LLM_ORCHESTRATION_BASE_URL,
    LLM_ORCHESTRATION_GENERATE_PATH,
    OLLAMA_BASE_URL,
    RAG_TIMEOUT,
    RAG_TOP_K,
)
from .retrieval import retrieve


# Prompt para composição de cláusulas (robusto, completo, não verboso)
CLAUSE_COMPOSITION_SYSTEM_PROMPT = """
Você é um agente de composição jurídica para documentos de licitação pública.

Sua função é gerar cláusulas COMPLETAS e ROBUSTAS, baseadas em exemplos reais fornecidos no contexto.

Regras obrigatórias:
1. O texto gerado deve ser completo e autocontido – incluir todas as disposições necessárias para a cláusula, sem remeter a "conforme acima" ou "anexo".
2. Não ser verboso nem repetitivo – ir direto ao ponto, com clareza e precisão técnica.
3. Usar os exemplos do contexto RAG como referência – adaptar ao objeto/contexto informado, mantendo estrutura jurídica e requisitos essenciais.
4. Garantir conformidade com a Lei 14.133/2021 quando aplicável – prazos, valores, modalidades e disposições devem respeitar limites legais.
5. Incluir obrigações, prazos, responsabilidades e condições quando fizerem parte da natureza da cláusula.
6. NUNCA inventar fundamentos legais ou disposições que não estejam nos exemplos ou na lei – em dúvida, seja conservador.
7. O texto deve poder ser usado diretamente no documento – sem placeholder, sem "[preencher]", sem lacunas.

Formato de saída: apenas o texto da cláusula, pronto para inserção no documento. Sem título, sem numeração, sem explicações adicionais.
"""


def _document_type_to_rag_filter(document_type: str) -> str:
    """Mapeia document_type do llm_agent para document_type do RAG."""
    dt = (document_type or "").lower()
    if "termo" in dt or dt == "termo_referencia":
        return "termo_referencia"
    if "estudo" in dt or "etp" in dt or dt == "estudo_tecnico_preliminar":
        return "etp"
    if "formalizacao" in dt or "demanda" in dt or dt == "documento_formalizacao_demanda":
        return "dfd"
    return document_type


async def _call_llm_agent_structure(user_prompt: str) -> Dict[str, Any]:
    """Chama llm_agent para obter estrutura a partir do prompt livre."""
    url = f"{LLM_AGENT_BASE_URL}/api/agent/structure-from-prompt"
    payload = {"user_prompt": user_prompt}
    async with httpx.AsyncClient(timeout=RAG_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    if not data.get("ok") or not data.get("structure"):
        raise ValueError(data.get("error", "Estrutura não retornada pelo llm_agent"))
    return data["structure"]


async def _generate_clause_text(
    section_key: str,
    section_title: str,
    context: Dict[str, Any],
    rag_context: str,
    document_type: str,
) -> str:
    """Gera texto da cláusula via LLM usando contexto RAG e seção."""
    query = f"""Gerar o texto COMPLETO da cláusula "{section_title}" (section_key: {section_key}).

Contexto do documento:
- Tipo: {document_type}
- Objeto: {context.get("objeto", "não informado")}
- Órgão: {context.get("orgao", "não informado")}
- Modalidade: {context.get("modalidade", "não informado")}

EXEMPLOS DE CLÁUSULAS SIMILARES (extraídos de documentos reais):
{rag_context}

Instruções: Gere um texto completo, robusto e pronto para uso. Adapte ao contexto (objeto, órgão) mantendo a estrutura jurídica dos exemplos. Não seja verboso; seja preciso e completo."""

    full_prompt = f"<<SYSTEM>>\n{CLAUSE_COMPOSITION_SYSTEM_PROMPT.strip()}\n\n<<USER>>\n{query}"
    url = f"{LLM_ORCHESTRATION_BASE_URL}{LLM_ORCHESTRATION_GENERATE_PATH}"
    payload = {"prompt": full_prompt, "stream": False}

    async with httpx.AsyncClient(timeout=RAG_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        body = resp.json()
    data = body.get("data", body) if isinstance(body, dict) else {}
    text = data.get("response", data.get("text", ""))
    return (text or "").strip()


def _collect_text_sections(nodes: List[Dict], acc: List[Dict]) -> None:
    """Coleta seções com content_type=text (incluindo subseções)."""
    for node in nodes:
        if node.get("content_type") == "text":
            acc.append({"key": node["key"], "title": node.get("title", node["key"])})
        if node.get("children"):
            _collect_text_sections(node["children"], acc)


async def generate_full_document(
    user_prompt: str,
    collection_name: Optional[str] = None,
    top_k_per_section: int = 5,
) -> Dict[str, Any]:
    """
    Gera documento completo: estrutura + textos de cláusulas.

    Fluxo:
    1. Chama llm_agent para interpretar prompt e obter estrutura
    2. Para cada seção de texto: recupera exemplos do RAG
    3. Gera texto de cada cláusula via LLM com contexto RAG
    4. Retorna estrutura + section_texts

    Args:
        user_prompt: Pedido livre (ex.: "gerar ETP para coleta seletiva")
        collection_name: Coleção RAG (default: config)
        top_k_per_section: Quantos exemplos recuperar por seção

    Returns:
        Dict com structure, section_texts, context
    """
    resp = await _call_llm_agent_structure(user_prompt)
    doc_structure = resp.get("structure") or resp
    document_type = doc_structure.get("document_type", "termo_referencia")
    doc_type_filter = _document_type_to_rag_filter(document_type)
    # Context vem do llm_agent (retornado em structure-from-prompt)
    ctx = resp.get("context") or {}
    if not isinstance(ctx, dict):
        ctx = {}
    if not ctx.get("objeto"):
        ctx["objeto"] = user_prompt[:400].strip() or "Documento solicitado"

    # Coleta seções que precisam de texto
    text_sections: List[Dict[str, str]] = []
    root = doc_structure.get("root_sections", [])
    _collect_text_sections(root, text_sections)

    section_texts: Dict[str, str] = {}
    coll = collection_name or CHROMA_COLLECTION

    for sec in text_sections:
        key = sec["key"]
        title = sec["title"]
        # Query RAG: busca exemplos da seção + contexto
        query = f"{ctx.get('objeto', '')} cláusula {title} {key}"
        docs = retrieve(
            query=query,
            collection_name=coll,
            top_k=top_k_per_section,
            where={"document_type": doc_type_filter},
        )
        # Fallback sem filtro se não encontrou
        if not docs:
            docs = retrieve(
                query=query,
                collection_name=coll,
                top_k=top_k_per_section,
            )
        rag_context = "\n\n---\n\n".join(
            (d.get("content", "") or "")[:600] for d in docs
        )
        if not rag_context:
            rag_context = "(Nenhum exemplo encontrado no RAG. Gere uma cláusula genérica mas completa e robusta.)"
        try:
            text = await _generate_clause_text(
                section_key=key,
                section_title=title,
                context=ctx,
                rag_context=rag_context,
                document_type=document_type,
            )
            section_texts[key] = text
        except Exception as e:
            section_texts[key] = f"[Erro ao gerar: {e}]"

    return {
        "structure": doc_structure,
        "section_texts": section_texts,
        "document_type": document_type,
        "context": ctx,
    }