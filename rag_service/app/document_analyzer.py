"""
Analisador de documentos licitatórios contra a Lei 14.133/2021.

Extrai texto de DOCX/PDF (sem OCR), recupera trechos da lei via RAG e analisa
conformidade com o LLM. Processa documento inteiro por seções/chunks para
não exceder o contexto do modelo.
"""
from __future__ import annotations

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

# Prompt estritamente enxuto – sem fluff (por seção)
ANALYSIS_SYSTEM_PROMPT = """Analise este TRECHO de documento em relação à Lei 14.133/2021.
Responda APENAS em JSON válido. Sem intro, sem meta-comentários.
- pontos_importantes: até 5 bullets (o que este trecho trata).
- acertos: lista do que está CORRETO conforme a lei (cite art.).
- erros: lista do que está ERRADO ou viola a lei (cite art.).
- conformidade_geral: true SE não houver erros; false SE houver erros.
- observacoes: uma frase ou vazio."""

ANALYSIS_USER_PROMPT_TEMPLATE = """TRECHOS DA LEI 14.133:
{context}

TRECHO DO DOCUMENTO ({section_hint}):
{document}

JSON: {{"pontos_importantes": [...], "acertos": [...], "erros": [...], "conformidade_geral": bool, "observacoes": "..."}}"""


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
        return (text or "").strip()


def _parse_analysis_response(text: str) -> Dict[str, Any]:
    """Extrai JSON da resposta do LLM (pode vir com markdown ou texto antes/depois)."""
    text = (text or "").strip()
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
        all_pontos.extend(p.get("pontos_importantes") or [])
        all_acertos.extend(p.get("acertos") or [])
        all_erros.extend(p.get("erros") or [])
        if p.get("conformidade_geral") is False:
            any_error = True
        obs = (p.get("observacoes") or "").strip()
        if obs:
            obs_parts.append(obs)

    # Deduplica mantendo ordem (simples: por igualdade)
    def _dedup(items: List[str], limit: int = 20) -> List[str]:
        seen_lower: set = set()
        out = []
        for x in items:
            xn = (x or "").strip()
            if not xn:
                continue
            k = xn.lower()
            if k not in seen_lower:
                seen_lower.add(k)
                out.append(xn)
                if len(out) >= limit:
                    break
        return out

    return {
        "pontos_importantes": _dedup(all_pontos, 12),
        "acertos": _dedup(all_acertos, 15),
        "erros": _dedup(all_erros, 15),
        "conformidade_geral": False if any_error else (
            all(p.get("conformidade_geral") for p in parsed_list) if parsed_list else None
        ),
        "observacoes": " | ".join(obs_parts[:3]) if obs_parts else "",
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

        context = "\n\n---\n\n".join(
            (d.get("content", "") or "")[:MAX_LAW_CHUNK_CHARS] for d in docs[:MAX_LAW_CHUNKS]
        ) if docs else "Lei 14.133 não indexada. Analise com base em conhecimento geral."

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
