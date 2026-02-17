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
    RAG_HTTP_TIMEOUT,
    RAG_TOP_K,
)
from .retrieval import retrieve


# Prompt para composição de cláusulas (robusto, completo, não verboso)
CLAUSE_COMPOSITION_SYSTEM_PROMPT = """
Você é um agente de composição jurídica para documentos de licitação pública.

Sua função é gerar cláusulas COMPLETAS e ROBUSTAS, baseadas em exemplos reais fornecidos no contexto.

LÍNGUA E FORMATAÇÃO (obrigatório):
- Redija SEMPRE em português brasileiro (pt-BR). NUNCA use inglês ou outros idiomas.
- Use acentuação correta: resíduos, órgão, disposições, número, seqüência (ou sequência), § 1º, art. 1º, etc.
- NUNCA use formatação markdown: proibido **negrito**, *itálico*, ##, ---, | tabela |. O texto será inserido em documento Word; use apenas texto puro.
- Para listas, use parágrafos ou enumeração em prosa (primeiro, segundo; a) b) c)). Não use * ou - como marcadores.

Regras obrigatórias:
1. O texto gerado deve ser completo e autocontido – incluir todas as disposições necessárias para a cláusula, sem remeter a "conforme acima" ou "anexo".
2. Não ser verboso nem repetitivo – ir direto ao ponto, com clareza e precisão técnica.
3. Usar os exemplos do contexto RAG como referência – adaptar ao objeto/contexto informado, mantendo estrutura jurídica e requisitos essenciais.
4. Garantir conformidade com a Lei 14.133/2021 quando aplicável – prazos, valores, modalidades e disposições devem respeitar limites legais.
5. Incluir obrigações, prazos, responsabilidades e condições quando fizerem parte da natureza da cláusula.
6. NUNCA inventar fundamentos legais ou disposições que não estejam nos exemplos ou na lei – em dúvida, seja conservador.
7. O texto deve poder ser usado diretamente no documento – sem placeholder, sem "[preencher]", sem lacunas.
8. NUNCA use formatação markdown para tabelas (ex.: | col1 | col2 | ou linhas com ---). Tabelas são renderizadas em seções separadas pelo sistema. Se precisar mencionar dados tabulares, descreva em prosa ou indique "conforme tabela na seção correspondente".

Formato de saída: apenas o texto da cláusula, pronto para inserção no documento. Sem título, sem numeração, sem explicações adicionais. Texto puro, sem markdown.
- NUNCA faça meta-comentário: não escreva "A cláusula X deve conter...", "A cláusula \"Necessidade\" é fundamental...", "section_key: ...". Redija DIRETAMENTE o conteúdo da cláusula, como se já estivesse no documento final.
- NUNCA use títulos ou cabeçalhos no texto (ex.: "CONFORMIDADE COM A LEGISLAÇÃO", "Conclusão", "LISTA DE ALTERNATIVAS"). O título da seção já será inserido automaticamente.
"""


# Prompt para geração de linhas de tabela (retorno estruturado JSON)
TABLE_ROWS_SYSTEM_PROMPT = """
Você gera linhas de tabela para documentos de licitação. Sua saída DEVE ser APENAS um array JSON de objetos.

Regras:
- Retorne SOMENTE um array JSON: [{"col1": "val1", "col2": "val2"}, ...]
- Cada objeto representa uma linha; as chaves devem ser exatamente os nomes das colunas fornecidos.
- Valores em string, SEMPRE em português brasileiro. Valores monetários no formato "R$ X.XXX,XX".
- Gere 3 a 10 linhas realistas conforme o contexto (objeto, tipo de documento).
- NÃO escreva texto explicativo; NÃO use markdown; NÃO use ```.
"""


def _postprocess_clause_text(text: str) -> str:
    """
    Limpa saída do LLM antes de ir para o DOCX.
    Corrige markdown residual, acentuação comum e símbolos.
    """
    import re
    if not text or not isinstance(text, str):
        return text
    t = text.strip()
    # Remove **negrito** e *itálico* (markdown)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", t)
    # Corrige § No → § Nº (ordinal em parágrafos)
    t = re.sub(r"§\s*(\d+)\s*[oO](?=\s|$|\.|,)", r"§ \1º", t)
    t = re.sub(r"art\.?\s*(\d+)\s*[oO](?=\s|$|\.|,)", r"art. \1º", t)
    # Corrige erros comuns de português
    fixes = [
        (r"\btratante\b", "contratante"),
        (r"\bresiduos\b", "resíduos"),
        (r"\bresiduo\b", "resíduo"),
        (r"\borgao\b", "órgão"),
        (r"\borgaos\b", "órgãos"),
        (r"\bnumero\b", "número"),
        (r"\bnumeros\b", "números"),
        (r"\bdisposicoes\b", "disposições"),
        (r"\bsequencia\b", "sequência"),
        (r"\bseqüencia\b", "sequência"),
    ]
    for pat, repl in fixes:
        t = re.sub(pat, repl, t, flags=re.IGNORECASE)
    # Remove meta-comentários residuais (ex.: "A cláusula \"X\" (section_key: y) deve conter...")
    t = re.sub(
        r"A cláusula\s+[\"']?[^\"']+[\"']?\s*\([^)]*section_key[^)]*\)[^.]*\.?\s*",
        "",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"A cláusula\s+[\"']?[^\"']+[\"']?\s+(?:é fundamental|deve conter|deve abordar)[^.]*\.\s*",
        "",
        t,
        flags=re.IGNORECASE,
    )
    # Remove marcadores markdown no início de linha (* ou - , inclusive com espaços)
    t = re.sub(r"^\s*[\*\-]\s+", "", t, flags=re.MULTILINE)
    # Remove linhas vazias excessivas (mais de 2 seguidas)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


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
    """Chama llm_agent para obter estrutura, context e especificacoes a partir do prompt livre."""
    url = f"{LLM_AGENT_BASE_URL}/api/agent/structure-from-prompt"
    payload = {"user_prompt": user_prompt}
    async with httpx.AsyncClient(timeout=RAG_HTTP_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    if not data.get("ok") or not data.get("structure"):
        raise ValueError(data.get("error", "Estrutura não retornada pelo llm_agent"))
    return data


def _format_especificacoes(especificacoes: Dict[str, Any] | None) -> str:
    """Formata especificacoes (listas, tabelas) para inclusão no prompt."""
    if not especificacoes:
        return ""
    parts: List[str] = []
    if especificacoes.get("listas"):
        for key, items in especificacoes["listas"].items():
            if isinstance(items, list) and items:
                parts.append(f"- Lista '{key}': {', '.join(str(x) for x in items)}")
    if especificacoes.get("tabelas"):
        for key, tbl in especificacoes["tabelas"].items():
            if isinstance(tbl, dict) and tbl.get("colunas"):
                cols = ", ".join(str(c) for c in tbl["colunas"])
                parts.append(f"- Tabela '{key}' (colunas: {cols}) – será renderizada em seção própria; NÃO gere tabela em markdown aqui")
    if not parts:
        return ""
    return "Especificações indicadas pelo usuário (use quando fizer sentido para esta seção):\n" + "\n".join(parts) + "\n\n"


async def _generate_clause_text(
    section_key: str,
    section_title: str,
    context: Dict[str, Any],
    rag_context: str,
    document_type: str,
    especificacoes: Dict[str, Any] | None = None,
) -> str:
    """Gera texto da cláusula via LLM usando contexto RAG, seção e especificacoes."""
    espec_text = _format_especificacoes(especificacoes)
    query = f"""Gerar o texto COMPLETO da cláusula "{section_title}" (section_key: {section_key}).

Contexto do documento:
- Tipo: {document_type}
- Objeto: {context.get("objeto", "não informado")}
- Órgão: {context.get("orgao", "não informado")}
- Modalidade: {context.get("modalidade", "não informado")}

{espec_text}EXEMPLOS DE CLÁUSULAS SIMILARES (extraídos de documentos reais):
{rag_context}

Instruções: Gere o CONTEÚDO da cláusula diretamente, sem meta-comentário ("A cláusula deve...", "section_key", títulos). Sempre em português brasileiro com acentuação correta. Adapte ao contexto (objeto, órgão) mantendo a estrutura jurídica dos exemplos. Use listas em prosa quando fizer sentido; tabelas são renderizadas em seções separadas. Nunca use markdown (** * ## ---). Não seja verboso; seja preciso e completo."""

    full_prompt = f"<<SYSTEM>>\n{CLAUSE_COMPOSITION_SYSTEM_PROMPT.strip()}\n\n<<USER>>\n{query}"
    url = f"{LLM_ORCHESTRATION_BASE_URL}{LLM_ORCHESTRATION_GENERATE_PATH}"
    payload = {"prompt": full_prompt, "stream": False}

    async with httpx.AsyncClient(timeout=RAG_HTTP_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        body = resp.json()
    data = body.get("data", body) if isinstance(body, dict) else {}
    text = data.get("response", data.get("text", ""))
    raw = (text or "").strip()
    return _postprocess_clause_text(raw)


def _collect_text_sections(nodes: List[Dict], acc: List[Dict]) -> None:
    """Coleta seções com content_type=text (incluindo subseções)."""
    for node in nodes:
        if node.get("content_type") == "text":
            acc.append({"key": node["key"], "title": node.get("title", node["key"])})
        if node.get("children"):
            _collect_text_sections(node["children"], acc)


def _collect_table_sections(nodes: List[Dict], acc: List[Dict]) -> None:
    """Coleta seções com content_type=table (incluindo subseções)."""
    for node in nodes:
        if node.get("content_type") == "table":
            schema = node.get("table_schema") or {}
            cols = schema.get("columns") or []
            acc.append({
                "key": node["key"],
                "title": node.get("title", node["key"]),
                "columns": [{"key": c.get("key"), "label": c.get("label", c.get("key", ""))} for c in cols],
            })
        if node.get("children"):
            _collect_table_sections(node["children"], acc)


def _parse_table_rows_json(raw: str) -> List[Dict[str, Any]]:
    """Extrai array JSON de linhas da resposta do LLM (aceita markdown, etc)."""
    import json
    import re

    text = (raw or "").strip()
    # Remove ```json ... ```
    if "```" in text:
        m = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text)
        if m:
            text = m.group(1)
    # Procura primeiro [...]
    start = text.find("[")
    if start < 0:
        return []
    depth = 0
    for i, c in enumerate(text[start:], start=start):
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                try:
                    out = json.loads(text[start : i + 1])
                    return out if isinstance(out, list) else []
                except json.JSONDecodeError:
                    pass
                break
    return []


async def _generate_table_rows(
    section_key: str,
    section_title: str,
    columns: List[Dict[str, str]],
    context: Dict[str, Any],
    document_type: str,
    rag_context: str,
) -> List[Dict[str, Any]]:
    """Gera linhas de tabela via LLM; retorna lista de dicts ou vazia em falha."""
    col_labels = [c.get("label") or c.get("key") or "" for c in columns if c.get("label") or c.get("key")]
    if not col_labels:
        return []

    query = f"""Gerar linhas para a tabela "{section_title}" (section_key: {section_key}).

Contexto: {document_type}. Objeto: {context.get("objeto", "não informado")}. Órgão: {context.get("orgao", "não informado")}.

Colunas (use exatamente esses nomes como chaves em cada objeto): {", ".join(col_labels)}

Exemplos de conteúdo similar (referência):
{rag_context[:800] if rag_context else "Nenhum."}

Retorne APENAS um array JSON de objetos, cada um com as chaves das colunas. Exemplo: [{{"{col_labels[0]}": "val1", "{col_labels[1] if len(col_labels) > 1 else col_labels[0]}": "val2"}}, ...]"""

    full_prompt = f"<<SYSTEM>>\n{TABLE_ROWS_SYSTEM_PROMPT.strip()}\n\n<<USER>>\n{query}"
    url = f"{LLM_ORCHESTRATION_BASE_URL}{LLM_ORCHESTRATION_GENERATE_PATH}"
    payload = {"prompt": full_prompt, "stream": False}

    try:
        async with httpx.AsyncClient(timeout=RAG_HTTP_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            body = resp.json()
        data = body.get("data", body) if isinstance(body, dict) else {}
        raw = data.get("response", data.get("text", ""))
        rows = _parse_table_rows_json(str(raw or ""))
        if not isinstance(rows, list):
            return []
        # Validar: cada item deve ser dict
        return [r for r in rows if isinstance(r, dict)][:20]
    except Exception:
        return []


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
    # Context e especificacoes vêm do llm_agent (retornado em structure-from-prompt)
    ctx = resp.get("context") or {}
    especificacoes = resp.get("especificacoes")
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
                especificacoes=especificacoes,
            )
            section_texts[key] = text
        except Exception as e:
            section_texts[key] = f"[Erro ao gerar: {e}]"

    # Table data: inicialmente de especificacoes (linhas_sugeridas)
    table_data: Dict[str, List[Dict[str, Any]]] = {}
    espec_tabelas = especificacoes.get("tabelas") if isinstance(especificacoes, dict) else {}
    if espec_tabelas:
        for k, v in espec_tabelas.items():
            if isinstance(v, dict):
                linhas = v.get("linhas_sugeridas")
                if isinstance(linhas, list) and linhas:
                    table_data[k] = linhas

    # Seções de tabela sem dados: gerar linhas via LLM
    table_sections: List[Dict] = []
    _collect_table_sections(root, table_sections)
    for sec in table_sections:
        key = sec["key"]
        if table_data.get(key):
            continue
        cols = sec.get("columns") or []
        if not cols:
            continue
        query = f"{ctx.get('objeto', '')} tabela {sec.get('title', key)} estimativa custos"
        docs = retrieve(
            query=query,
            collection_name=coll,
            top_k=3,
            where={"document_type": doc_type_filter},
        )
        rag_ctx = "\n\n---\n\n".join((d.get("content", "") or "")[:500] for d in docs)
        rows = await _generate_table_rows(
            section_key=key,
            section_title=sec.get("title", key),
            columns=cols,
            context=ctx,
            document_type=document_type,
            rag_context=rag_ctx,
        )
        if rows:
            table_data[key] = rows

    return {
        "structure": doc_structure,
        "section_texts": section_texts,
        "document_type": document_type,
        "context": ctx,
        "especificacoes": especificacoes,
        "table_data": table_data,
    }