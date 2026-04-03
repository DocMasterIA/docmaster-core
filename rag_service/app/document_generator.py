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
    LLM_ORCHESTRATION_GENERATE_PATH,
    OLLAMA_BASE_URL,
    RAG_HTTP_TIMEOUT,
    RAG_LLM_SANITIZE,
    RAG_POSTPROCESS,
    RAG_TOP_K,
    llm_generation_base_url_for_document_type,
)
from .retrieval import retrieve


# Prompt para composição de cláusulas (robusto, completo, não verboso)
CLAUSE_COMPOSITION_SYSTEM_PROMPT = """
Você é um agente de composição jurídica para documentos de licitação pública.

REGRA FUNDAMENTAL - ENTENDA BEM: Sua saída será INSERIDA DIRETAMENTE no documento final. Você está escrevendo o conteúdo que já aparecerá na página, como se fosse um redator humano. Portanto:
- NUNCA inclua frases introdutórias como "Aqui estão os itens...", "Segue a lista...", "A cláusula deve conter...".
- NUNCA inclua notas, avisos ou meta-informações: "Nota: Este texto foi gerado...", "section_key:", referências ao sistema.
- NUNCA explique o que você vai fazer ou o que a seção deve ter. Redija DIRETAMENTE o conteúdo jurídico final.

PALAVRAS/EXPRESSÕES PROIBIDAS – não use em hipótese alguma:
"Nota:", "Notas:", "Atenção:", "Observação:" (quando meta), "A cláusula deve", "Segue", "Aqui estão", "section_key", "O texto a seguir", "Conforme instruções", "Gerado com base em".
- Pense: "Um leitor abrirá o documento e verá isto. Deve ser conteúdo de cláusula puro, sem prefácios."

Sua função é gerar cláusulas COMPLETAS e ROBUSTAS, baseadas em exemplos reais fornecidos no contexto.

LÍNGUA E FORMATAÇÃO (obrigatório):
- Redija SEMPRE em português brasileiro (pt-BR). NUNCA use inglês ou outros idiomas.
- Use acentuação correta: resíduos, órgão, disposições, número, seqüência (ou sequência), etc.
- § 1º, § 2º: use SOMENTE ao citar artigo de lei (ex.: "art. 10, § 1º, da Lei 14.133/2021"). Para enumeração em texto de cláusula, use 1., 2., 3. ou a), b), c) – NUNCA § 1º, § 2º em redação ordinária.
- NUNCA use formatação markdown: proibido **negrito**, *itálico*, ##, ---, | tabela |. O texto será inserido em documento Word; use apenas texto puro.
- Para listas, use parágrafos ou enumeração em prosa (primeiro, segundo; 1. 2. 3.; a) b) c)). Não use * ou - como marcadores.

Regras obrigatórias:
1. O texto gerado deve ser completo e autocontido – incluir todas as disposições necessárias para a cláusula, sem remeter a "conforme acima" ou "anexo".
2. Não ser verboso nem repetitivo – ir direto ao ponto, com clareza e precisão técnica.
3. Usar os exemplos do contexto RAG como referência – adaptar ao objeto/contexto informado, mantendo estrutura jurídica e requisitos essenciais.
4. LEGISLAÇÃO: Use APENAS a Lei 14.133/2021. NUNCA cite a Lei 8.666/1993 (foi revogada em 2021).
5. CITAÇÕES LEGAIS: SALVO se o artigo, inciso ou parágrafo aparecerem EXPLICITAMENTE (com o mesmo número) no contexto fornecido (exemplos do RAG ou texto do usuário), NÃO invente números de artigos, incisos ou parágrafos (ex.: "art. 40", "art. 10, § 1º"). Quando não houver certeza absoluta, mencione apenas "Lei 14.133/2021" de forma genérica (ex.: "conforme a Lei 14.133/2021"), sem indicar artigo ou parágrafo.
6. Incluir obrigações, prazos, responsabilidades e condições quando fizerem parte da natureza da cláusula.
7. NUNCA inventar fundamentos legais ou disposições que não estejam nos exemplos ou na lei – em dúvida, seja conservador e cite apenas a lei em termos genéricos, sem numeração de artigos ou parágrafos.
8. NUNCA use placeholders: proibido [preencher], [prazo determinado], [valor], [X], [objeto], etc. Use valores genéricos plausíveis quando não houver dado específico (ex.: "30 dias", "conforme edital", "no prazo estabelecido no contrato").
9. REPETIÇÃO É INACEITÁVEL: NUNCA repita frases ou parágrafos idênticos ou quase idênticos na MESMA seção. Cada parágrafo deve ter redação única. Evite fórmulas genéricas repetidas (ex.: "encontra-se detalhada nas partes específicas", "A Administração fará o acompanhamento e o controle das obras e serviços", "nos termos das necessidades específicas"). Se precisar reiterar uma ideia, reformule completamente.
10. NUNCA use formatação markdown para tabelas (ex.: | col1 | col2 | ou linhas com ---). Tabelas são renderizadas em seções separadas pelo sistema. Se precisar mencionar dados tabulares, descreva em prosa ou indique "conforme tabela na seção correspondente".

Formato de saída: APENAS o texto da cláusula. Sem prefácios, sem intros, sem notas, sem explicações. O primeiro caractere da sua resposta deve ser o início do conteúdo jurídico, não uma frase sobre a seção.
- NUNCA use títulos ou cabeçalhos no texto. O título da seção já é inserido automaticamente pelo sistema.
"""


# Prompt para geração de listas (Obrigações, Critérios de Aceitação, etc.)
LIST_COMPOSITION_SYSTEM_PROMPT = """
Você gera itens de lista para seções de documentos de licitação (obrigações, critérios de aceitação, etc.).

REGRA FUNDAMENTAL: Sua saída será INSERIDA DIRETAMENTE no documento. NUNCA comece com intros como "Aqui estão os itens...", "Segue a lista...", "Os itens da seção...". O PRIMEIRO caractere da sua resposta deve ser o primeiro item da lista. Sem prefácios, sem notas, sem section_key ou meta-informações.

PROIBIDO: "Nota:", "Notas:", "Atenção:", "Observação:" (meta), "A cláusula deve", "Segue", "Aqui estão", "section_key".

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
- NUNCA repita frases idênticas ou quase idênticas entre os itens – cada item deve ter redação própria.
"""


# Prompt para sanitização via LLM (remove meta-comentários usando a IA)
LLM_SANITIZE_PROMPT = """Remova do texto abaixo QUALQUER frase que não seja conteúdo de documento:
- Linhas que comecem com: Nota:, Notas:, Atenção:, Observação: (quando meta)
- Intros: "Aqui estão...", "Segue a lista...", "A cláusula deve conter..."
- Meta: "section_key:", "O texto a seguir", "Conforme instruções", "Gerado com base em", "Este texto foi gerado"
Retorne APENAS o texto limpo. O primeiro caractere deve ser o início do conteúdo jurídico. Sem explicações.

TEXTO:
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


async def _llm_sanitize_meta_comments(text: str, document_type: str | None = None) -> str:
    """
    Usa o LLM para remover meta-comentários. A IA interpreta o que deve ser removido.
    Retorna o texto original em caso de falha.
    Para ETP, usa o mesmo backend de geração (ex.: Qwen) quando LLM_ETP_GENERATION_BASE_URL está definido.
    """
    if not text or not RAG_LLM_SANITIZE or not RAG_POSTPROCESS:
        return text
    if len(text.strip()) < 50:
        return text
    try:
        full_prompt = LLM_SANITIZE_PROMPT + text
        base = llm_generation_base_url_for_document_type(document_type)
        url = f"{base}{LLM_ORCHESTRATION_GENERATE_PATH}"
        payload = {"prompt": full_prompt, "stream": False}
        async with httpx.AsyncClient(timeout=RAG_HTTP_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            body = resp.json()
        data = body.get("data", body) if isinstance(body, dict) else {}
        out = (data.get("response", data.get("text", "")) or "").strip()
        if out:
            return out
    except Exception:
        pass
    return text


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
        # Linha de tabela: | col | col | ou col | col (sem | inicial) ou separador ---|
        _is_table_line = (
            lambda s: re.match(r"^\s*\|.+\|\s*$", s)
            or re.match(r"^[\s\|\-:]+$", s)
            or (s.count("|") >= 2 and len(s.strip()) > 10)
        )
        if _is_table_line(line):
            block: List[str] = [line]
            j = i + 1
            while j < len(lines) and _is_table_line(lines[j]):
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


def _postprocess_clause_text(text: str, section_key: str = "") -> str:
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
    # Corrige § 1o → § 1º em citações de lei (art. X, § 1º)
    t = re.sub(r"§\s*(\d+)\s*[oO](?=\s|$|\.|,)", r"§ \1º", t)
    t = re.sub(r"art\.?\s*(\d+)\s*[oO](?=\s|$|\.|,)", r"art. \1º", t)
    # Converte § 1º em início de linha (enumeração indevida) → 1. (§ só em citação de lei)
    t = re.sub(r"^\s*§\s*(\d+)\s*º\s+", r"\1. ", t, flags=re.MULTILINE)
    # Converte 1ª, 2ª, 3ª em enumeração → 1., 2., 3.
    t = re.sub(r"(\d+)\s*ª\s+", r"\1. ", t)
    # Remove "Art. 123. " no início de parágrafo (ETP/estudo não usa numeração de artigos)
    t = re.sub(r"^(Art\.?\s*\d+\.\s+)", "", t, flags=re.MULTILINE)
    # Substitui "presente artigo" por "nesta seção" (estudo/ETP não usa numeração de artigos)
    t = re.sub(r"\bno presente artigo\b", "nesta seção", t, flags=re.IGNORECASE)
    t = re.sub(r"\bdo presente artigo\b", "desta seção", t, flags=re.IGNORECASE)
    t = re.sub(r"\bneste artigo\b", "nesta seção", t, flags=re.IGNORECASE)
    # Leis revogadas: corrige para Lei 14.133/2021
    t = re.sub(r"Lei\s*(?:n[º°]?|n\.?\s*[º°]?)?\s*8\.666/1993", "Lei 14.133/2021", t, flags=re.IGNORECASE)
    t = re.sub(r"Lei\s*8\.666", "Lei 14.133/2021", t, flags=re.IGNORECASE)
    t = re.sub(r"Lei\s*(?:n[º°]?|n\.?\s*[º°]?)?\s*8\.333/1991", "Lei 14.133/2021", t, flags=re.IGNORECASE)
    t = re.sub(r"Lei\s*8\.333", "Lei 14.133/2021", t, flags=re.IGNORECASE)
    # Evita numeração legal potencialmente inventada no texto final:
    # mantemos referência genérica à lei.
    t = re.sub(
        r"\bart(?:igo)?\.?\s*\d+[º°]?(?:\s*,\s*§\s*\d+[º°]?)?\s*(?:,?\s*(?:inciso|alínea)\s*[IVXLCDM\d]+)?\s+da\s+Lei\s+14\.133/2021\b",
        "Lei 14.133/2021",
        t,
        flags=re.IGNORECASE,
    )
    # Normaliza sigla incorreta ETC -> ETP no contexto de estudo técnico preliminar.
    t = re.sub(r"(?i)\bEstudo Técnico Preliminar\s*\(ETC\)", "Estudo Técnico Preliminar (ETP)", t)
    t = re.sub(r"(?i)\bpresente\s+Estudo Técnico Preliminar\s*\(ETC\)", "presente Estudo Técnico Preliminar (ETP)", t)
    t = re.sub(r"(?i)\bETC\b(?=[\s\),\.;:])", "ETP", t)
    # Placeholders: substitui por texto genérico plausível
    placeholder_fixes = [
        (r"R\$\s*\[conforme\s+edital\]", "conforme edital"),
        (r"\[prazo\s+determinado\]", "no prazo estabelecido no edital"),
        (r"\[conforme\s+edital\]", "conforme edital"),
        (r"\[preencher\]", "conforme especificado no edital"),
        (r"\[valor\]", "o valor estabelecido no contrato"),
        (r"\[objeto\]", "o objeto da contratação"),
        (r"\[órgão\]", "o órgão competente"),
        (r"\[orgao\]", "o órgão competente"),
        (r"\[X\]", "conforme edital"),
    ]
    for pat, repl in placeholder_fixes:
        t = re.sub(pat, repl, t, flags=re.IGNORECASE)
    # Corrige erros comuns de português
    fixes = [
        (r"Mantê-la documentação", "Manter a documentação"),
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
        (r"\bacatuladoras\b", "acautelatórias"),
        (r"\bacatulador\b", "acautelatório"),
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
    # Remove citações que remetem a itens/tabela abaixo (objeto e outras seções = descrição pura)
    objeto_ref_patterns = [
        r",?\s*compreendendo\s+os\s+itens\s+descritos\s+abaixo\.?",
        r",?\s*compreendendo\s+os\s+itens\s+relacionados\s+abaixo\.?",
        r",?\s*conforme\s+itens\s+(descritos\s+)?abaixo\.?",
        r",?\s*conforme\s+especificações\s+(a\s+seguir|abaixo)\.?",
        r",?\s*conforme\s+tabela\s+(a\s+seguir|abaixo|em\s+anexo)\.?",
        r",?\s*conforme\s+quantitativo\s+(a\s+seguir|abaixo)\.?",
        r",?\s*conforme\s+detalhamento\s+(na\s+tabela|abaixo)\.?",
        r",?\s*conforme\s+o\s+quantitativo\s+descrito\s+abaixo\.?",
        r",?\s*detalhados\s+(na\s+tabela|nos\s+itens)\s+abaixo\.?",
        r",?\s*especificados\s+(na\s+tabela|nos\s+itens)\s+abaixo\.?",
    ]
    for pat in objeto_ref_patterns:
        t = re.sub(pat, "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s{2,}", " ", t)
    # Converte tabelas markdown (| col1 | col2 | + | --- | + | val |) em lista legível
    t = _convert_markdown_table_to_plain(t)
    # Remove marcadores markdown no início de linha (* ou - , inclusive com espaços)
    t = re.sub(r"^\s*[\*\-]\s+", "", t, flags=re.MULTILINE)
    # Remove notas e meta-comentários (linhas inteiras)
    _M = re.MULTILINE | re.IGNORECASE
    t = re.sub(r"^.*\(section_key\s*:\s*[a-z_]+\)[^.\n]*\.?\s*(?:\n|$)", "", t, flags=_M)
    t = re.sub(r"^Nota:\s*[^\n]*(?:\n|$)", "", t, flags=_M)
    t = re.sub(r"^Notas:\s*[^\n]*(?:\n|$)", "", t, flags=_M)
    # Remove qualquer linha iniciada por "Atenção:" (mesmo quando o texto em seguida é jurídico),
    # para evitar prefácios do tipo "Atenção:" no documento final.
    t = re.sub(r"^Atenção:\s*", "", t, flags=_M)
    t = re.sub(r"^Observação:\s*[^\n]*(?:\n|$)", "", t, flags=_M)
    t = re.sub(r"^(?:A cláusula deve|Segue(?:m)?|Aqui estão)\s+[^\n]*(?:\n|$)", "", t, flags=_M)

    # Remove parágrafos inteiros que são citação legal pura (transcrição de lei)
    _legal_para_patterns = (
        r"^O contrato (?:será|seria) regido pelas regras",
        r"^A Administração poderá optar por licitar de acordo com as leis citadas",
        r"^As hipóteses de cancelamento da ata de registro de preços",
        r"^A contratação posterior de item específico constante de grupo",
        r"^O descumprimento das determinações constantes no presente artigo",
        r"^É vedada a aplicação combinada desta Lei",
        r"^A Administração poderá exigir a comprovação do recolhimento de quantia a título de garantia de proposta",
        r"^A garantia de proposta será devolvida aos licitantes",
        r"^Constará do edital de licitação cláusula que exija dos licitantes",
    )
    paras = re.split(r"\n\s*\n", t)
    kept = []
    for p in paras:
        s = (p or "").strip()
        if not s:
            continue
        if any(re.match(pat, s, re.IGNORECASE) for pat in _legal_para_patterns):
            continue
        kept.append(p)
    t = "\n\n".join(kept)

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
    # Evita vazamento de conteúdo de "análise de riscos" em seção de solução proposta.
    if "soluc" in (section_key or "").lower():
        paras = re.split(r"\n\s*\n", t)
        risk_markers = (
            "nesta seção, são identificados os principais riscos",
            "riscos técnicos",
            "riscos operacionais",
            "riscos de cronograma",
            "riscos de fornecimento",
            "medidas acauteladoras",
        )
        paras = [p for p in paras if not any(m in p.lower() for m in risk_markers)]
        t = "\n\n".join(paras)
    # Remove parágrafos duplicados (repetição – mantém apenas a primeira ocorrência)
    t = _remove_duplicate_paragraphs(t)
    # Remove linhas vazias excessivas (mais de 2 seguidas)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _remove_duplicate_paragraphs(text: str) -> str:
    """
    Remove parágrafos idênticos ou quase idênticos, mantendo apenas a primeira ocorrência.
    Reduz repetições geradas pela IA.
    """
    import re
    if not text or not isinstance(text, str):
        return text
    paras = re.split(r"\n\s*\n", text)
    seen_normalized: set[str] = set()
    kept: List[str] = []
    for p in paras:
        s = (p or "").strip()
        if not s:
            kept.append(p)
            continue
        # Normaliza para comparação: lowercase, colapsa espaços
        norm = re.sub(r"\s+", " ", s.lower())
        if len(norm) < 30:
            kept.append(p)
            continue
        if norm in seen_normalized:
            continue
        seen_normalized.add(norm)
        kept.append(p)
    return "\n\n".join(kept)


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


def _mark_pure_legal_citations_in_rag(rag_context: str) -> str:
    """
    Sinaliza trechos do RAG que parecem citação legal pura (transcrição de artigos),
    para que o LLM não os copie literalmente como cláusulas narrativas.
    """
    import re
    if not rag_context or not isinstance(rag_context, str):
        return rag_context
    sep = "\n\n---\n\n"
    chunks = rag_context.split(sep)
    marker = "[Referência legal – adaptar em prosa contratual, não transcrever literalmente]\n"
    legal_boilerplate = re.compile(
        r"^(?:Art\.|§\s*\d|Artigo\s+\d)",
        re.IGNORECASE,
    )
    legal_phrases = (
        "vedada a aplicação combinada",
        "será regido pelas regras",
        "inciso II do caput",
        "indicadas expressamente no edital",
        "hipóteses de cancelamento da ata",
        "contratação posterior de item específico",
        "prévia pesquisa de mercado",
        "descumprimento das determinações",
        "presente artigo ensejará",
        "ata de registro de preços",
    )
    result = []
    for c in chunks:
        s = (c or "").strip()
        if not s:
            result.append(c)
            continue
        is_pure_legal = (
            legal_boilerplate.match(s)
            and any(p in s.lower() for p in legal_phrases)
            and len(s) < 500
        )
        result.append(marker + c if is_pure_legal else c)
    return sep.join(result)


def _get_etp_preamble() -> str:
    """
    Retorna preâmbulo de instruções específicas para ETP (Estudo Técnico Preliminar).
    Injetado no prompt quando document_type é ETP para refinar a geração.
    """
    return (
        "\n\n=== DOCUMENTO ETP (ESTUDO TÉCNICO PRELIMINAR) ===\n"
        "O ETP é um ESTUDO INTERNO da Administração, não um edital nem um contrato.\n"
        "Regras específicas:\n"
        "- SIGLA OFICIAL: use SEMPRE \"ETP\" para Estudo Técnico Preliminar. NUNCA use \"ETC\".\n"
        "- PRIORIDADE: Use SEMPRE o objeto informado no prompt/contexto. Não mude o tema do estudo com base em exemplos do RAG.\n"
        "- OBJETO/SEÇÃO \"OBJETO\": descreva com 2 a 4 frases o que será CONTRATADO (bens, serviços ou obra), para qual finalidade e quais necessidades administrativas atende, citando o órgão/setor e, quando couber, o público/área beneficiada.\n"
        "  É EXPRESSAMENTE PROIBIDO limitar o OBJETO a uma expressão curta e genérica como apenas \"materiais de limpeza\", \"material de escritório\" ou semelhantes; o texto deve ser completo e autoexplicativo, mesmo que o pedido do usuário seja breve.\n"
        "- SEÇÕES DE NECESSIDADE/MOTIVAÇÃO: explique de forma analítica por que a contratação é necessária, quais problemas pretende resolver e quais riscos existem se não for realizada, SEM inventar números, valores, datas ou normas que não apareçam no contexto.\n"
        "- SOLUÇÃO PROPOSTA / ALTERNATIVAS: foque em descrever alternativas técnicas e a solução escolhida. NÃO copie cláusulas de edital (garantia de proposta, prazos de homologação, penalidades) e NÃO declare modalidade de licitação ou enquadramento em dispensa/inexigibilidade. Redija SEMPRE em prosa contínua (2 a 4 parágrafos), integrando objeto, equipe, rotinas e resultados esperados; NÃO gere listas soltas, itens isolados ou cabeçalhos desconectados (ex.: \"Coleta seletiva\", \"Eficiência e economia\" sozinhos em linhas separadas).\n"
        "- ANÁLISE DE RISCOS: identifique riscos relevantes ligados à execução do objeto (técnicos, operacionais, de cronograma, de fornecimento), e medidas acauteladoras proporcionais. Evite listas vazias ou genéricas demais.\n"
        "- REFERÊNCIAS LEGAIS: você pode mencionar a Lei 14.133/2021 de forma geral. NÃO cite decretos, portarias ou leis específicas (nº, ano) que não estejam no contexto ou exemplos do RAG. NÃO transcreva artigos de lei na íntegra.\n"
        "- VALORES E PRAZOS: quando o valor estimado ou prazos não forem informados no contexto, NÃO invente números (R$ X,00, quantidade de postos, dias exatos). Use formulações genéricas como \"valor estimado a ser definido em estudo orçamentário próprio\" ou \"no prazo a ser fixado no edital\".\n"
        "- LINGUAGEM: use prosa técnica, em português brasileiro, sem \"Art.\", sem \"presente artigo\" – use \"nesta seção\" ou \"no presente estudo\". Não repita parágrafos nem frases inteiras.\n"

    )


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


def _is_conclusion_section(node: Dict[str, Any]) -> bool:
    """
    Heurística para identificar seções de conclusão/encerramento em ETP.
    Usa key e title, buscando termos como 'conclus' e 'encerramento'.
    """
    if not isinstance(node, dict):
        return False
    key = str(node.get("key") or "").lower()
    title = str(node.get("title") or "").lower()
    tokens = ("conclus", "encerramento", "fechamento")
    return any(t in key for t in tokens) or any(t in title for t in tokens)


def _retrieve_with_pncp_priority(
    query: str,
    collection_name: str,
    top_k: int,
    doc_type_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Recupera exemplos do RAG priorizando documentos oriundos do PNCP.

    Estratégia:
    - Primeiro tenta buscar até top_k itens com filtro fonte=pncp (+ document_type, se fornecido);
    - Se vierem menos que top_k, completa com documentos de outras fontes
      com o mesmo document_type;
    - Se ainda assim não houver nada, faz uma busca geral sem filtro.
    """
    where_pncp: Dict[str, Any] = {"fonte": "pncp"}
    if doc_type_filter:
        where_pncp["document_type"] = doc_type_filter

    docs: List[Dict[str, Any]] = []

    # 1) PNCP primeiro
    try:
        docs = retrieve(
            query=query,
            collection_name=collection_name,
            top_k=top_k,
            where=where_pncp,
        )
    except Exception:
        docs = []

    if len(docs) >= top_k:
        return docs[:top_k]

    # 2) Completa com mesma seção de outras fontes (sem fonte=pncp)
    remaining = top_k - len(docs)
    where_others: Optional[Dict[str, Any]] = None
    if doc_type_filter:
        # Filtro por tipo, mas sem restringir fonte
        where_others = {"document_type": doc_type_filter}

    try:
        extra = retrieve(
            query=query,
            collection_name=collection_name,
            top_k=remaining,
            where=where_others,
        )
    except Exception:
        extra = []

    if extra:
        docs.extend(extra)

    if docs:
        return docs[:top_k]

    # 3) Fallback final: sem filtro algum
    try:
        docs = retrieve(
            query=query,
            collection_name=collection_name,
            top_k=top_k,
        )
    except Exception:
        docs = []

    return docs


def _reorder_conclusion_sections_in_tree(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Garante que seções de conclusão/encerramento fiquem sempre ao final da lista.
    Também aplica a mesma regra recursivamente às subseções.
    """
    if not isinstance(nodes, list):
        return nodes

    processed: List[Dict[str, Any]] = []
    for node in nodes:
        if isinstance(node, dict):
            children = node.get("children")
            if isinstance(children, list):
                node["children"] = _reorder_conclusion_sections_in_tree(children)
        processed.append(node)

    conclusion_nodes = [n for n in processed if _is_conclusion_section(n)]
    other_nodes = [n for n in processed if not _is_conclusion_section(n)]
    if not conclusion_nodes:
        return processed
    return other_nodes + conclusion_nodes


def _ensure_etp_conclusion_last(
    structure: Dict[str, Any],
    document_type: str,
) -> Dict[str, Any]:
    """
    Para documentos de tipo ETP/estudo, força que seções de conclusão
    apareçam sempre ao final do documento (root_sections).
    """
    dt = (document_type or structure.get("document_type") or "").lower()
    if "etp" not in dt and "estudo" not in dt:
        return structure

    root = structure.get("root_sections")
    if isinstance(root, list):
        structure["root_sections"] = _reorder_conclusion_sections_in_tree(root)
    return structure


def _sanitize_table_schema_mismatch(structure: Dict[str, Any]) -> Dict[str, Any]:
    """
    Garante que apenas seções com content_type='table' mantenham table_schema.
    Remove table_schema de nós text/list para evitar erros de validação do backend.
    """
    def _clean_nodes(nodes: List[Dict[str, Any]]) -> None:
        for node in nodes:
            if not isinstance(node, dict):
                continue
            ctype = node.get("content_type")
            if ctype != "table" and "table_schema" in node:
                node.pop("table_schema", None)
            children = node.get("children")
            if isinstance(children, list):
                _clean_nodes(children)

    root = structure.get("root_sections")
    if isinstance(root, list):
        _clean_nodes(root)
    return structure


async def _call_llm_agent_structure(user_prompt: str) -> Dict[str, Any]:
    """Chama llm_agent para obter estrutura, context e especificacoes a partir do prompt livre."""
    url = f"{LLM_AGENT_BASE_URL}/api/agent/structure-from-prompt"
    payload = {"user_prompt": user_prompt}
    try:
        async with httpx.AsyncClient(timeout=RAG_HTTP_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 404:
                raise ValueError(
                    "Orquestração retornou 404 (modelo não encontrado no Ollama). "
                    "Execute no host do Ollama: ollama pull <modelo> (ex.: ollama pull llama3.2)."
                )
            resp.raise_for_status()
            data = resp.json()
    except httpx.ConnectError as e:
        raise ValueError(
            f"Não foi possível conectar ao llm_agent ({url}). "
            "Verifique se llm_agent está em execução (docker compose up -d llm_api llm_agent)."
        ) from e
    if not data.get("ok") or not data.get("structure"):
        raise ValueError(data.get("error", "Estrutura não retornada pelo llm_agent"))
    return data


def _get_section_specific_instructions(
    section_key: str, for_list: bool = False, document_type: str = ""
) -> str:
    """
    Retorna instruções específicas por seção para guiar a geração.
    for_list=True: instruções condensadas para itens de lista.
    document_type: usado para regras específicas de ETP, TR, DFD.
    """
    key = (section_key or "").lower()
    doc_type = (document_type or "").lower()
    is_etp = "etp" in doc_type or "estudo" in doc_type

    # ETP: Conclusão – sem Art., sem "presente artigo"
    if "conclus" in key and is_etp:
        return "\nINSTRUÇÕES ETP: Conclusão em prosa. NUNCA use \"Art. X.\" no início. NUNCA use \"presente artigo\". Use \"nesta seção\" ou \"neste documento\". Não repita parágrafos.\n"

    # ETP: Objeto – escopo do CONTRATO, não estrutura do ETP
    if (key == "objeto" or key.startswith("objeto_")) and is_etp:
        if for_list:
            return "\nINSTRUÇÕES ETP: Liste partes do OBJETO DA CONTRATAÇÃO (o que será contratado). NUNCA descreva o que o ETP deve conter – defina os serviços/bens a serem contratados. NUNCA inclua linhas de tabela.\n"
        return "\nINSTRUÇÕES ETP: Defina o OBJETO DA CONTRATAÇÃO (o que será contratado – serviços, bens, escopo). NUNCA descreva \"o que o ETP deve incluir\" ou \"aspectos do estudo\". O objeto é o escopo da contratação futura. Inclua alcance e excludentes. Priorize o objeto informado no prompt (ex.: limpeza urbana ≠ coleta seletiva). Sem tabelas inline. DESCRIÇÃO PURA: NUNCA use \"compreendendo os itens descritos abaixo\", \"conforme tabela\", \"especificações a seguir\" ou qualquer citação que remeta a outras seções – apenas a descrição do objeto.\n"

    # ETP: Solução proposta – técnica/operacional, sem transcrição de lei
    if "soluc" in key and is_etp:
        return (
            "\nINSTRUÇÕES ETP: Descreva a solução TÉCNICA/OPERACIONAL (como o serviço será prestado, requisitos técnicos, rotinas, equipe, equipamentos). "
            "Redija em PROSA CONTÍNUA, em 2 a 4 parágrafos, integrando os elementos (não use listas soltas, títulos isolados ou linhas únicas como \"Coleta seletiva\", \"Eficiência e economia\"). "
            "NUNCA transcreva trechos de lei (garantia de proposta, cláusula do edital, critérios de desempate detalhados). "
            "NUNCA inclua linhas de tabela de custos – use \"conforme tabela na seção correspondente\". "
            "Quando o contexto não trouxer valores ou quantidades exatas, NÃO invente valores monetários (R$ X,00) nem números de postos; use formulações genéricas como "
            "\"valor estimado a ser definido em estudo orçamentário próprio\" ou \"quantitativos a serem detalhados em planilha específica\". Não repita parágrafos.\n"
        )

    # ETP: Conformidade – sem lista de colunas
    if ("conformidade" in key or "legislacao" in key or "legislação" in key) and is_etp:
        return "\nINSTRUÇÕES ETP: Indique conformidade com Lei 14.133/2021. NUNCA liste \"Item, Quantidade, Valor Unitário, Total\" como itens – isso é estrutura de tabela, não de texto. Não repita frases.\n"

    # ETP: Riscos / Análise de riscos
    if "risco" in key and is_etp:
        return "\nINSTRUÇÕES ETP: Descreva alocação de riscos de forma objetiva. Use enumeração 1., 2., 3. ou a), b), c) – NUNCA use 1ª, 2ª, 3ª. Diferencie responsabilidades da Administração e do contratado. Não repita. Não transcreva trechos de lei.\n"

    # Alternativas Analisadas (ETP): ETP NÃO apresenta alternativas À CONTRATADA
    if "alternativa" in key and ("etp" in doc_type or "estudo" in doc_type):
        return (
            "\nINSTRUÇÕES OBRIGATÓRIAS - ALTERNATIVAS EM ETP:\n"
            "- O ETP NÃO apresenta alternativas À CONTRATADA. O objeto já está definido; a contratada não escolhe entre opções.\n"
            "- Se houver esta seção, descreva brevemente as alternativas que a ADMINISTRAÇÃO analisou ao elaborar o estudo (para fins de documentação), indicando qual foi adotada e por quê. Ex.: diferentes modalidades de prestação que a Administração considerou (cooperativa, empresa privada etc.) e a escolha final.\n"
            "- NUNCA liste equipamentos (caminhão, contêineres, EPI) como \"alternativas\" – são parte do objeto/solução, não alternativas.\n"
            "- NUNCA use estrutura \"Alternativa 1\", \"Alternativa 2\" como subseções – não é utilizada em ETPs.\n"
            "- FORMATO: Use SEMPRE texto corrido ou enumeração explícita (1., 2., 3. ou a), b), c)). NUNCA use listas soltas (um item por linha sem 1., 2. ou a), b) – ex.: O modelo X\\nA contratação Y). Redija \"1. O modelo... 2. A contratação...\" ou texto corrido. NUNCA use 1ª, 2ª em enumeração – use 1., 2. NUNCA use § 1º, § 2º (só em citação de lei).\n"
        )

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
            return (
                "\nINSTRUÇÕES ESPECÍFICAS: Liste tipos de garantia (proposta, execução, etc.) e as formas admitidas, "
                "evitando inventar percentuais concretos quando eles não estiverem no contexto. "
                "Lei 14.133: garantia de proposta até o limite legal (ex.: 5% do valor estimado), mas, se o percentual exato não estiver informado, "
                "use formulações genéricas como \"até o limite previsto na Lei 14.133/2021\". NÃO cite Lei 8.666.\n"
            )
        return (
            "\nINSTRUÇÕES ESPECÍFICAS: Descreva a garantia de proposta e/ou de execução com base na Lei 14.133/2021, "
            "sem inventar percentuais ou valores monetários quando não estiverem no contexto. "
            "Use expressões como \"até o limite previsto na Lei 14.133/2021\" em vez de chutar números (R$ X,00, Y%). "
            "Especifique, de forma qualitativa, prazos de prestação e devolução da garantia, e as formas admitidas (caução, seguro-garantia, etc.). "
            "NÃO cite Lei 8.666.\n"
        )

    # Forma de Pagamento
    if "pagamento" in key or "forma_pagamento" in key:
        if for_list:
            return "\nINSTRUÇÕES ESPECÍFICAS: Liste condições de pagamento (parcelas, datas, documentos). Use valores ou percentuais plausíveis, nunca placeholders.\n"
        return "\nINSTRUÇÕES ESPECÍFICAS: Descreva forma e condições de pagamento. Use prazos concretos (ex.: \"30 dias após a entrega\"). NÃO use [prazo] ou [valor].\n"

    # Objeto (fallback quando não ETP)
    if key == "objeto" or key.startswith("objeto_"):
        if for_list:
            return "\nINSTRUÇÕES ESPECÍFICAS: Liste as partes ou modalidades do OBJETO DA CONTRATAÇÃO (o que será contratado). Seja específico ao contexto (serviços, bens).\n"
        return "\nINSTRUÇÕES ESPECÍFICAS: Defina o OBJETO DA CONTRATAÇÃO (o que será contratado – escopo, serviços, bens). NUNCA descreva \"o que o documento deve incluir\". Inclua alcance e excludentes. Priorize o objeto informado no prompt. DESCRIÇÃO PURA: NUNCA use \"compreendendo os itens descritos abaixo\", \"conforme tabela\", \"especificações a seguir\" ou qualquer citação que remeta a outras seções – apenas a descrição do objeto.\n"

    # Necessidade
    if "necessidade" in key:
        if for_list:
            return "\nINSTRUÇÕES ESPECÍFICAS: Liste motivos da necessidade. Priorize o objeto do prompt (ex.: se for limpeza urbana, não misture com coleta seletiva). Evite repetir frases.\n"
        return "\nINSTRUÇÕES ESPECÍFICAS: Fundamente a necessidade da contratação. PRIORIDADE: adapte ao objeto informado no prompt – se o usuário pediu limpeza urbana, não use exemplos de coleta seletiva. Evite fórmulas genéricas.\n"

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


def _format_user_context(context: Dict[str, Any]) -> str:
    """Formata contexto do usuário (Django) para inclusão no prompt."""
    usuario = context.get("usuario") if isinstance(context, dict) else None
    if not usuario or not isinstance(usuario, dict):
        return ""
    parts: List[str] = []
    if usuario.get("nome_completo"):
        parts.append(f"- Solicitante: {usuario['nome_completo']}")
    if usuario.get("secretaria"):
        parts.append(f"- Secretaria/Gabinete: {usuario['secretaria']}")
    if usuario.get("prefeitura") and not context.get("orgao"):
        parts.append(f"- Prefeitura: {usuario['prefeitura']}")
    estado = usuario.get("estado_nome") or usuario.get("estado_uf")
    if estado:
        parts.append(f"- Estado: {estado}")
    if not parts:
        return ""
    return "Contexto do solicitante:\n" + "\n".join(parts) + "\n\n"


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


def _contains_cjk_chars(text: str) -> bool:
    """Detecta presença de ideogramas CJK (sinal forte de idioma incorreto no contexto pt-BR)."""
    import re

    if not text:
        return False
    hits = re.findall(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]", text)
    return len(hits) >= 4


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
    section_hint = _get_section_specific_instructions(section_key, for_list=False, document_type=document_type)
    doc_type_lower = (document_type or "").lower()
    etp_preamble = _get_etp_preamble() if ("etp" in doc_type_lower or "estudo" in doc_type_lower) else ""
    user_ctx = _format_user_context(context)
    query = f"""Gerar o texto COMPLETO da cláusula "{section_title}" (section_key: {section_key}).
{etp_preamble}
Contexto do documento:
- Tipo: {document_type}
- Objeto: {context.get("objeto", "não informado")}
- Órgão: {context.get("orgao", "não informado")}
- Modalidade: {context.get("modalidade", "não informado")}
{user_ctx}{section_hint}
{espec_text}EXEMPLOS DE CLÁUSULAS SIMILARES (extraídos de documentos reais, com prioridade para Termos de Referência, ETPs e contratos oriundos do PNCP quando disponíveis):
{rag_context}

ATENÇÃO AO CONTEXTO RAG: Alguns exemplos podem conter trechos de citação legal pura (transcrição literal de artigos de lei). NÃO copie esses trechos como cláusulas narrativas – use-os apenas como referência para fundamentar; redija em prosa contratual adequada ao documento.

Instruções: O PRIMEIRO caractere da sua resposta deve ser o início do conteúdo jurídico. Não comece com "Aqui estão...", "A cláusula deve...", "Segue..." ou qualquer intro. PROIBIDO: Nota:, Notas:, Atenção:, Observação: (meta), section_key. Redija DIRETAMENTE a cláusula. Português brasileiro. Sem markdown. Sem placeholders []. Cite Lei 14.133/2021. Não repita frases ou parágrafos."""


    async def _run_once(extra_instruction: str = "") -> str:
        q = query if not extra_instruction else f"{query}\n\n{extra_instruction}"
        full_prompt = f"<<SYSTEM>>\n{CLAUSE_COMPOSITION_SYSTEM_PROMPT.strip()}\n\n<<USER>>\n{q}"
        base = llm_generation_base_url_for_document_type(document_type)
        url = f"{base}{LLM_ORCHESTRATION_GENERATE_PATH}"
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
        raw = await _llm_sanitize_meta_comments(raw, document_type=document_type)
        return _postprocess_clause_text(raw, section_key=section_key)

    out = await _run_once()
    if _contains_cjk_chars(out):
        out = await _run_once(
            "RETENTATIVA OBRIGATÓRIA: a resposta anterior veio em idioma inválido. "
            "Reescreva integralmente em português brasileiro (pt-BR), sem qualquer trecho em chinês, japonês ou outro idioma."
        )
    return out


def _is_meta_comment_line(line: str) -> bool:
    """Detecta linhas meta (Nota:, Notas:, section_key, intros). Nunca incluir no documento."""
    import re
    s = (line or "").strip()
    if not s:
        return True
    if re.search(r"\(section_key\s*:\s*[a-z_]+\)", s, re.IGNORECASE):
        return True
    if re.match(r"^Nota:\s*", s, re.IGNORECASE):
        return True
    if re.match(r"^Notas:\s*", s, re.IGNORECASE):
        return True
    if re.match(r"^Atenção:\s*", s, re.IGNORECASE):
        return True
    if re.match(r"^(Aqui estão|Segue(?:m)? (?:aqui )?(?:os )?itens|A cláusula deve conter)", s, re.IGNORECASE):
        return True
    if re.match(r"^(O texto a seguir|Conforme instruções|Gerado com base em)", s, re.IGNORECASE):
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
    section_hint = _get_section_specific_instructions(section_key, for_list=True, document_type=document_type)
    user_ctx = _format_user_context(context)
    query = f"""Gerar os itens da lista para a seção "{section_title}" (section_key: {section_key}).

Contexto: {document_type}. Objeto: {context.get("objeto", "não informado")}. Órgão: {context.get("orgao", "não informado")}.
{user_ctx}
{section_hint}
{espec_text}Exemplos de itens similares (referência):
{rag_context}

ATENÇÃO: Não copie trechos de citação legal pura (transcrição de artigos) dos exemplos – use como referência e redija em prosa adequada. O PRIMEIRO caractere da resposta deve ser o primeiro item. Não comece com intro. Cada item em uma linha. Sem numeração, sem marcadores. Sem placeholders. Lei 14.133/2021."""

    async def _run_once(extra_instruction: str = "") -> str:
        q = query if not extra_instruction else f"{query}\n\n{extra_instruction}"
        full_prompt = f"<<SYSTEM>>\n{LIST_COMPOSITION_SYSTEM_PROMPT.strip()}\n\n<<USER>>\n{q}"
        base = llm_generation_base_url_for_document_type(document_type)
        url = f"{base}{LLM_ORCHESTRATION_GENERATE_PATH}"
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
        raw = await _llm_sanitize_meta_comments(raw, document_type=document_type)
        return _postprocess_list_text(raw)

    out = await _run_once()
    if _contains_cjk_chars(out):
        out = await _run_once(
            "RETENTATIVA OBRIGATÓRIA: a resposta anterior veio em idioma inválido. "
            "Reescreva integralmente em português brasileiro (pt-BR), sem qualquer trecho em chinês, japonês ou outro idioma."
        )
    return out


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
    base = llm_generation_base_url_for_document_type(document_type)
    url = f"{base}{LLM_ORCHESTRATION_GENERATE_PATH}"
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
    context_override: Optional[Dict[str, Any]] = None,
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
    ctx = dict(resp.get("context") or {}) if isinstance(resp.get("context"), dict) else {}
    especificacoes = resp.get("especificacoes")
    if not ctx.get("objeto"):
        ctx["objeto"] = user_prompt[:400].strip() or "Documento solicitado"

    # Merge context_override (Django: usuario, template_id, etc.)
    if context_override and isinstance(context_override, dict):
        usuario = context_override.get("usuario")
        if isinstance(usuario, dict):
            ctx["usuario"] = usuario
            if usuario.get("orgao"):
                ctx["orgao"] = usuario["orgao"]
            elif usuario.get("prefeitura"):
                ctx["orgao"] = f"Prefeitura Municipal de {usuario['prefeitura']}"
        if context_override.get("template_id") is not None:
            ctx["template_id"] = context_override["template_id"]
        if context_override.get("document_type_hint"):
            doc_type_hint = (context_override["document_type_hint"] or "").strip().lower()
            if doc_type_hint:
                document_type = doc_type_hint
                doc_type_filter = _document_type_to_rag_filter(document_type)

    # ETP/Estudo: força seções de conclusão/encerramento ao final do documento
    doc_structure = _ensure_etp_conclusion_last(doc_structure, document_type)
    # Sanitiza inconsistências de table_schema vindo do llm_agent
    doc_structure = _sanitize_table_schema_mismatch(doc_structure)

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
        docs = _retrieve_with_pncp_priority(
            query=query,
            collection_name=coll,
            top_k=top_k_per_section,
            doc_type_filter=doc_type_filter,
        )
        rag_context = "\n\n---\n\n".join(
            (d.get("content", "") or "")[:600] for d in docs
        )
        if not rag_context:
            rag_context = "(Nenhum exemplo encontrado no RAG. Gere uma cláusula genérica mas completa e robusta.)"
        rag_context = _sanitize_rag_context_for_legislation(rag_context)
        rag_context = _mark_pure_legal_citations_in_rag(rag_context)
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
        docs = _retrieve_with_pncp_priority(
            query=query,
            collection_name=coll,
            top_k=top_k_per_section,
            doc_type_filter=doc_type_filter,
        )
        rag_context = "\n\n---\n\n".join((d.get("content", "") or "")[:600] for d in docs)
        if not rag_context:
            rag_context = "(Nenhum exemplo encontrado. Gere itens genéricos mas pertinentes à seção.)"
        rag_context = _sanitize_rag_context_for_legislation(rag_context)
        rag_context = _mark_pure_legal_citations_in_rag(rag_context)
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
        docs = _retrieve_with_pncp_priority(
            query=query,
            collection_name=coll,
            top_k=3,
            doc_type_filter=doc_type_filter,
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