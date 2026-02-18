"""
Analisador de documentos licitatórios contra a Lei 14.133/2021.

Extrai texto de DOCX/PDF (sem OCR), recupera trechos da lei via RAG e analisa
conformidade com o LLM. Saída direta: pontos importantes, acertos, erros.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from .config import (
    CHROMA_COLLECTION,
    LLM_ORCHESTRATION_BASE_URL,
    LLM_ORCHESTRATION_GENERATE_PATH,
    RAG_HTTP_TIMEOUT,
)
from .document_classifier import detect_document_type, extract_sections
from .loaders import load_document_text
from .retrieval import retrieve

# Limite de caracteres para evitar estourar contexto LLM
MAX_DOCUMENT_CHARS = 45_000

# Prompt estritamente enxuto – sem fluff
ANALYSIS_SYSTEM_PROMPT = """Analise o documento em relação à Lei 14.133/2021 (Lei de Licitações e Contratos).
Responda APENAS em JSON válido. Sem intro, sem meta-comentários.
Regras:
- pontos_importantes: até 8 bullets objetivos (o que o doc trata).
- acertos: lista do que está CORRETO conforme a lei (cite art. quando possível).
- erros: lista do que está ERRADO ou viola a lei (cite art. sempre).
- conformidade_geral: true SE não houver erros; false SE houver qualquer erro.
- observacoes: uma frase curta ou string vazia.
Nada mais."""

ANALYSIS_USER_PROMPT_TEMPLATE = """TRECHOS RELEVANTES DA LEI 14.133:
{context}

DOCUMENTO A ANALISAR:
{document}

Retorne JSON: {"pontos_importantes": [...], "acertos": [...], "erros": [...], "conformidade_geral": bool, "observacoes": "..."}"""


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


async def analyze_document(
    path: Optional[str] = None,
    text: Optional[str] = None,
    collection_name: Optional[str] = None,
    top_k: int = 8,
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

    doc_text = raw_text[:MAX_DOCUMENT_CHARS]
    if len(raw_text) > MAX_DOCUMENT_CHARS:
        doc_text += "\n\n[... documento truncado ...]"

    sections = extract_sections(raw_text)
    sections_detected = [s.key for s in sections] if sections else []
    document_type = _infer_document_type(raw_text)

    # RAG: trechos da Lei 14.133
    docs = retrieve(
        query=doc_text,
        collection_name=collection_name or CHROMA_COLLECTION,
        top_k=top_k,
        where={"document_type": "lei"},
    )
    if not docs:
        docs = retrieve(
            query=doc_text,
            collection_name=collection_name or CHROMA_COLLECTION,
            top_k=top_k,
            where={"document_type": "outro"},
        )
        law_docs = [
            d for d in docs
            if "lei" in (d.get("metadata") or {}).get("source_file", "").lower()
            or "14133" in (d.get("metadata") or {}).get("source_file", "")
        ]
        docs = law_docs if law_docs else docs[:2]

    context = "\n\n---\n\n".join(
        (d.get("content", "") or "")[:800] for d in docs
    ) if docs else "Lei 14.133 não indexada. Analise com base em conhecimento geral."

    user_part = ANALYSIS_USER_PROMPT_TEMPLATE.format(
        context=context, document=doc_text
    )
    prompt = f"{ANALYSIS_SYSTEM_PROMPT}\n\n{user_part}"
    llm_response = await _call_llm(prompt)
    parsed = _parse_analysis_response(llm_response)

    return {
        "ok": True,
        "document_type": document_type,
        "sections_detected": sections_detected,
        "pontos_importantes": parsed.get("pontos_importantes") or [],
        "acertos": parsed.get("acertos") or [],
        "erros": parsed.get("erros") or [],
        "conformidade_geral": parsed.get("conformidade_geral"),
        "observacoes": (parsed.get("observacoes") or "").strip(),
    }
