"""
Analisador de documentos licitatórios contra a Lei 14.133/2021.

Extrai texto de DOCX/PDF (sem OCR), recupera trechos da lei via RAG e analisa
conformidade com o LLM. Processa documento inteiro por seções/chunks para
não exceder o contexto do modelo.
"""
from __future__ import annotations

import html
import json
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .config import (
    CHROMA_COLLECTION,
    LLM_ORCHESTRATION_BASE_URL,
    LLM_ORCHESTRATION_GENERATE_PATH,
    RAG_HTTP_TIMEOUT,
)
from .document_classifier import ExtractedSection, detect_document_type, extract_sections
from .loaders import load_document_text
from .retrieval import retrieve

# Limite por chamada LLM (cada seção/chunk cabe no contexto)
MAX_SECTION_CHARS = 2_800
MAX_LAW_CHUNK_CHARS = 350
MAX_LAW_CHUNKS = 4

# Prompt: análise direta e funcional, sem citação explícita de artigos
# Inclui: conformidade Lei 14.133, erros formais, riscos jurídicos, sugestões de reescrita.
# Objetivo: NÃO inventar nada – apenas descrever o que está claramente presente ou ausente no texto.
ANALYSIS_SYSTEM_PROMPT = """Analise este TRECHO de documento licitatório (ETP, DFD ou TR) quanto à Lei 14.133/2021.
Responda APENAS em JSON válido. Sem intro, sem meta-comentários.

ESTILO: Seja DIRETO e FUNCIONAL. Descreva o que está certo/errado em termos práticos.
EVITE: citações diretas de lei ("Art. 46 § 5º"). Use a lei como referência interna; escreva para o usuário entender sem buscar o dispositivo.
PREFIRA: "Falta justificativa para a contratação integrada" em vez de "Não há menção ao Art. 46 § 5º".

NÃO INVENTE NADA:
- NÃO suponha riscos, erros ou acertos que não estejam claramente indicados no texto.
- Se não houver exemplo CLARO no trecho, deixe a lista correspondente VAZIA.
- Evite linguagem especulativa ("pode", "poderia", "talvez", "possível", "em tese", "aparenta", "parece").

REGRAS (máximo 3 itens por lista, apenas os mais claros):
1. pontos_importantes: até 3 bullets – o que este trecho trata (objeto, justificativa, prazo, etc.).
2. acertos: até 3 itens – APENAS o que o documento faz BEM de forma CLARA, diretamente sustentado pelo texto. Sem dúvida, sem "talvez".
3. ressalvas: até 3 itens – pontos em parte positivos mas com dúvida/ambiguidade que estejam presentes no texto (ex.: "cronograma será apresentado posteriormente"). Não invente ressalvas genéricas.
4. erros: até 3 itens – o que FALTA ou está INCORRETO, incluindo erros formais (redação confusa, ausência de requisito, prazos incoerentes). Sempre descreva o problema de forma objetiva, ancorado no texto.
5. riscos_juridicos: até 3 itens – apenas riscos de questionamento, impugnação ou vício QUE SEJAM CLARAMENTE SUGERIDOS pelo texto (ex.: mencionada falta de estimativa de preços). Se não houver menção explícita, deixe vazio.
6. sugestoes_reescrita: até 3 itens – sugestões objetivas de como reescrever ou completar trechos, baseadas em lacunas ou problemas claramente observáveis no texto. Sem "poderia ser melhor", apenas o que falta ou está mal redigido.
7. conformidade_geral: true SE erros vazio; false SE houver erros.
8. observacoes: sugestões breves adicionais (opcional, apenas se úteis e ancoradas no texto)."""

ANALYSIS_USER_PROMPT_TEMPLATE = """CONTEXTO (Lei 14.133 e boas práticas):
{context}

TRECHO DO DOCUMENTO ({section_hint}):
{document}

Avalie com base no contexto. Resposta em linguagem DIRETA. Não cite artigos na saída.
- acertos: só itens claramente positivos e diretamente sustentados pelo texto.
- ressalvas: itens ambíguos ou com dúvida que estejam mencionados no texto.
- erros: inclua apenas erros formais e de conteúdo claramente identificáveis no trecho.
- riscos_juridicos: apenas riscos explicitamente sugeridos pelo texto (se não houver, deixe lista vazia).
- sugestoes_reescrita: como reescrever ou completar trechos problemáticos ou incompletos.
JSON: {{"pontos_importantes": [...], "acertos": [...], "ressalvas": [...], "erros": [...], "riscos_juridicos": [...], "sugestoes_reescrita": [...], "conformidade_geral": bool, "observacoes": "..."}}"""

# Prompt para gerar resumo executivo único a partir do resultado agregado
RESUMO_EXECUTIVO_PROMPT = """Com base na análise de um documento licitatório (ETP, DFD ou TR) frente à Lei 14.133/2021, redija um RESUMO EXECUTIVO em um único parágrafo (3 a 6 linhas).

O resumo deve: (1) dizer o tipo de documento e a conclusão sobre conformidade; (2) destacar os principais pontos positivos; (3) mencionar os principais problemas ou riscos, se houver; (4) encerrar com uma recomendação breve (ex.: adequar antes de publicar, ou documento em conformidade).

Responda APENAS com o parágrafo do resumo. Sem título, sem bullet points, sem "Resumo executivo:" no início."""

RESUMO_EXECUTIVO_USER_TEMPLATE = """Resultado da análise agregada:

- Pontos importantes: {pontos}
- Acertos: {acertos}
- Ressalvas: {ressalvas}
- Erros / não conformidades: {erros}
- Riscos jurídicos: {riscos}
- Sugestões de reescrita: {sugestoes}
- Conformidade geral: {conformidade}
- Observações: {observacoes}

Gere o resumo executivo (um único parágrafo)."""


def _decode_html(text: str) -> str:
    """Decodifica entidades HTML (&#x; &amp; &agrave; etc.)."""
    if not text or not isinstance(text, str):
        return text
    try:
        return html.unescape(text)
    except Exception:
        return text


def _ensure_str(val: Any) -> str:
    """Garante que o valor seja string (LLM pode retornar dict/list)."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, dict):
        for key in ("response", "text", "content", "message"):
            v = val.get(key)
            if v is not None:
                return _ensure_str(v)
        return ""
    if isinstance(val, (list, tuple)):
        return " ".join(_ensure_str(x) for x in val if x)
    return str(val) if val else ""


async def _call_llm(prompt: str) -> str:
    """Chama o LLM com o prompt completo."""
    url = f"{LLM_ORCHESTRATION_BASE_URL}{LLM_ORCHESTRATION_GENERATE_PATH}"
    payload = {"prompt": prompt, "stream": False}
    timeout = RAG_HTTP_TIMEOUT or 120.0
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        body = resp.json()
        data = body.get("data", body) if isinstance(body, dict) else {}
        text = data.get("response", data.get("text", ""))
        return _ensure_str(text)


def _parse_analysis_response(text: Any) -> Dict[str, Any]:
    """Extrai JSON da resposta do LLM (pode vir com markdown ou texto antes/depois)."""
    text = _ensure_str(text)
    # Tenta extrair bloco ```json ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        raw = m.group(1).strip()
    else:
        # Tenta encontrar objeto JSON (primeiro { até último })
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            raw = text[start:end]
        else:
            raw = text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "pontos_importantes": [],
            "acertos": [],
            "ressalvas": [],
            "erros": [],
            "riscos_juridicos": [],
            "sugestoes_reescrita": [],
            "conformidade_geral": None,
            "observacoes": "Resposta do LLM não pôde ser interpretada como JSON.",
        }


def _infer_document_type(text: str) -> str:
    """Infere tipo (etp, dfd, termo_referencia) pelo conteúdo do documento.

    OBS: detect_document_type prioriza DFD porque muitos DFD citam TR/ETP.
    Para o analisador, se houver menção forte a ETP logo no início,
    forçamos etp mesmo que também apareça referência a DFD.
    """
    doc_type, _ = detect_document_type(text[:2000])

    # Heurística extra: se o início do texto mencionar explicitamente
    # "ESTUDO TÉCNICO PRELIMINAR" ou sigla "ETP", priorizar etp.
    snippet = text[:600]
    if re.search(r"ESTUDO\s+T[EÉ]CNICO\s+PRELIMINAR", snippet, re.IGNORECASE) or re.search(r"\bETP\b", snippet, re.IGNORECASE):
        return "etp"

    return doc_type.value if hasattr(doc_type, "value") else str(doc_type)


def _chunk_text(text: str, max_size: int) -> List[str]:
    """Quebra texto em chunks por parágrafos, respeitando max_size."""
    if len(text) <= max_size:
        return [text] if text.strip() else []
    chunks = []
    current = []
    current_len = 0
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if current_len + len(para) + 2 > max_size and current:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(para)
        current_len += len(para) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _build_analysis_chunks(
    sections: List[ExtractedSection],
    raw_text: str,
) -> List[Tuple[str, str]]:
    """
    Retorna lista de (texto, hint) para análise.
    Se houver seções: uma entrada por seção (ou chunks se a seção for grande).
    Se não: chunks do texto completo.
    """
    result: List[Tuple[str, str]] = []
    if sections:
        for sec in sections:
            if not sec.content or not sec.content.strip():
                continue
            if len(sec.content) <= MAX_SECTION_CHARS:
                result.append((sec.content, f"Seção: {sec.title}"))
            else:
                for i, chunk in enumerate(_chunk_text(sec.content, MAX_SECTION_CHARS)):
                    hint = f"Seção {sec.title} (parte {i+1})"
                    result.append((chunk, hint))
    else:
        for i, chunk in enumerate(_chunk_text(raw_text, MAX_SECTION_CHARS)):
            result.append((chunk, f"Trecho {i+1}"))
    return result


def _word_tokens(s: str) -> set:
    """Tokens normalizados (min 2 chars) para comparação de similaridade."""
    s = (s or "").lower()
    words = re.findall(r"[a-záàâãéêíóôõúç0-9]{2,}", s)
    return set(words)


def _word_overlap_ratio(a: set, b: set) -> float:
    """Razão de sobreposição: |a ∩ b| / max(|a|, |b|). Alto quando um é quase subconjunto do outro."""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / max(len(a), len(b))


def _merge_by_word_overlap(items: List[str], threshold: float = 0.6) -> List[str]:
    """Mantém um item por 'cluster' de paráfrases (alta sobreposição de palavras). Ordem preservada."""
    kept: List[str] = []
    for item in items:
        item = _ensure_str(item)
        if not item:
            continue
        tokens = _word_tokens(item)
        if any(_word_overlap_ratio(tokens, _word_tokens(k)) >= threshold for k in kept):
            continue
        kept.append(item)
    return kept


def _topic_signature(s: str) -> set:
    """Palavras de tema (exclui polaridade: presente, ausente, falta, adequada, etc.)."""
    stop = {
        "presente", "ausente", "falta", "adequada", "adequado", "clareza", "não", "há",
        "justificado", "mencionad", "descrito", "suficiente", "para", "com",
        "da", "de", "do", "em", "a", "o", "e", "ou", "se", "que", "na", "no",
    }
    t = _word_tokens(s)
    return t - stop


def _is_positive_phrase(s: str) -> bool:
    low = (s or "").lower()
    return any(x in low for x in ("presente", "adequad", "clareza", "suficiente", "atendendo", "evidenciada", "valorizada", "mencionado", "mencionada"))


def _is_negative_phrase(s: str) -> bool:
    low = (s or "").lower()
    return any(x in low for x in ("ausente", "falta", "não há", "não há ", "incompleta", "incompleto"))


def _contains_hedge(s: str) -> bool:
    """Detecta linguagem especulativa que indica suposição da IA."""
    low = (s or "").lower()
    # Palavras típicas de especulação/hipótese – queremos evitá-las
    hedges = [
        "pode ", "poderá", "poderia", "talvez", "possível", "possivelmente",
        "aparenta", "aparentemente", "parece", "indicaria", "eventual", "em tese",
        "suger", "poderiam", "risco de ser considerado", "pode ser entendido como",
    ]
    return any(h in low for h in hedges)


def _drop_contradictions(
    acertos: List[str],
    erros: List[str],
) -> Tuple[List[str], List[str], List[str]]:
    """
    Remove erros que contradizem acertos (mesmo tema, polaridade oposta).
    Retorna (acertos_final, erros_final, mensagens_para_observacoes).
    """
    acertos_final = list(acertos)
    erros_final = list(erros)
    observacoes_extra: List[str] = []
    for ac in acertos_final[:]:
        if not _is_positive_phrase(ac):
            continue
        sig_ac = _topic_signature(ac)
        if len(sig_ac) < 2:
            continue
        to_remove: List[int] = []
        for i, er in enumerate(erros_final):
            if not _is_negative_phrase(er):
                continue
            sig_er = _topic_signature(er)
            if _word_overlap_ratio(sig_ac, sig_er) >= 0.5:
                to_remove.append(i)
                if sig_ac & sig_er:
                    topic = " ".join(sorted(sig_ac & sig_er)[:4])
                    observacoes_extra.append(f"Inconsistência na análise: menções conflitantes sobre «{topic}».")
        for i in reversed(to_remove):
            erros_final.pop(i)
    return acertos_final, erros_final, observacoes_extra


def _merge_analysis_results(
    parsed_list: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Agrega resultados de múltiplas chamadas LLM."""
    all_pontos: List[str] = []
    all_acertos: List[str] = []
    all_ressalvas: List[str] = []
    all_erros: List[str] = []
    all_riscos: List[str] = []
    all_sugestoes: List[str] = []
    any_error = False
    obs_parts: List[str] = []

    for p in parsed_list:
        for item in p.get("pontos_importantes") or []:
            all_pontos.append(_ensure_str(item))
        for item in p.get("acertos") or []:
            all_acertos.append(_ensure_str(item))
        for item in p.get("ressalvas") or []:
            all_ressalvas.append(_ensure_str(item))
        for item in p.get("erros") or []:
            all_erros.append(_ensure_str(item))
        for item in p.get("riscos_juridicos") or []:
            all_riscos.append(_ensure_str(item))
        for item in p.get("sugestoes_reescrita") or []:
            all_sugestoes.append(_ensure_str(item))
        if p.get("conformidade_geral") is False:
            any_error = True
        obs = _ensure_str(p.get("observacoes"))
        if obs:
            obs_parts.append(obs)

    # Deduplica: 1) igualdade (lowercase) 2) subcadeia 3) paráfrases (overlap de palavras)
    def _dedup(items: List[str], limit: int = 20) -> List[str]:
        seen_lower: set = set()
        out = []
        for x in items:
            xn = _ensure_str(x)
            if not xn:
                continue
            k = xn.lower()
            if k not in seen_lower:
                seen_lower.add(k)
                out.append(xn)
                if len(out) >= limit:
                    break
        return out

    def _drop_subsumed(items: List[str]) -> List[str]:
        """Remove itens que são subcadeia estrita de outro (mantém só a versão mais completa)."""
        if not items:
            return items
        normalized = [(s, s.lower()) for s in items]
        kept = []
        for s, low in normalized:
            if not any(s != t and low in tlow for t, tlow in normalized):
                kept.append(s)
        return kept

    def _clean(items: List[str]) -> List[str]:
        return [_decode_html(x) for x in items]

    def _remove_hedged(items: List[str]) -> List[str]:
        """Remove frases com linguagem especulativa (preferimos não considerar esses pontos)."""
        out: List[str] = []
        for x in items:
            xn = _ensure_str(x)
            if not xn:
                continue
            if _contains_hedge(xn):
                continue
            out.append(xn)
        return out

    # Mover acertos ambíguos (embora, questionável, porém) para ressalvas
    def _is_ambiguous_acerto(s: str) -> bool:
        low = (s or "").lower()
        return any(x in low for x in ("embora", "questionável", "porém", "porem", "todavia", "contudo", "entretanto", " no entanto ", "será apresentad", "mencionado que será"))

    acertos_sem_ambiguos: List[str] = []
    for item in all_acertos:
        if _is_ambiguous_acerto(item):
            all_ressalvas.append(item)
        else:
            acertos_sem_ambiguos.append(item)

    # Remover frases especulativas das listas sensíveis
    acertos_sem_ambiguos = _remove_hedged(acertos_sem_ambiguos)
    all_ressalvas = _remove_hedged(all_ressalvas)
    all_erros = _remove_hedged(all_erros)
    all_riscos = _remove_hedged(all_riscos)
    all_sugestoes = _remove_hedged(all_sugestoes)

    # Limites um pouco mais baixos para evitar listões
    acertos_dedup = _dedup(acertos_sem_ambiguos, 15)
    erros_dedup = _dedup(all_erros, 15)
    acertos_sub = _drop_subsumed(acertos_dedup)
    erros_sub = _drop_subsumed(erros_dedup)
    acertos_overlap = _merge_by_word_overlap(acertos_sub, threshold=0.6)
    # Para erros, seja um pouco mais agressivo na fusão de paráfrases.
    erros_overlap = _merge_by_word_overlap(erros_sub, threshold=0.55)
    acertos_final, erros_final, obs_contrad = _drop_contradictions(acertos_overlap, erros_overlap)

    ressalvas_dedup = _dedup(all_ressalvas, 12)
    ressalvas_sub = _drop_subsumed(ressalvas_dedup)
    ressalvas_final = _merge_by_word_overlap(ressalvas_sub, threshold=0.55)

    riscos_dedup = _dedup(all_riscos, 10)
    riscos_sub = _drop_subsumed(riscos_dedup)
    riscos_final = _merge_by_word_overlap(riscos_sub, threshold=0.5)

    sugestoes_dedup = _dedup(all_sugestoes, 10)
    sugestoes_sub = _drop_subsumed(sugestoes_dedup)
    sugestoes_final = _merge_by_word_overlap(sugestoes_sub, threshold=0.5)

    # Observações: apenas o que veio da própria análise de cada trecho (sem meta-comentários de inconsistência)
    observacoes_base = _decode_html(" | ".join(obs_parts[:3]) if obs_parts else "")
    observacoes_full = observacoes_base.strip(" | ")

    return {
        "pontos_importantes": _clean(_merge_by_word_overlap(_drop_subsumed(_dedup(all_pontos, 12)), 0.65)),
        "acertos": _clean(acertos_final),
        "ressalvas": _clean(ressalvas_final),
        "erros": _clean(erros_final),
        "riscos_juridicos": _clean(riscos_final),
        "sugestoes_reescrita": _clean(sugestoes_final),
        "conformidade_geral": False if any_error else (
            all(p.get("conformidade_geral") for p in parsed_list) if parsed_list else None
        ),
        "observacoes": observacoes_full,
    }


async def _generate_resumo_executivo(merged: Dict[str, Any]) -> str:
    """Gera um parágrafo de resumo executivo a partir do resultado agregado da análise."""
    def _join(items: List[str], limit: int = 8) -> str:
        parts = [_ensure_str(x) for x in (items or [])[:limit] if _ensure_str(x)]
        return "; ".join(parts) if parts else "Nenhum."
    try:
        conf = merged.get("conformidade_geral")
        conf_str = "Conforme" if conf is True else ("Não conforme" if conf is False else "Indefinida")
        user_msg = RESUMO_EXECUTIVO_USER_TEMPLATE.format(
            pontos=_join(merged.get("pontos_importantes") or []),
            acertos=_join(merged.get("acertos") or []),
            ressalvas=_join(merged.get("ressalvas") or []),
            erros=_join(merged.get("erros") or []),
            riscos=_join(merged.get("riscos_juridicos") or []),
            sugestoes=_join(merged.get("sugestoes_reescrita") or []),
            conformidade=conf_str,
            observacoes=_ensure_str(merged.get("observacoes") or ""),
        )
        prompt = f"{RESUMO_EXECUTIVO_PROMPT}\n\n{user_msg}"
        text = await _call_llm(prompt)
        return _decode_html(_ensure_str(text))
    except Exception:
        return ""


async def analyze_document(
    path: Optional[str] = None,
    text: Optional[str] = None,
    collection_name: Optional[str] = None,
    top_k: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Analisa documento contra a Lei 14.133/2021.

    Args:
        path: Caminho do arquivo DOCX ou PDF.
        text: Texto bruto (alternativa a path).
        collection_name: Coleção ChromaDB.
        top_k: Trechos da lei a recuperar.

    Returns:
        Dict com document_type, sections_detected, pontos_importantes, acertos,
        ressalvas, erros, conformidade_geral, observacoes.
    """
    k = top_k if top_k is not None else MAX_LAW_CHUNKS

    if path and not text:
        raw_text = load_document_text(path)
    elif text:
        raw_text = (text or "").strip()
    else:
        return {
            "ok": False,
            "error": "Informe path ou text.",
            "document_type": "outro",
            "sections_detected": [],
            "pontos_importantes": [],
            "acertos": [],
            "ressalvas": [],
            "erros": [],
            "riscos_juridicos": [],
            "sugestoes_reescrita": [],
            "conformidade_geral": None,
            "observacoes": "",
            "resumo_executivo": "",
        }

    sections = extract_sections(raw_text)
    # Remove duplicatas mantendo a ordem de primeira aparição
    sections_detected = list(dict.fromkeys([s.key for s in sections])) if sections else []
    document_type = _infer_document_type(raw_text)
    chunks = _build_analysis_chunks(sections, raw_text)

    if not chunks:
        return {
            "ok": True,
            "document_type": document_type,
            "sections_detected": sections_detected,
            "pontos_importantes": [],
            "acertos": [],
            "ressalvas": [],
            "erros": [],
            "riscos_juridicos": [],
            "sugestoes_reescrita": [],
            "conformidade_geral": None,
            "observacoes": "Documento sem conteúdo textual extraível.",
            "resumo_executivo": "",
        }

    parsed_list: List[Dict[str, Any]] = []
    coll = collection_name or CHROMA_COLLECTION

    for doc_chunk, section_hint in chunks:
        docs = retrieve(
            query=doc_chunk,
            collection_name=coll,
            top_k=k,
            where={"document_type": "lei"},
        )
        if not docs:
            docs = retrieve(
                query=doc_chunk,
                collection_name=coll,
                top_k=k,
                where={"document_type": "outro"},
            )
            law_docs = [
                d for d in docs
                if "lei" in (d.get("metadata") or {}).get("source_file", "").lower()
                or "14133" in (d.get("metadata") or {}).get("source_file", "")
            ]
            docs = law_docs if law_docs else docs[:2]

        law_context = "\n\n---\n\n".join(
            (d.get("content", "") or "")[:MAX_LAW_CHUNK_CHARS] for d in docs[:MAX_LAW_CHUNKS]
        ) if docs else "Lei 14.133 não indexada."

        guia_docs = retrieve(
            query=doc_chunk,
            collection_name=coll,
            top_k=2,
            where={"document_type": "guia"},
        )
        guia_context = ""
        if guia_docs:
            guia_parts = [(d.get("content", "") or "")[:400] for d in guia_docs]
            guia_context = "\n\n[Referência – boas práticas]\n" + "\n---\n".join(guia_parts)

        context = (law_context + guia_context) if law_context or guia_context else "Sem referências indexadas."

        user_part = ANALYSIS_USER_PROMPT_TEMPLATE.format(
            context=context,
            document=doc_chunk,
            section_hint=section_hint,
        )
        prompt = f"{ANALYSIS_SYSTEM_PROMPT}\n\n{user_part}"
        llm_response = await _call_llm(prompt)
        parsed_list.append(_parse_analysis_response(llm_response))

    merged = _merge_analysis_results(parsed_list)
    resumo_executivo = await _generate_resumo_executivo(merged)

    return {
        "ok": True,
        "document_type": document_type,
        "sections_detected": sections_detected,
        "pontos_importantes": merged["pontos_importantes"],
        "acertos": merged["acertos"],
        "ressalvas": merged["ressalvas"],
        "erros": merged["erros"],
        "riscos_juridicos": merged["riscos_juridicos"],
        "sugestoes_reescrita": merged["sugestoes_reescrita"],
        "conformidade_geral": merged["conformidade_geral"],
        "observacoes": merged["observacoes"],
        "resumo_executivo": resumo_executivo,
    }
