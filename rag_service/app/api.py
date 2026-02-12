"""
API FastAPI do serviço RAG.

Endpoints para ingestão, consulta e gerenciamento de coleções.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .chroma_client import delete_collection, get_chroma_client, list_collections
from .ingestion import ingest_text
from .retrieval import check_compliance, generate_answer, retrieve
from .schemas import (
    CheckComplianceRequest,
    CheckComplianceResponse,
    CollectionsResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    RetrievedChunk,
)


# Schemas adicionais para ingestão inteligente
class SmartIngestFileRequest(BaseModel):
    """Request para ingestão de arquivo por caminho."""
    path: str = Field(..., description="Caminho do arquivo (PDF ou DOCX).")
    collection: Optional[str] = Field(None, description="Nome da coleção.")
    extra_metadata: Optional[dict] = Field(None, description="Metadados extras.")
    document_type: Optional[str] = Field(
        None,
        description="Tipo do documento (termo_referencia, etp, dfd). Se omitido, infere pelo caminho.",
    )


class SmartIngestFolderRequest(BaseModel):
    """Request para ingestão de pasta."""
    folder_path: str = Field(..., description="Caminho da pasta.")
    collection: Optional[str] = Field(None, description="Nome da coleção.")
    extra_metadata: Optional[dict] = Field(None, description="Metadados extras.")
    recursive: bool = Field(True, description="Processar subpastas.")

router = APIRouter(prefix="/rag", tags=["rag"])


def _check_chroma() -> bool:
    """Verifica se a conexão com ChromaDB está ativa."""
    try:
        client = get_chroma_client()
        client.list_collections()
        return True
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse)
async def endpoint_health() -> HealthResponse:
    """Health check: serviço e conexão ChromaDB."""
    chroma_ok = _check_chroma()
    return HealthResponse(
        ok=True,
        chroma_connected=chroma_ok,
        message="ChromaDB conectado" if chroma_ok else "ChromaDB indisponível",
    )


@router.post("/ingest", response_model=IngestResponse)
async def endpoint_ingest(body: IngestRequest) -> IngestResponse:
    """
    Ingere texto no vector store.

    Divide em chunks, gera embeddings e adiciona ao ChromaDB.
    """
    try:
        chunks_added = ingest_text(
            text=body.text,
            metadata=body.metadata,
            collection_name=body.collection,
        )
        return IngestResponse(
            ok=True,
            message=f"Ingestão concluída: {chunks_added} chunks adicionados.",
            chunks_added=chunks_added,
            collection=body.collection,
        )
    except Exception as e:
        return IngestResponse(
            ok=False,
            message="Erro na ingestão.",
            error=str(e),
        )


@router.post("/query", response_model=QueryResponse)
async def endpoint_query(body: QueryRequest) -> QueryResponse:
    """
    Consulta RAG: recupera trechos relevantes e opcionalmente gera resposta via LLM.
    """
    try:
        docs = retrieve(
            query=body.query,
            collection_name=body.collection,
            top_k=body.top_k,
        )

        sources = None
        if body.include_sources:
            sources = [
                RetrievedChunk(
                    content=d.get("content", ""),
                    score=d.get("score"),
                    metadata=d.get("metadata"),
                )
                for d in docs
            ]

        answer = None
        if body.generate_answer and docs:
            answer = await generate_answer(query=body.query, context_docs=docs)

        return QueryResponse(
            ok=True,
            answer=answer,
            sources=sources,
        )
    except Exception as e:
        return QueryResponse(ok=False, error=str(e))


@router.post("/check-compliance", response_model=CheckComplianceResponse)
async def endpoint_check_compliance(body: CheckComplianceRequest) -> CheckComplianceResponse:
    """
    Verifica se o texto gerado está em conformidade com a Lei 14.133.

    Fluxo:
    1. Busca trechos da lei (document_type=lei) relevantes ao texto
    2. Envia texto + trechos ao LLM
    3. Retorna SIM/NÃO + observação breve

    Pré-requisito: Lei 14.133 ingerida em /data/treinamento/LEI_14_133/
    """
    try:
        result = await check_compliance(
            text=body.text,
            collection_name=body.collection,
            top_k=body.top_k,
        )
        return CheckComplianceResponse(
            ok=True,
            compliant=result["compliant"],
            observations=result.get("observations", ""),
            relevant_articles=result.get("relevant_articles"),
        )
    except Exception as e:
        return CheckComplianceResponse(
            ok=False,
            observations="",
            error=str(e),
        )


@router.get("/collections", response_model=CollectionsResponse)
async def endpoint_collections() -> CollectionsResponse:
    """Lista coleções disponíveis no ChromaDB."""
    try:
        cols = list_collections()
        return CollectionsResponse(ok=True, collections=cols)
    except Exception as e:
        return CollectionsResponse(ok=False, collections=[], error=str(e))


@router.delete("/collections/{name}")
async def endpoint_delete_collection(name: str) -> dict:
    """Remove uma coleção do ChromaDB."""
    try:
        deleted = delete_collection(name)
        if deleted:
            return {"ok": True, "message": f"Coleção '{name}' removida."}
        raise HTTPException(status_code=404, detail=f"Coleção '{name}' não encontrada.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================
# Endpoints de ingestão inteligente (com classificação automática)
# ============================================================


@router.post("/smart-ingest/file")
async def endpoint_smart_ingest_file(body: SmartIngestFileRequest) -> dict:
    """
    Ingere arquivo com extração de seções.
    
    O tipo de documento é inferido pelo caminho da pasta (/DFD/ → dfd, etc)
    ou pode ser informado explicitamente via document_type.
    """
    from .smart_ingest import smart_ingest_file
    
    try:
        result = smart_ingest_file(
            path=body.path,
            collection_name=body.collection,
            extra_metadata=body.extra_metadata,
            document_type=body.document_type,
        )
        return {"ok": True, **result}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {body.path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-ingest/folder")
async def endpoint_smart_ingest_folder(body: SmartIngestFolderRequest) -> dict:
    """
    Ingere todos os documentos de uma pasta.
    
    Processa PDFs e DOCXs, classificando cada um automaticamente.
    """
    from .smart_ingest import smart_ingest_folder
    
    try:
        result = smart_ingest_folder(
            folder_path=body.folder_path,
            collection_name=body.collection,
            extra_metadata=body.extra_metadata,
            recursive=body.recursive,
        )
        return {"ok": True, **result}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Pasta não encontrada: {body.folder_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def endpoint_summary(collection: Optional[str] = None) -> dict:
    """
    Retorna resumo das seções indexadas.
    
    Agrupa por tipo de documento e seção.
    """
    from .smart_ingest import get_sections_summary
    
    try:
        summary = get_sections_summary(collection_name=collection)
        return {"ok": True, **summary}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/classify")
async def endpoint_classify(body: SmartIngestFileRequest) -> dict:
    """
    Mostra tipo inferido e seções extraídas (sem indexar).
    
    Útil para testar antes de fazer a ingestão.
    """
    from .document_classifier import extract_sections
    from .smart_ingest import _infer_document_type_from_path
    from .loaders import load_document_text
    
    try:
        text = load_document_text(body.path)
        doc_type = body.document_type or _infer_document_type_from_path(body.path)
        sections = extract_sections(text)
        
        return {
            "ok": True,
            "document_type": doc_type,
            "inferred_from": "path" if not body.document_type else "explicit",
            "sections_found": len(sections),
            "sections": [
                {
                    "key": s.key,
                    "title": s.title,
                    "number": s.number,
                    "content_preview": s.content[:200] + "..." if len(s.content) > 200 else s.content,
                }
                for s in sections
            ],
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {body.path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def create_app() -> FastAPI:
    """Cria a aplicação FastAPI do serviço RAG."""
    app = FastAPI(
        title="DocMaster IA – Serviço RAG",
        description=(
            "Ingestão, retrieval e geração contextualizada. "
            "Conecta ao ChromaDB e à orquestração LLM."
        ),
        version="0.1.0",
    )
    app.include_router(router, prefix="/api")
    return app
