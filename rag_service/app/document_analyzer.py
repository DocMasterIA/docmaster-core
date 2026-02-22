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
# Foco no que funciona/não funciona no documento, não em "Art. X diz Y"
ANALYSIS_SYSTEM_PROMPT = """Analise este TRECHO de documento licitatório (ETP, DFD ou TR).
Responda APENAS em JSON válido. Sem intro, sem meta-comentários.

ESTILO: Seja DIRETO e FUNCIONAL. Descreva o que está certo/errado em termos práticos.
EVITE: citações diretas de lei ("Art. 46 § 5º", "conforme art. X"). Use a lei como referência interna, mas escreva para o usuário entender o problema ou o acerto sem precisar buscar o dispositivo.
PREFIRA: "Falta justificativa para a contratação integrada" em vez de "Não há menção ao Art. 46 § 5º".

REGRAS:
1. pontos_importantes: até 5 bullets – o que este trecho trata (objeto, justificativa, prazo, etc.).
2. acertos: o que o documento faz BEM – descreva em linguagem clara. Ex.: "Objeto descrito com clareza", "Justificativa técnica adequada".
3. erros: o que FALTA ou está INCORRETO – descreva o problema e o que deveria ter, sem citar art. Ex.: "Não há justificativa para não parcelar a solução", "Cronograma físico-financeiro ausente".
4. conformidade_geral: true SE erros vazio; false SE houver erros.
5. observacoes: sugestões breves ou dúvidas (opcional)."""

ANALYSIS_USER_PROMPT_TEMPLATE = """CONTEXTO (Lei 14.133 e boas práticas):
{context}

TRECHO DO DOCUMENTO ({section_hint}):
{document}

Use o contexto para avaliar. Responda em linguagem DIRETA e FUNCIONAL. Não cite artigos na saída – descreva o acerto ou o problema de forma que o usuário entenda.
JSON: {{"pontos_importantes": [...], "acertos": [...], "erros": [...], "conformidade_geral": bool, "observacoes": "..."}}"""


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
            "erros": [],
            "conformidade_geral": None,
            "observacoes": "Resposta do LLM não pôde ser interpretada como JSON.",
        }


def _infer_document_type(text: str) -> str:
    """Infere tipo (etp, dfd, termo_referencia) pelo conteúdo do documento."""
    doc_type, _ = detect_document_type(text[:2000])
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
        "justificativa", "justificado", "mencionad", "descrito", "suficiente", "para", "com",
        "da", "de", "do", "em", "a", "o", "e", "ou", "se", "que", "na", "no",
    }
    t = _word_tokens(s)
    return t - stop


def _is_positive_phrase(s: str) -> bool:
    low = (s or "").lower()
    return any(x in low for x in ("presente", "adequad", "clareza", "suficiente", "atendendo", "evidenciada", "valorizada"))


def _is_negative_phrase(s: str) -> bool:
    low = (s or "").lower()
    return any(x in low for x in ("ausente", "falta", "não há", "não há ", "incompleta", "incompleto"))


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
    all_erros: List[str] = []
    any_error = False
    obs_parts: List[str] = []

    for p in parsed_list:
        for item in p.get("pontos_importantes") or []:
            all_pontos.append(_ensure_str(item))
        for item in p.get("acertos") or []:
            all_acertos.append(_ensure_str(item))
        for item in p.get("erros") or []:
            all_erros.append(_ensure_str(item))
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

    acertos_dedup = _dedup(all_acertos, 25)
    erros_dedup = _dedup(all_erros, 25)
    acertos_sub = _drop_subsumed(acertos_dedup)
    erros_sub = _drop_subsumed(erros_dedup)
    acertos_overlap = _merge_by_word_overlap(acertos_sub, threshold=0.6)
    erros_overlap = _merge_by_word_overlap(erros_sub, threshold=0.6)
    acertos_final, erros_final, obs_contrad = _drop_contradictions(acertos_overlap, erros_overlap)

    observacoes_base = _decode_html(" | ".join(obs_parts[:3]) if obs_parts else "")
    observacoes_full = " | ".join([observacoes_base, *obs_contrad[:2]]) if obs_contrad else observacoes_base
    observacoes_full = observacoes_full.strip(" | ")

    return {
        "pontos_importantes": _clean(_merge_by_word_overlap(_drop_subsumed(_dedup(all_pontos, 12)), 0.65)),
        "acertos": _clean(acertos_final),
        "erros": _clean(erros_final),
        "conformidade_geral": False if any_error else (
            all(p.get("conformidade_geral") for p in parsed_list) if parsed_list else None
        ),
        "observacoes": observacoes_full,
    }


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
        erros, conformidade_geral, observacoes.
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
            "erros": [],
            "conformidade_geral": None,
            "observacoes": "",
        }

    sections = extract_sections(raw_text)
    sections_detected = [s.key for s in sections] if sections else []
    document_type = _infer_document_type(raw_text)
    chunks = _build_analysis_chunks(sections, raw_text)

    if not chunks:
        return {
            "ok": True,
            "document_type": document_type,
            "sections_detected": sections_detected,
            "pontos_importantes": [],
            "acertos": [],
            "erros": [],
            "conformidade_geral": None,
            "observacoes": "Documento sem conteúdo textual extraível.",
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

    return {
        "ok": True,
        "document_type": document_type,
        "sections_detected": sections_detected,
        "pontos_importantes": merged["pontos_importantes"],
        "acertos": merged["acertos"],
        "erros": merged["erros"],
        "conformidade_geral": merged["conformidade_geral"],
        "observacoes": merged["observacoes"],
    }
