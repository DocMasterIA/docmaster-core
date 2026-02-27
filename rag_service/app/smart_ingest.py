"""
Ingestão inteligente de documentos com extração de seções.

O tipo de documento é inferido pelo caminho da pasta (mais confiável
que detecção por conteúdo).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document

from .chroma_client import get_chroma_client
from .config import CHROMA_COLLECTION, OLLAMA_BASE_URL
from .document_classifier import (
    DocumentType,
    ExtractedSection,
    extract_sections,
)
from .loaders import get_file_metadata, load_document_text


def _infer_document_type_from_path(path: str) -> str:
    """
    Infere o tipo de documento pelo nome da PASTA pai.
    
    Exemplos:
        /data/treinamento/TERMO DE REFERENCIA/doc.pdf → termo_referencia
        /data/treinamento/ETP/doc.pdf → etp
        /data/treinamento/DFD/doc.pdf → dfd
    """
    from pathlib import Path as P
    
    # Pega o nome da pasta pai do arquivo
    parent_folder = P(path).parent.name.lower()
    
    # Checa pelo nome exato da pasta
    if parent_folder in ("etp", "etps"):
        return "etp"
    elif parent_folder in ("dfd", "dfds", "demanda", "demandas"):
        return "dfd"
    elif "termo" in parent_folder or parent_folder in ("tr", "trs"):
        return "termo_referencia"
    elif (
        "lei" in parent_folder
        or "14133" in parent_folder
        or "14_133" in parent_folder
        or "14.133" in parent_folder
        or "referencia" in parent_folder
        or "licitacoes" in parent_folder
    ):
        return "lei"
    else:
        return "outro"


def _get_embedding_function():
    """Retorna função de embeddings (Ollama)."""
    from langchain_community.embeddings import OllamaEmbeddings

    return OllamaEmbeddings(
        base_url=OLLAMA_BASE_URL,
        model="nomic-embed-text",
    )


def _section_to_document(
    section: ExtractedSection,
    doc_type: str,
    base_metadata: Dict[str, Any],
) -> Document:
    """Converte ExtractedSection para Document do LangChain."""
    metadata = {
        **base_metadata,
        "document_type": doc_type,
        "section_key": section.key,
        "section_title": section.title,
    }
    if section.number:
        metadata["section_number"] = section.number
    
    return Document(page_content=section.content, metadata=metadata)


def smart_ingest_file(
    path: str,
    collection_name: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
    document_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ingere um documento com extração de seções.
    
    O tipo de documento é inferido pelo caminho da pasta (ex: /DFD/ → dfd)
    ou pode ser passado explicitamente.
    
    Args:
        path: Caminho do arquivo (PDF ou DOCX).
        collection_name: Nome da coleção ChromaDB.
        extra_metadata: Metadados adicionais a anexar.
        document_type: Tipo explícito (se None, infere pelo caminho).
    
    Returns:
        Dict com resultado da ingestão.
    """
    from langchain_chroma import Chroma
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    # Carrega texto
    text = load_document_text(path)
    
    # Tipo: usa o informado ou infere pelo caminho
    doc_type = document_type or _infer_document_type_from_path(path)
    doc_type_lower = (doc_type or "").lower()
    
    # Metadados base
    file_meta = get_file_metadata(path)
    base_metadata = {
        **file_meta,
        **(extra_metadata or {}),
    }

    # Splitter para quebrar seções muito grandes
    # nomic-embed-text tem limite de ~8192 tokens
    # Sendo bem conservador: 500 chars ~= 125 tokens
    MAX_CHUNK = 500
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=MAX_CHUNK,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    docs: List[Document]
    sections_extracted: int

    # Caso especial: ingestão de lei (ex.: Lei 14.133/2021)
    if doc_type_lower == "lei":
        import re

        lines = text.splitlines()
        current_article_lines: List[str] = []
        current_article_num: str | None = None
        docs = []

        def flush_article():
            nonlocal current_article_lines, current_article_num, docs
            if not current_article_lines or not current_article_num:
                current_article_lines = []
                current_article_num = None
                return
            article_text = "\n".join(current_article_lines).strip()
            if not article_text:
                current_article_lines = []
                current_article_num = None
                return
            # Se o artigo for muito grande, quebra em chunks
            if len(article_text) > MAX_CHUNK:
                chunks = splitter.split_text(article_text)
                for i, chunk in enumerate(chunks):
                    docs.append(
                        Document(
                            page_content=chunk,
                            metadata={
                                **base_metadata,
                                "document_type": doc_type,
                                "section_key": f"artigo_{current_article_num}",
                                "section_title": f"Artigo {current_article_num}",
                                "chunk_index": i,
                            },
                        )
                    )
            else:
                docs.append(
                    Document(
                        page_content=article_text,
                        metadata={
                            **base_metadata,
                            "document_type": doc_type,
                            "section_key": f"artigo_{current_article_num}",
                            "section_title": f"Artigo {current_article_num}",
                        },
                    )
                )
            current_article_lines = []
            current_article_num = None

        # Detecta linhas que iniciam artigos: "Art. 1º", "Art. 2º", "Art. 75."
        art_pattern = re.compile(r"^\s*Art\.\s*(\d+)", re.IGNORECASE)
        for line in lines:
            m = art_pattern.match(line)
            if m:
                # Novo artigo encontrado: flush do anterior
                flush_article()
                current_article_num = m.group(1)
                current_article_lines = [line]
            else:
                if current_article_lines is not None:
                    current_article_lines.append(line)
        # Último artigo
        flush_article()

        sections_extracted = len(docs)
        if not docs:
            # Fallback: ingere como documento único
            chunks = splitter.split_text(text)
            docs = [
                Document(
                    page_content=chunk,
                    metadata={
                        **base_metadata,
                        "document_type": doc_type,
                        "section_key": "full_document",
                        "chunk_index": i,
                    },
                )
                for i, chunk in enumerate(chunks)
            ]
    else:
        # Fluxo padrão: extrai seções com o extrator genérico
        sections = extract_sections(text)
        # Se não encontrou seções, usa texto completo
        if not sections:
            chunks = splitter.split_text(text)
            docs = [
                Document(
                    page_content=chunk,
                    metadata={
                        **base_metadata,
                        "document_type": doc_type,
                        "section_key": "full_document",
                        "chunk_index": i,
                    },
                )
                for i, chunk in enumerate(chunks)
            ]
            sections_extracted = 0
        else:
            # Converte seções para documents, quebrando as muito grandes
            docs = []
            for section in sections:
                section_meta = {
                    **base_metadata,
                    "document_type": doc_type,
                    "section_key": section.key,
                    "section_title": section.title,
                }
                if section.number:
                    section_meta["section_number"] = section.number

                # Se a seção for grande, divide em chunks
                if len(section.content) > MAX_CHUNK:
                    chunks = splitter.split_text(section.content)
                    for i, chunk in enumerate(chunks):
                        docs.append(
                            Document(
                                page_content=chunk,
                                metadata={**section_meta, "chunk_index": i},
                            )
                        )
                else:
                    docs.append(
                        Document(page_content=section.content, metadata=section_meta)
                    )
            sections_extracted = len(sections)
    
    # Indexa no ChromaDB
    client = get_chroma_client()
    coll_name = collection_name or CHROMA_COLLECTION
    embeddings = _get_embedding_function()
    vectorstore = Chroma(
        collection_name=coll_name,
        embedding_function=embeddings,
        client=client,
    )
    ids = vectorstore.add_documents(docs)
    
    return {
        "file": Path(path).name,
        "document_type": doc_type,
        "inferred_from": "path",
        "sections_extracted": sections_extracted,
        "chunks_added": len(ids),  # pode ser > sections se houve split
        "collection": coll_name,
    }


def smart_ingest_folder(
    folder_path: str,
    collection_name: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
    recursive: bool = True,
    document_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ingere todos os documentos de uma pasta.

    Args:
        folder_path: Caminho da pasta.
        collection_name: Nome da coleção.
        extra_metadata: Metadados extras para todos os docs.
        recursive: Se True, processa subpastas.
        document_type: Forçar tipo (lei, etp, dfd, etc.). Se None, infere pelo caminho.

    Returns:
        Dict com resultados por arquivo.
    """
    folder = Path(folder_path)
    results = {
        "success": [],
        "errors": [],
        "summary": {
            "total_files": 0,
            "success_count": 0,
            "error_count": 0,
            "total_sections": 0,
            "by_type": {},
        }
    }
    
    # Padrão de busca
    pattern = "**/*" if recursive else "*"
    
    for file_path in folder.glob(pattern):
        if file_path.suffix.lower() not in (".pdf", ".docx", ".doc"):
            continue
        
        results["summary"]["total_files"] += 1
        
        try:
            result = smart_ingest_file(
                str(file_path),
                collection_name=collection_name,
                extra_metadata=extra_metadata,
                document_type=document_type,
            )
            results["success"].append(result)
            results["summary"]["success_count"] += 1
            results["summary"]["total_sections"] += result["sections_extracted"]
            
            # Conta por tipo
            doc_type = result["document_type"]
            results["summary"]["by_type"][doc_type] = \
                results["summary"]["by_type"].get(doc_type, 0) + 1
                
        except Exception as e:
            results["errors"].append({
                "file": file_path.name,
                "error": str(e),
            })
            results["summary"]["error_count"] += 1
    
    return results


def get_sections_summary(
    collection_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retorna resumo das seções indexadas na coleção.
    
    Agrupa por document_type e section_key.
    """
    from langchain_chroma import Chroma
    
    client = get_chroma_client()
    coll_name = collection_name or CHROMA_COLLECTION
    embeddings = _get_embedding_function()
    
    vectorstore = Chroma(
        collection_name=coll_name,
        embedding_function=embeddings,
        client=client,
    )
    
    # Busca todos os documentos (limitado)
    # Nota: para coleções grandes, isso pode precisar de paginação
    collection = client.get_or_create_collection(coll_name)
    data = collection.get(include=["metadatas"])
    
    summary = {
        "total_chunks": len(data["ids"]),
        "by_document_type": {},
        "by_section_key": {},
    }
    
    for meta in data.get("metadatas", []):
        if not meta:
            continue
        
        doc_type = meta.get("document_type", "unknown")
        section_key = meta.get("section_key", "unknown")
        
        summary["by_document_type"][doc_type] = \
            summary["by_document_type"].get(doc_type, 0) + 1
        summary["by_section_key"][section_key] = \
            summary["by_section_key"].get(section_key, 0) + 1
    
    return summary
