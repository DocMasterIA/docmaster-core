"""
Ingestão de documentos no ChromaDB via LangChain.

Carrega texto, divide em chunks e adiciona ao vector store.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .chroma_client import get_chroma_client
from .config import CHROMA_COLLECTION, OLLAMA_BASE_URL


def _get_embedding_function():
    """
    Retorna função de embeddings (Ollama).

    Requer Ollama rodando com modelo de embeddings (ex.: nomic-embed-text).
    """
    from langchain_community.embeddings import OllamaEmbeddings

    return OllamaEmbeddings(
        base_url=OLLAMA_BASE_URL,
        model="nomic-embed-text",  # ou outro modelo de embeddings suportado
    )


def split_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
    """
    Divide texto em chunks para indexação.

    Args:
        text: Texto a dividir.
        chunk_size: Tamanho máximo do chunk em caracteres.
        chunk_overlap: Sobreposição entre chunks.

    Returns:
        Lista de Document (LangChain).
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    return [Document(page_content=c, metadata={}) for c in chunks]


def ingest_text(
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
    collection_name: Optional[str] = None,
) -> int:
    """
    Ingere texto no ChromaDB.

    Args:
        text: Conteúdo textual.
        metadata: Metadados a anexar aos chunks.
        collection_name: Nome da coleção (None = padrão).

    Returns:
        Quantidade de chunks adicionados.
    """
    from langchain_chroma import Chroma

    docs = split_text(text)
    meta = metadata or {}

    for doc in docs:
        doc.metadata.update(meta)

    embeddings = _get_embedding_function()
    client = get_chroma_client()
    coll_name = collection_name or CHROMA_COLLECTION
    vectorstore = Chroma(
        collection_name=coll_name,
        embedding_function=embeddings,
        client=client,
    )
    ids = vectorstore.add_documents(docs)
    return len(ids)

#,,,