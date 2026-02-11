"""
Cliente ChromaDB para o serviço RAG.

Conecta ao ChromaDB via HTTP (servidor remoto).
"""
from __future__ import annotations

from typing import List, Optional

from .config import CHROMA_COLLECTION, CHROMA_HOST, CHROMA_PORT


def get_chroma_client():
    """
    Retorna cliente ChromaDB HTTP.

    ChromaDB está instalado no servidor; conectamos via HttpClient.
    """
    import chromadb
    from chromadb.config import Settings

    return chromadb.HttpClient(
        host=CHROMA_HOST,
        port=CHROMA_PORT,
        settings=Settings(anonymized_telemetry=False),
    )


def get_or_create_collection(name: Optional[str] = None):
    """
    Obtém ou cria coleção no ChromaDB.

    Args:
        name: Nome da coleção. Se None, usa CHROMA_COLLECTION.

    Returns:
        Coleção ChromaDB.
    """
    client = get_chroma_client()
    coll_name = name or CHROMA_COLLECTION
    return client.get_or_create_collection(
        name=coll_name,
        metadata={"description": "DocMaster IA – documentos e seções indexados"},
    )


def list_collections() -> List[str]:
    """Lista nomes das coleções existentes."""
    client = get_chroma_client()
    cols = client.list_collections()
    return [c.name for c in cols]


def delete_collection(name: str) -> bool:
    """Remove uma coleção. Retorna True se removida com sucesso."""
    client = get_chroma_client()
    try:
        client.delete_collection(name=name)
        return True
    except Exception:
        return False
