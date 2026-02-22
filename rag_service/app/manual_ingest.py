"""
Ingestão de manuais/guias (ex.: manual de licitações, ETP, DFD, TR).

Tratamento específico:
- document_type="guia" (distinto de lei, etp, dfd)
- Chunking por seção, focado em conceitos (evitar blocos longos)
- Metadados: tipo_documento (etp, dfd, termo_referencia, geral) para filtro no RAG
- Uso como base de conhecimento, não para citação direta
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document

from .chroma_client import get_chroma_client
from .config import CHROMA_COLLECTION, OLLAMA_BASE_URL
from .document_classifier import extract_sections
from .loaders import get_file_metadata, load_document_text


def _infer_tipo_from_text(text: str) -> str:
    """
    Infere tipo_documento (etp, dfd, termo_referencia, geral) a partir do texto.
    Usado para marcar chunks do manual conforme o assunto.
    """
    t = (text or "").lower()[:800]
    if re.search(r"\betp\b|estudo\s+t[eé]cnico\s+preliminar", t):
        return "etp"
    if re.search(r"\bdfd\b|documento\s+de\s+formaliza[çc][ãa]o\s+(da\s+)?demanda|formaliza[çc][ãa]o\s+da\s+demanda", t):
        return "dfd"
    if re.search(r"termo\s+de\s+refer[eê]ncia|\btr\b(?:\s|$)|termo\s+referencia", t):
        return "termo_referencia"
    return "geral"


def _get_embedding_function():
    from langchain_community.embeddings import OllamaEmbeddings
    return OllamaEmbeddings(base_url=OLLAMA_BASE_URL, model="nomic-embed-text")


def _chunk_for_conceptual_use(
    text: str,
    max_chars: int = 600,
    min_chars: int = 80,
) -> List[Tuple[str, str, str]]:
    """
    Quebra texto em chunks conceituais (por parágrafo), evitando blocos longos.
    Retorna lista de (chunk_text, section_hint, tipo_documento).
    """
    chunks: List[Tuple[str, str, str]] = []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    current = []
    current_len = 0
    section_hint = "geral"
    for para in paragraphs:
        if len(para) > max_chars:
            if current:
                block = "\n\n".join(current)
                chunks.append((block, section_hint, _infer_tipo_from_text(block)))
                current = []
                current_len = 0
            for sub in re.split(r"(?<=[.!?])\s+", para):
                if len(sub) >= min_chars:
                    chunks.append((sub[:max_chars], section_hint, _infer_tipo_from_text(sub)))
            continue
        if current_len + len(para) + 2 > max_chars and current:
            block = "\n\n".join(current)
            chunks.append((block, section_hint, _infer_tipo_from_text(block)))
            current = []
            current_len = 0
        current.append(para)
        current_len += len(para) + 2
        if re.match(r"^[\d\.\-\s]*(ETP|DFD|TERMO|DEMANDA|ESTUDO)\b", para, re.I):
            section_hint = para[:80]
    if current:
        block = "\n\n".join(current)
        if len(block) >= min_chars:
            chunks.append((block, section_hint, _infer_tipo_from_text(block)))
    return chunks


def ingest_manual(
    path: str,
    collection_name: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Ingere manual/guia (PDF ou DOCX) como base de conhecimento.

    Chunks são marcados com document_type="guia" e tipo_documento (etp, dfd,
    termo_referencia, geral) para filtro no RAG. O analisador pode usar para
    contextualizar a análise sem citar o manual diretamente.

    Args:
        path: Caminho do arquivo (PDF ou DOCX).
        collection_name: Coleção ChromaDB.
        extra_metadata: Metadados adicionais.

    Returns:
        Dict com file, chunks_added, collection, by_tipo.
    """
    from langchain_chroma import Chroma

    text = load_document_text(path)
    file_meta = get_file_metadata(path)

    sections = extract_sections(text)
    base_meta = {
        **file_meta,
        "document_type": "guia",
        **(extra_metadata or {}),
    }

    docs: List[Document] = []
    if sections:
        for sec in sections:
            if not sec.content or len(sec.content.strip()) < 50:
                continue
            tipo = _infer_tipo_from_text(sec.title + " " + sec.content[:500])
            for chunk_text, hint, chunk_tipo in _chunk_for_conceptual_use(sec.content):
                meta = {
                    **base_meta,
                    "tipo_documento": chunk_tipo or tipo,
                    "section_key": sec.key,
                    "section_title": sec.title,
                }
                if sec.number:
                    meta["section_number"] = sec.number
                docs.append(Document(page_content=chunk_text, metadata=meta))
    else:
        for chunk_text, hint, tipo in _chunk_for_conceptual_use(text):
            docs.append(Document(
                page_content=chunk_text,
                metadata={
                    **base_meta,
                    "tipo_documento": tipo,
                    "section_key": "manual",
                    "section_title": hint[:100] if hint != "geral" else "Conteúdo geral",
                },
            ))

    if not docs:
        return {
            "file": Path(path).name,
            "document_type": "guia",
            "chunks_added": 0,
            "collection": collection_name or CHROMA_COLLECTION,
            "by_tipo": {},
        }

    # ChromaDB limita o tamanho do batch (ex.: 5461); envia em lotes.
    CHROMA_ADD_BATCH_SIZE = 2000

    client = get_chroma_client()
    coll_name = collection_name or CHROMA_COLLECTION
    embeddings = _get_embedding_function()
    vectorstore = Chroma(
        collection_name=coll_name,
        embedding_function=embeddings,
        client=client,
    )
    all_ids: List[str] = []
    for i in range(0, len(docs), CHROMA_ADD_BATCH_SIZE):
        batch = docs[i : i + CHROMA_ADD_BATCH_SIZE]
        batch_ids = vectorstore.add_documents(batch)
        all_ids.extend(batch_ids)

    by_tipo: Dict[str, int] = {}
    for d in docs:
        t = d.metadata.get("tipo_documento", "geral")
        by_tipo[t] = by_tipo.get(t, 0) + 1

    return {
        "file": Path(path).name,
        "document_type": "guia",
        "chunks_added": len(all_ids),
        "collection": coll_name,
        "by_tipo": by_tipo,
    }
