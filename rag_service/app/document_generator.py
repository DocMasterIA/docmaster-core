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
    RAG_POSTPROCESS,
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
4. LEGISLAÇÃO: Use APENAS a Lei 14.133/2021. NUNCA cite a Lei 8.666/1993 (foi revogada em 2021).
5. Incluir obrigações, prazos, responsabilidades e condições quando fizerem parte da natureza da cláusula.
6. NUNCA inventar fundamentos legais ou disposições que não estejam nos exemplos ou na lei – em dúvida, seja conservador.
7. NUNCA use placeholders: proibido [preencher], [prazo determinado], [valor], [X], [objeto], etc. Use valores genéricos plausíveis quando não houver dado específico (ex.: "30 dias", "conforme edital", "no prazo estabelecido no contrato").
8. NUNCA repita frases ou parágrafos idênticos – cada seção deve ter redação própria e específica. Evite fórmulas genéricas repetidas (ex.: "encontra-se detalhada nas partes específicas").
9. NUNCA use formatação markdown para tabelas (ex.: | col1 | col2 | ou linhas com ---). Tabelas são renderizadas em seções separadas pelo sistema. Se precisar mencionar dados tabulares, descreva em prosa ou indique "conforme tabela na seção correspondente".

Formato de saída: apenas o texto da cláusula, pronto para inserção no documento. Sem título, sem numeração, sem explicações adicionais. Texto puro, sem markdown.
- NUNCA faça meta-comentário: não escreva "A cláusula X deve conter...", "A cláusula \"Necessidade\" é fundamental...", "section_key: ...". Redija DIRETAMENTE o conteúdo da cláusula, como se já estivesse no documento final.
- NUNCA use títulos ou cabeçalhos no texto (ex.: "CONFORMIDADE COM A LEGISLAÇÃO", "Conclusão", "LISTA DE ALTERNATIVAS"). O título da seção já será inserido automaticamente.
"""


# Prompt para geração de listas (Obrigações, Critérios de Aceitação, etc.)
LIST_COMPOSITION_SYSTEM_PROMPT = """
Você gera itens de lista para seções de documentos de licitação (obrigações, critérios de aceitação, etc.).

LÍNGUA: Sempre português brasileiro com acentuação correta.

FORMATO DE SAÍDA: Cada item em UMA LINHA separada. NÃO use numeração (1. 2. 3.) nem marcadores (- * •). Apenas o texto de cada item, um por linha. O sistema aplicará os marcadores automaticamente.

Regras:
- Gere 3 a 8 itens conforme a natureza da seção e do objeto.
- Baseie-se nos exemplos do contexto RAG quando disponíveis.
- Cada item deve ser conciso e completo (frase ou oração).
- Sem markdown, sem meta-comentários.
- NUNCA use placeholders: proibido [preencher], [prazo], [valor], [X], etc. Use valores genéricos plausíveis (ex.: "30 dias", "conforme edital").
- LEGISLAÇÃO: Use APENAS a Lei 14.133/2021. NUNCA cite a Lei 8.666/1993 (foi revogada).
- Diferencie obrigações da CONTRATADA (empresa/fornecedor) das do CONTRATANTE (Administração): o sujeito deve ser correto em cada tipo de seção.
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


def _convert_markdown_table_to_plain(text: str) -> str:
    """
    Converte blocos de tabela markdown (| col | col | + | --- | + | val |)
    em lista numerada legível, preservando o conteúdo.
    """
    import re
    if not text or "|" not in text:
        return text
    lines = text.split("\n")
    result: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detecta início de tabela markdown: linha com | ... |
        if re.match(r"^\s*\|.+\|\s*$", line):
            block: List[str] = [line]
            j = i + 1
            while j < len(lines) and re.match(r"^\s*\|.+\|\s*$", lines[j]):
                block.append(lines[j])
                j += 1
            # Parse: header, separador (|---|), dados
            rows: List[List[str]] = []
            for bl in block:
                cells = [c.strip() for c in bl.strip().strip("|").split("|")]
                if not cells:
                    continue
                # Pula linha separadora (só --- ou vazio)
                if all(re.match(r"^[\s\-:]*$", c) for c in cells):
                    continue
                rows.append(cells)
            if len(rows) >= 2:
                # Converte em lista numerada (preserva conteúdo das células)
                conv = []
                for i, row in enumerate(rows[1:], 1):
                    clean = " – ".join(c for c in row if c)
                    if clean:
                        conv.append(f"{i}. {clean}")
                if conv:
                    result.append("\n".join(conv))
                    i = j
                    if i < len(lines) and lines[i].strip():
                        result.append("")
                    continue
        result.append(line)
        i += 1
    return "\n".join(result)


def _postprocess_clause_text(text: str) -> str:
    """
    Limpa saída do LLM antes de ir para o DOCX.

    Filosofia: corrigir apenas erros claros (typos, markdown residual, símbolos).
    NÃO restringe conteúdo; removemos só meta-comentários explícitos e títulos duplicados.
    Para desativar: RAG_POSTPROCESS=0 (retorna texto bruto do modelo).
    """
    import re
    if not text or not isinstance(text, str):
        return text
    if not RAG_POSTPROCESS:
        return text.strip()
    t = text.strip()
    # Remove **negrito** e *itálico* (markdown)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", t)
    # Corrige § No → § Nº (ordinal em parágrafos)
    t = re.sub(r"§\s*(\d+)\s*[oO](?=\s|$|\.|,)", r"§ \1º", t)
    t = re.sub(r"art\.?\s*(\d+)\s*[oO](?=\s|$|\.|,)", r"art. \1º", t)
    # Leis revogadas: corrige para Lei 14.133/2021
    t = re.sub(r"Lei\s*(?:n[º°]?|n\.?\s*[º°]?)?\s*8\.666/1993", "Lei 14.133/2021", t, flags=re.IGNORECASE)
    t = re.sub(r"Lei\s*8\.666", "Lei 14.133/2021", t, flags=re.IGNORECASE)
    t = re.sub(r"Lei\s*(?:n[º°]?|n\.?\s*[º°]?)?\s*8\.333/1991", "Lei 14.133/2021", t, flags=re.IGNORECASE)
    t = re.sub(r"Lei\s*8\.333", "Lei 14.133/2021", t, flags=re.IGNORECASE)
    # Placeholders: substitui por texto genérico plausível
    placeholder_fixes = [
        (r"R\$\s*\[conforme\s+edital\]", "conforme edital"),
        (r"\[prazo\s+determinado\]", "no prazo estabelecido no edital"),
        (r"\[conforme\s+edital\]", "conforme edital"),
        (r"\[preencher\]", "conforme especificado no edital"),
        (r"\[valor\]", "o valor estabelecido no contrato"),
        (r"\[objeto\]", "o objeto da contratação"),
        (r"\[X\]", "conforme edital"),
    ]
    for pat, repl in placeholder_fixes:
        t = re.sub(pat, repl, t, flags=re.IGNORECASE)
    # Corrige erros comuns de português
    fixes = [
        (r"\btratante\b", "contratante"),
        (r"\bmodificiem\b", "modifiquem"),
        (r"\bo equipamentos\b", "os equipamentos"),
        (r"será verificado a conformidade", "será verificada a conformidade"),
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
    # Remove meta-comentários explícitos (só quando o nome da cláusula está entre aspas - auto-referência)
    # Ex.: "A cláusula \"Necessidade\" é fundamental..." - NÃO remove "A cláusula de garantia deve..."
    t = re.sub(
        r"A cláusula\s+[\"'][^\"']+[\"']\s*\([^)]*section_key[^)]*\)[^.]*\.?\s*",
        "",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"A cláusula\s+[\"'][^\"']+[\"']\s+(?:é fundamental|deve conter|deve abordar)[^.]*\.\s*",
        "",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"A presente cláusula tem como objetivo estabelecer[^.]*\.\s*",
        "",
        t,
        flags=re.IGNORECASE,
    )
    # Converte tabelas markdown (| col1 | col2 | + | --- | + | val |) em lista legível
    t = _convert_markdown_table_to_plain(t)
    # Remove marcadores markdown no início de linha (* ou - , inclusive com espaços)
    t = re.sub(r"^\s*[\*\-]\s+", "", t, flags=re.MULTILINE)
    # Remove meta-comentários do LLM (intro listas, section_key, etc.)
    meta_comment_patterns = [
        r"^Aqui estão os itens da lista para a seção[^\n]*(?:\n|$)",
        r"^Segue(?:m)? os itens da (?:lista )?para a seção[^\n]*(?:\n|$)",
        r"^(?:Os )?itens da seção[^\n]*(?:\n|$)",
        r"^Lista de itens para a seção[^\n]*(?:\n|$)",
        r"^.*\(section_key\s*:\s*[a-z_]+\)[^.\n]*\.?\s*(?:\n|$)",
    ]
    for pat in meta_comment_patterns:
        t = re.sub(pat, "", t, flags=re.IGNORECASE)

    # Remove títulos/cabeçalhos no início do texto (o título da seção já é inserido automaticamente)
    heading_patterns = [
        r"^Conclusão\s*(?:e\s+Recomendações?\s*(?:Finais?)?)?\.?\s*\n+",
        r"^CONFORMIDADE\s+COM\s+A\s+LEGISLAÇÃO\.?\s*\n+",
        r"^LISTA\s+DE\s+ALTERNATIVAS\.?\s*\n+",
        r"^LISTA\s+DE\s+MEDIDAS\.?\s*\n+",
        r"^Análise\s+de\s+Riscos\.?\s*\n+",
        r"^SOLUÇÃO\s+PROPOSTA\.?\s*\n+",
    ]
    for pat in heading_patterns:
        t = re.sub(pat, "", t, flags=re.IGNORECASE)
    # Remove linhas vazias excessivas (mais de 2 seguidas)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _sanitize_rag_context_for_legislation(rag_context: str) -> str:
    """
    Substitui referências a leis revogadas (8.666, 8.333) no contexto RAG por Lei 14.133/2021.
    Assim o LLM recebe exemplos já atualizados e não replica as leis antigas.
    """
    import re
    if not rag_context or not isinstance(rag_context, str):
        return rag_context
    t = rag_context
    # Lei 8.666/1993 (licitações - revogada pela 14.133/2021)
    t = re.sub(r"Lei\s*(?:n[º°]?|n\.?\s*[º°]?)?\s*8\.666/1993", "Lei 14.133/2021", t, flags=re.IGNORECASE)
    t = re.sub(r"Lei\s*8\.666(?:/1993)?", "Lei 14.133/2021", t, flags=re.IGNORECASE)
    # Lei 8.333/1991 (orçamento - quando citada em contexto licitatório, priorizar 14.133)
    t = re.sub(r"Lei\s*(?:n[º°]?|n\.?\s*[º°]?)?\s*8\.333/1991", "Lei 14.133/2021", t, flags=re.IGNORECASE)
    t = re.sub(r"Lei\s*8\.333(?:/1991)?", "Lei 14.133/2021", t, flags=re.IGNORECASE)
    return t


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


def _get_section_specific_instructions(section_key: str, for_list: bool = False) -> str:
    """
    Retorna instruções específicas por seção para guiar a geração.
    for_list=True: instruções condensadas para itens de lista.
    """
    key = (section_key or "").lower()

    # Obrigações da Contratada (empresa que executa)
    if "contratada" in key:
        if for_list:
            return "\nINSTRUÇÕES ESPECÍFICAS: Cada item deve descrever obrigação da CONTRATADA (empresa, fornecedor, licitante). NÃO inclua deveres da Administração. Ex.: \"Apresentar cronograma de execução\", \"Manter documentação atualizada\".\n"
        return "\nINSTRUÇÕES ESPECÍFICAS: O sujeito das obrigações é a CONTRATADA (empresa, fornecedor, licitante que executa o serviço). NÃO inclua obrigações da Administração. Redija deveres da empresa em relação ao contrato.\n"

    # Obrigações do Contratante (Administração que contrata)
    if "contratante" in key:
        if for_list:
            return "\nINSTRUÇÕES ESPECÍFICAS: Cada item deve descrever obrigação do CONTRATANTE (Administração, órgão). NÃO inclua deveres da empresa. Ex.: \"Fornecer dados necessários à execução\", \"Efetuar pagamento conforme cronograma\".\n"
        return "\nINSTRUÇÕES ESPECÍFICAS: O sujeito das obrigações é o CONTRATANTE (Administração Pública, órgão, poder público). NÃO inclua obrigações da empresa contratada. Redija deveres da Administração em relação ao contrato.\n"

    # Critérios de Aceitação / Julgamento
    if "criterios" in key or "aceitacao" in key or "julgamento" in key:
        if for_list:
            return "\nINSTRUÇÕES ESPECÍFICAS: Liste critérios de aceitação ou de julgamento de propostas. Cite APENAS a Lei 14.133/2021 (não a Lei 8.666). Ex.: \"Conformidade com as especificações técnicas\", \"Menor preço global\".\n"
        return "\nINSTRUÇÕES ESPECÍFICAS: Descreva os critérios de aceitação e/ou julgamento das propostas. Cite APENAS a Lei 14.133/2021 (não a Lei 8.666). Evite repetir \"menor preço\" ou fórmulas genéricas em excesso.\n"

    # Requisitos Técnicos
    if "requisitos" in key and "tecnic" in key:
        if for_list:
            return "\nINSTRUÇÕES ESPECÍFICAS: Liste requisitos técnicos específicos do objeto (equipamentos, capacidades, qualificações). Cada item deve ser verificável e mensurável.\n"
        return "\nINSTRUÇÕES ESPECÍFICAS: Especifique requisitos técnicos objetivos (capacidade, desempenho, qualificação). Evite vagas genéricas; seja específico ao objeto.\n"

    # Justificativa
    if "justificativa" in key:
        if for_list:
            return "\nINSTRUÇÕES ESPECÍFICAS: Liste argumentos que justifiquem as exigências. NÃO repita \"encontra-se detalhada nas partes específicas\". Cada item deve trazer justificativa concreta.\n"
        return "\nINSTRUÇÕES ESPECÍFICAS: Justifique as exigências de forma objetiva. NÃO use fórmulas genéricas repetidas (ex.: \"encontra-se detalhada nas partes específicas deste documento\"). Apresente argumentos concretos.\n"

    # Prazo de Execução
    if "prazo" in key and "execuc" in key:
        if for_list:
            return "\nINSTRUÇÕES ESPECÍFICAS: Liste prazos e condições. Quem EXECUTA é a CONTRATADA (empresa), não a Administração. Use valores plausíveis (ex.: \"180 dias\", \"30 dias\").\n"
        return "\nINSTRUÇÕES ESPECÍFICAS: O prazo de execução é da CONTRATADA (empresa que executa o serviço). NÃO escreva que \"a Administração executará\". Use prazos em dias conforme Lei 14.133/2021.\n"

    # Garantia
    if "garantia" in key:
        if for_list:
            return "\nINSTRUÇÕES ESPECÍFICAS: Liste tipos de garantia (proposta, execução, etc.) e percentuais. Lei 14.133: garantia de proposta até 5% do valor estimado. NÃO cite Lei 8.666.\n"
        return "\nINSTRUÇÕES ESPECÍFICAS: Garantia de proposta não superior a 5% (Lei 14.133/2021). NÃO cite Lei 8.666. Especifique prazos de devolução e exigência.\n"

    # Forma de Pagamento
    if "pagamento" in key or "forma_pagamento" in key:
        if for_list:
            return "\nINSTRUÇÕES ESPECÍFICAS: Liste condições de pagamento (parcelas, datas, documentos). Use valores ou percentuais plausíveis, nunca placeholders.\n"
        return "\nINSTRUÇÕES ESPECÍFICAS: Descreva forma e condições de pagamento. Use prazos concretos (ex.: \"30 dias após a entrega\"). NÃO use [prazo] ou [valor].\n"

    # Objeto
    if key == "objeto" or key.startswith("objeto_"):
        if for_list:
            return "\nINSTRUÇÕES ESPECÍFICAS: Liste as partes ou modalidades do objeto. Seja específico ao contexto (serviços, bens).\n"
        return "\nINSTRUÇÕES ESPECÍFICAS: Defina o objeto da contratação com clareza. Inclua escopo, alcance e excludentes. Adapte ao contexto informado.\n"

    # Necessidade
    if "necessidade" in key:
        if for_list:
            return "\nINSTRUÇÕES ESPECÍFICAS: Liste motivos da necessidade (legal, operacional, técnico). Evite repetir frases de outras seções.\n"
        return "\nINSTRUÇÕES ESPECÍFICAS: Fundamente a necessidade da contratação. Evite fórmulas genéricas; adapte ao objeto e ao órgão.\n"

    # Gestão e Fiscalização
    if "gestao" in key or "fiscalizacao" in key or "acompanhamento" in key:
        if for_list:
            return "\nINSTRUÇÕES ESPECÍFICAS: Liste etapas, responsáveis ou ações de gestão/fiscalização. Diferencie responsabilidade da Administração da da contratada.\n"
        return "\nINSTRUÇÕES ESPECÍFICAS: Descreva competências de gestão e fiscalização. Diferencie o papel da Administração (fiscalizar) do da contratada (executar).\n"

    # Conformidade com Legislação
    if "conformidade" in key or "legislacao" in key or "legislação" in key:
        if for_list:
            return "\nINSTRUÇÕES ESPECÍFICAS: Liste leis e normas aplicáveis. Priorize Lei 14.133/2021. NÃO cite Lei 8.666/1993.\n"
        return "\nINSTRUÇÕES ESPECÍFICAS: Indique conformidade com Lei 14.133/2021 e normas aplicáveis. NÃO cite Lei 8.666/1993 (revogada).\n"

    return ""


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
    section_hint = _get_section_specific_instructions(section_key, for_list=False)
    query = f"""Gerar o texto COMPLETO da cláusula "{section_title}" (section_key: {section_key}).

Contexto do documento:
- Tipo: {document_type}
- Objeto: {context.get("objeto", "não informado")}
- Órgão: {context.get("orgao", "não informado")}
- Modalidade: {context.get("modalidade", "não informado")}
{section_hint}
{espec_text}EXEMPLOS DE CLÁUSULAS SIMILARES (extraídos de documentos reais):
{rag_context}

Instruções: Gere o CONTEÚDO da cláusula diretamente, sem meta-comentário ("A cláusula deve...", "section_key", títulos). Sempre em português brasileiro com acentuação correta. Adapte ao contexto (objeto, órgão) mantendo a estrutura jurídica dos exemplos. Use listas em prosa quando fizer sentido; tabelas são renderizadas em seções separadas. Nunca use markdown (** * ## ---). Não seja verboso; seja preciso e completo. NUNCA use placeholders como [preencher] ou [prazo]. Cite apenas a Lei 14.133/2021 (não a Lei 8.666). Não repita frases de outras seções."""

    full_prompt = f"<<SYSTEM>>\n{CLAUSE_COMPOSITION_SYSTEM_PROMPT.strip()}\n\n<<USER>>\n{query}"
    url = f"{LLM_ORCHESTRATION_BASE_URL}{LLM_ORCHESTRATION_GENERATE_PATH}"
    payload = {"prompt": full_prompt, "stream": False}

    async with httpx.AsyncClient(timeout=RAG_HTTP_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        body = resp.json()

    # Se a resposta contiver "detail" com mensagem de erro (ex.: proxy retorna 200 com erro), não inserir no documento
    if isinstance(body, dict) and body.get("detail"):
        detail = str(body["detail"]).strip()
        if any(kw in detail.lower() for kw in ("falha", "erro", "timeout", "error", "verifique")):
            raise ValueError(f"Orquestração retornou erro: {detail}")

    data = body.get("data", body) if isinstance(body, dict) else {}
    text = data.get("response", data.get("text", ""))
    raw = (text or "").strip()
    return _postprocess_clause_text(raw)


def _is_meta_comment_line(line: str) -> bool:
    """Verifica se a linha é meta-comentário do LLM (intro de lista, section_key, etc.)."""
    import re
    s = (line or "").strip()
    if not s:
        return True
    patterns = [
        r"^Aqui estão os itens da lista para a seção",
        r"^Segue(?:m)? os itens da (?:lista )?para a seção",
        r"^(?:Os )?itens da seção\s+[\"'].*[\"']",
        r"^Lista de itens para a seção",
        r"\(section_key\s*:\s*[a-z_]+\)",
        r"baseados?\s+na\s+Lei\s+14\.133.*contexto\s+fornecido",
    ]
    for pat in patterns:
        if re.search(pat, s, re.IGNORECASE):
            return True
    return False


def _postprocess_list_text(text: str) -> str:
    """Garante que a saída seja uma linha por item, sem numeração/marcadores no início."""
    import re
    if not text or not isinstance(text, str):
        return text
    # Leis 8.666 e 8.333 → 14.133
    text = re.sub(r"Lei\s*(?:n[º°]?|n\.?\s*[º°]?)?\s*8\.666/1993", "Lei 14.133/2021", text, flags=re.IGNORECASE)
    text = re.sub(r"Lei\s*8\.666", "Lei 14.133/2021", text, flags=re.IGNORECASE)
    text = re.sub(r"Lei\s*(?:n[º°]?|n\.?\s*[º°]?)?\s*8\.333/1991", "Lei 14.133/2021", text, flags=re.IGNORECASE)
    text = re.sub(r"Lei\s*8\.333", "Lei 14.133/2021", text, flags=re.IGNORECASE)
    lines = [ln.strip() for ln in text.strip().split("\n") if ln.strip()]
    cleaned = []
    for ln in lines:
        if _is_meta_comment_line(ln):
            continue
        # Remove numeração inicial (1. 2. 3. ou 1) 2) etc.) e marcadores (- * •)
        ln = re.sub(r"^\s*[\d]+[\.\)]\s*", "", ln)
        ln = re.sub(r"^\s*[\-\*•]\s+", "", ln)
        if ln:
            cleaned.append(ln)
    return "\n".join(cleaned)


async def _generate_list_content(
    section_key: str,
    section_title: str,
    context: Dict[str, Any],
    rag_context: str,
    document_type: str,
    especificacoes: Dict[str, Any] | None = None,
) -> str:
    """Gera itens de lista via LLM para seções content_type=list."""
    espec_text = _format_especificacoes(especificacoes)
    section_hint = _get_section_specific_instructions(section_key, for_list=True)
    query = f"""Gerar os itens da lista para a seção "{section_title}" (section_key: {section_key}).

Contexto: {document_type}. Objeto: {context.get("objeto", "não informado")}. Órgão: {context.get("orgao", "não informado")}.
{section_hint}
{espec_text}Exemplos de itens similares (referência):
{rag_context}

Retorne cada item em uma linha separada. Sem numeração, sem marcadores (- * •). Apenas o texto de cada item. NUNCA use placeholders. Cite apenas Lei 14.133/2021 (não 8.666)."""

    full_prompt = f"<<SYSTEM>>\n{LIST_COMPOSITION_SYSTEM_PROMPT.strip()}\n\n<<USER>>\n{query}"
    url = f"{LLM_ORCHESTRATION_BASE_URL}{LLM_ORCHESTRATION_GENERATE_PATH}"
    payload = {"prompt": full_prompt, "stream": False}

    async with httpx.AsyncClient(timeout=RAG_HTTP_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        body = resp.json()

    if isinstance(body, dict) and body.get("detail"):
        detail = str(body["detail"]).strip()
        if any(kw in detail.lower() for kw in ("falha", "erro", "timeout", "error", "verifique")):
            raise ValueError(f"Orquestração retornou erro: {detail}")

    data = body.get("data", body) if isinstance(body, dict) else {}
    text = data.get("response", data.get("text", ""))
    raw = (text or "").strip()
    return _postprocess_list_text(raw)


def _collect_text_sections(nodes: List[Dict], acc: List[Dict]) -> None:
    """Coleta seções com content_type=text (incluindo subseções)."""
    for node in nodes:
        if node.get("content_type") == "text":
            acc.append({"key": node["key"], "title": node.get("title", node["key"])})
        if node.get("children"):
            _collect_text_sections(node["children"], acc)


def _collect_list_sections(nodes: List[Dict], acc: List[Dict]) -> None:
    """Coleta seções com content_type=list (incluindo subseções)."""
    for node in nodes:
        if node.get("content_type") == "list":
            acc.append({"key": node["key"], "title": node.get("title", node["key"])})
        if node.get("children"):
            _collect_list_sections(node["children"], acc)


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
        rag_context = _sanitize_rag_context_for_legislation(rag_context)
        text = await _generate_clause_text(
            section_key=key,
            section_title=title,
            context=ctx,
            rag_context=rag_context,
            document_type=document_type,
            especificacoes=especificacoes,
        )
        section_texts[key] = text

    # Seções content_type=list: gerar itens via LLM
    list_sections: List[Dict[str, str]] = []
    _collect_list_sections(root, list_sections)
    for sec in list_sections:
        key = sec["key"]
        title = sec["title"]
        query = f"{ctx.get('objeto', '')} {title} {key} obrigações critérios itens"
        docs = retrieve(
            query=query,
            collection_name=coll,
            top_k=top_k_per_section,
            where={"document_type": doc_type_filter},
        )
        if not docs:
            docs = retrieve(query=query, collection_name=coll, top_k=top_k_per_section)
        rag_context = "\n\n---\n\n".join((d.get("content", "") or "")[:600] for d in docs)
        if not rag_context:
            rag_context = "(Nenhum exemplo encontrado. Gere itens genéricos mas pertinentes à seção.)"
        rag_context = _sanitize_rag_context_for_legislation(rag_context)
        text = await _generate_list_content(
            section_key=key,
            section_title=title,
            context=ctx,
            rag_context=rag_context,
            document_type=document_type,
            especificacoes=especificacoes,
        )
        section_texts[key] = text

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
        rag_ctx = _sanitize_rag_context_for_legislation(rag_ctx)
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