"""
API FastAPI do serviço RAG.

Endpoints para ingestão, consulta e gerenciamento de coleções.
"""
from __future__ import annotations

import base64
import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, FastAPI, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

from .chroma_client import delete_collection, get_chroma_client, list_collections
from .ingestion import ingest_text
from .retrieval import check_compliance, generate_answer, retrieve
from .text_corrector_client import correct_section_texts
from .template_packages import (
    ensure_fallback_path,
    get_package_template_paths,
    pick_dfd_template_in_package,
)
from .schemas import (
    AnalyzeDocumentResponse,
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


class GenerateDocumentRequest(BaseModel):
    """Request para geração de documento completo (estrutura + textos de cláusulas)."""
    user_prompt: str = Field(..., description="Pedido livre (ex.: gerar ETP para coleta seletiva)")
    collection: Optional[str] = Field(None, description="Coleção RAG.")
    top_k_per_section: int = Field(5, description="Exemplos por seção para composição.")
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="Contexto do usuário (usuario: {nome_completo, secretaria, prefeitura, orgao}, template_id, document_type_hint).",
    )

    @field_validator("user_prompt")
    @classmethod
    def _user_prompt_not_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("user_prompt é obrigatório.")
        return v


class RenderDocumentRequest(BaseModel):
    """
    JSON para geração de DOCX/PDF.
    Compatível com saída de generate-document.
    """
    structure: dict = Field(
        ...,
        description="Estrutura com document_type e root_sections (chaves: key, title, content_type, children, table_schema).",
    )
    section_texts: Dict[str, str] = Field(
        default_factory=dict,
        description="Textos por section_key (content_type=text).",
    )
    table_data: Optional[Dict[str, List[Dict[str, Any]]]] = Field(
        None,
        description="Dados de tabelas: {section_key: [{col_key: value}, ...]}.",
    )


class SmartIngestFolderRequest(BaseModel):
    """Request para ingestão de pasta."""
    folder_path: str = Field(..., description="Caminho da pasta.")
    collection: Optional[str] = Field(None, description="Nome da coleção.")
    extra_metadata: Optional[dict] = Field(None, description="Metadados extras.")
    recursive: bool = Field(True, description="Processar subpastas.")
    document_type: Optional[str] = Field(
        None,
        description="Forçar tipo (termo_referencia, etp, dfd, lei). Se omitido, infere pelo caminho.",
    )


class PNCPMarketSearchRequest(BaseModel):
    """Request do Agente Pesquisador de Dados PNCP (mercado/preços)."""
    termo_busca: str = Field(..., description="Termo principal do objeto (ex.: pavimentação asfáltica CBUQ).")
    uf: Optional[str] = Field(None, description="UF para recorte geográfico (ex.: SC).")
    codigo_municipio_ibge: Optional[str] = Field(None, description="Código IBGE do município (7 dígitos).")
    data_inicial: Optional[str] = Field(None, description="AAAAMMDD. Se omitido, usa janela padrão.")
    data_final: Optional[str] = Field(None, description="AAAAMMDD. Se omitido, usa data atual UTC.")
    codigo_modalidade: int = Field(8, description="Código de modalidade no PNCP (padrão: 8 - dispensa).")
    limite: int = Field(80, description="Quantidade máxima de contratações para análise.")

    @field_validator("termo_busca")
    @classmethod
    def _termo_not_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("termo_busca é obrigatório.")
        return v


class GenerateTRFromModelRequest(BaseModel):
    """Request para gerar TR a partir do modelo fixo, com slots preenchidos pela IA (e opcionalmente pelo usuário)."""
    user_prompt: str = Field(..., description="Pedido livre (ex.: TR para compra de material de escritório)")
    slots_override: Optional[Dict[str, Any]] = Field(
        None,
        description="Slots já preenchidos pelo usuário (objeto, dispensa, itens, justificativa, fiscal, dotacao). Têm prioridade sobre a IA.",
    )
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="Contexto do usuário logado (usuario: nome_completo, secretaria, prefeitura, orgao). Usado para preencher fiscal e enriquecer o prompt.",
    )
    skip_context_in_prompt: Optional[bool] = Field(
        False,
        description="Se True, não inclui 'Contexto do solicitante' no prompt da LLM (evita objeto vir como palavra/item); fiscal e cidade continuam vindos do context.",
    )
    @field_validator("user_prompt")
    @classmethod
    def _user_prompt_not_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("user_prompt é obrigatório.")
        return v


router = APIRouter(prefix="/rag", tags=["rag"])


class GenerateDFDFromModelRequest(BaseModel):
    """
    Request para gerar DFD a partir do modelo fixo (DFD_modelo_base.docx),
    reutilizando os mesmos slots gerados para o TR.

    Fluxo:
    1. Gera os slots do TR (objeto, justificativa, cidade, etc.) via IA.
    2. Preenche o template de TR (TR_modelo_base.docx) – TR complementar.
    3. Preenche o template de DFD (DFD_modelo_base.docx) copiando:
       - objeto do TR,
       - justificativa do TR,
       - cidade do usuário.
    """

    user_prompt: str = Field(
        ...,
        description="Pedido livre (ex.: TR/DFD para contratação de organização social para gestão de hospital).",
    )
    slots_override: Optional[Dict[str, Any]] = Field(
        None,
        description="Slots já preenchidos/ajustados pelo usuário (objeto, justificativa, fiscal, etc.). Têm prioridade sobre a IA.",
    )
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="Contexto do usuário logado (usuario: nome_completo, secretaria, prefeitura, orgao). Usado para preencher cidade, secretaria, etc.",
    )

    @field_validator("user_prompt")
    @classmethod
    def _user_prompt_not_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("user_prompt é obrigatório.")
        return v


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


@router.post("/pncp/market-search")
async def endpoint_pncp_market_search(body: PNCPMarketSearchRequest) -> dict:
    """
    Agente Pesquisador PNCP:
    busca registros de contratações públicas e retorna painel de preços/tendência.
    """
    from .pncp_service import search_market_prices

    try:
        return await search_market_prices(
            termo_busca=body.termo_busca,
            uf=body.uf,
            codigo_municipio_ibge=body.codigo_municipio_ibge,
            data_inicial=body.data_inicial,
            data_final=body.data_final,
            codigo_modalidade=body.codigo_modalidade,
            limite=body.limite,
        )
    except Exception as e:
        logger.exception("Erro em pncp/market-search: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/generate-document")
async def endpoint_generate_document(
    body: GenerateDocumentRequest,
    output_docx: bool = Query(False, description="Se True, gera e retorna o arquivo DOCX"),
    format: str = Query("docx", description="Com output_docx: docx (arquivo) ou json (metadados)"),
    inspect: bool = Query(
        False,
        description="Com output_docx e format=json: retorna section_texts + docx em base64 para comparar origem dos erros (LLM vs docx)",
    ),
) -> Any:
    """
    Gera documento completo: estrutura + textos de cláusulas.

    Fluxo:
    1. Interpreta prompt via llm_agent e obtém estrutura
    2. Para cada seção: recupera exemplos do RAG
    3. Gera texto de cada cláusula via LLM (robusto, completo, não verboso)
    4. Retorna structure + section_texts
    5. Se output_docx=True: gera DOCX/PDF e retorna o arquivo ou metadados

    Exemplo: "gerar ETP para coleta seletiva" → estrutura + cláusula objeto com texto + justificativa com texto, etc.
    """
    from .document_generator import generate_full_document
    from .docx_generator import json_to_docx_and_pdf

    try:
        result = await generate_full_document(
            user_prompt=body.user_prompt,
            collection_name=body.collection,
            top_k_per_section=body.top_k_per_section,
            context_override=body.context,
        )
        result["section_texts"] = await correct_section_texts(
            result.get("section_texts") or {},
            document_type=result.get("document_type"),
        )
        out = {"ok": True, **result}

        if output_docx:
            data = {"structure": result["structure"], "section_texts": result["section_texts"]}
            table_data = result.get("table_data")  # Inclui linhas_sugeridas + linhas geradas por LLM
            files = json_to_docx_and_pdf(data, table_data=table_data)
            out["docx_path"] = files["docx_path"]
            out["pdf_path"] = files["pdf_path"]
            out["pdf_available"] = files["pdf_available"]
            if format == "docx" and Path(files["docx_path"]).exists():
                return FileResponse(
                    files["docx_path"],
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    filename="documento.docx",
                )
            if inspect and format == "json" and Path(files["docx_path"]).exists():
                with open(files["docx_path"], "rb") as f:
                    out["docx_base64"] = base64.b64encode(f.read()).decode("ascii")
                out["_inspect"] = "Compare section_texts (saída LLM) com o DOCX decodificado; erros iguais=LLM, só no DOCX=docx_generator"
        return out
    except Exception as e:
        logger.exception("Erro em generate-document: %s", e)
        detail = str(e).strip() or f"{type(e).__name__} (sem mensagem)"
        # Extrair mensagem limpa quando vier "Orquestração retornou status 404: {\"detail\":\"...\"}"
        if "404" in detail or "Orquestração" in detail:
            import re
            match = re.search(r'"detail"\s*:\s*"([^"]+)"', detail)
            if match:
                inner = match.group(1).strip()
                if inner:
                    detail = inner
            if "404" in detail and "Ollama" not in detail:
                detail = (
                    "Modelo não encontrado no Ollama (404). "
                    "No host do Ollama execute: ollama pull <modelo> (ex.: ollama pull llama3.2). "
                    "Verifique OLLAMA_MODEL no llm_api e se ollama list mostra o modelo."
                )
        raise HTTPException(status_code=500, detail=detail) from e


@router.post("/render-document")
async def endpoint_render_document(
    body: RenderDocumentRequest,
    format: str = Query("docx", description="Formato de retorno: docx ou json"),
) -> Any:
    """
    Gera DOCX (e PDF se LibreOffice disponível) a partir do JSON.

    Recebe structure + section_texts (formato do generate-document).
    Tabelas: use table_data para preencher linhas ou deixe vazio para placeholder.

    format=docx (padrão): retorna o arquivo DOCX para download.
    format=json: retorna JSON com docx_path, pdf_path, pdf_available.
    """
    from .docx_generator import json_to_docx_and_pdf

    try:
        data = {
            "structure": body.structure,
            "section_texts": await correct_section_texts(
                body.section_texts or {},
                document_type=(body.structure or {}).get("document_type"),
            ),
        }
        result = json_to_docx_and_pdf(
            data,
            table_data=body.table_data,
        )
        if format == "json":
            return {"ok": True, **result}
        # Retorna arquivo DOCX para download
        docx_path = result["docx_path"]
        if not Path(docx_path).exists():
            raise HTTPException(status_code=500, detail="Arquivo DOCX não foi gerado.")
        return FileResponse(
            docx_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="documento.docx",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def _merge_user_context_into_tr_slots(
    slots_override: Optional[Dict[str, Any]], context: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Mescla contexto do usuário (Django) em slots_override.

    Regras:
    - fiscal.nome = dfd_fiscal_contratos (drawer 2.5) quando o override trouxer só o DFD;
    - fiscal.nome = usuario.nome_completo quando ainda não houver nome em slots_override.
    - SECRETARIA DO USUARIO, Nome do USUARIO, CIDADE - ESTADO e CIDADE
      são preenchidos diretamente do backend (sem inferência da IA).
    """
    if not isinstance(context, dict):
        return slots_override

    usuario = context.get("usuario")
    if not isinstance(usuario, dict):
        return slots_override

    slots = dict(slots_override) if slots_override else {}

    # Fiscal do TR: mesma pessoa que «Fiscal de contratos» no DFD (drawer), quando só vier em dfd_fiscal_contratos.
    fiscal = (slots.get("fiscal") or {}) if isinstance(slots.get("fiscal"), dict) else {}
    dfd_fiscal = str(slots.get("dfd_fiscal_contratos") or "").strip()
    if dfd_fiscal and not str(fiscal.get("nome") or "").strip():
        fiscal = {**fiscal, "nome": dfd_fiscal}
        slots["fiscal"] = fiscal

    nome_completo = (usuario.get("nome_completo") or "").strip()
    if nome_completo and not str(fiscal.get("nome") or "").strip():
        fiscal = {**fiscal, "nome": nome_completo}
        slots["fiscal"] = fiscal

    # Campos adicionais do template, sempre vindos do backend e não da IA
    if nome_completo:
        slots.setdefault("nome_usuario", nome_completo)

    secretaria = (usuario.get("secretaria") or "").strip()
    if secretaria:
        slots.setdefault("secretaria_usuario", secretaria)

    cidade = (usuario.get("prefeitura") or "").strip()
    estado_nome = (usuario.get("estado_nome") or usuario.get("estado_uf") or "").strip()
    estado_uf = (usuario.get("estado_uf") or "").strip()
    if cidade:
        slots.setdefault("cidade", cidade)
    if cidade and estado_nome:
        slots.setdefault("cidade_estado", f"{cidade} - {estado_nome}")

    # Código UF (ex.: PR, SC) para placeholder específico no modelo de TR.
    if estado_uf:
        slots.setdefault("codigo_uf", estado_uf)

    return slots


def _file_response_with_llm_token_usage(
    path: str | Path,
    *,
    usage: Dict[str, int],
    **file_response_kwargs: Any,
) -> FileResponse:
    """FileResponse com header ASCII-safe de tokens para o backend Django."""
    from .llm_orchestration import token_usage_response_header_from_dict

    response = FileResponse(path, **file_response_kwargs)
    for key, value in token_usage_response_header_from_dict(usage).items():
        response.headers[key] = value
    return response


def _slot_package_key_from_body(
    context: Optional[Dict[str, Any]],
    slots_override: Optional[Dict[str, Any]] = None,
) -> str:
    """slot_package_key pode vir do context Django ou do slots_override do frontend."""
    for src in (context, slots_override):
        if isinstance(src, dict):
            k = str(src.get("slot_package_key") or "").strip()
            if k:
                return k
    return ""


def _resolve_tr_dfd_template_paths(
    context: Optional[Dict[str, Any]],
    slots: Optional[Any] = None,
    slots_override: Optional[Dict[str, Any]] = None,
) -> Dict[str, Path]:
    """
    Resolve TR + DFD. O DFD usa `DFD_modelo_base_v2.docx` no pacote quando não há
    número de processo e esse ficheiro existir; caso contrário `DFD_modelo_base.docx`.
    """
    from .dfd_template import dfd_numero_processo_filled

    slot_package_key = _slot_package_key_from_body(context, slots_override)
    paths = get_package_template_paths(slot_package_key)
    dfd_chosen = pick_dfd_template_in_package(
        paths["base_dir"],
        has_numero_processo=dfd_numero_processo_filled(slots),
    )
    return {
        "tr": ensure_fallback_path(
            paths["tr"], "TR_modelo_base.docx", slot_package_key=slot_package_key
        ),
        "dfd": ensure_fallback_path(
            dfd_chosen, "DFD_modelo_base.docx", slot_package_key=slot_package_key
        ),
    }


def _resolve_oficio_template_path(
    context: Optional[Dict[str, Any]],
    slots_override: Optional[Dict[str, Any]] = None,
) -> Path:
    slot_package_key = _slot_package_key_from_body(context, slots_override)
    paths = get_package_template_paths(slot_package_key)
    return ensure_fallback_path(
        paths["oficio"],
        "OFICIO_modelo_base.docx",
        slot_package_key=slot_package_key,
    )


@router.post("/generate-tr-from-model")
async def endpoint_generate_tr_from_model(body: GenerateTRFromModelRequest):
    """
    Gera Termo de Referência a partir do modelo fixo (TR_modelo_base.docx).

    Fluxo com IA:
    1. Interpreta o user_prompt via llm_agent (contexto + especificações).
    2. Chama a LLM para preencher os slots (objeto, dispensa, itens, justificativa, fiscal, dotacao).
    3. Mescla com slots_override (valores enviados pelo usuário têm prioridade); context.usuario preenche fiscal.nome se não informado.
    4. Preenche o template DOCX e retorna o arquivo.

    Os itens da tabela de especificações podem vir do prompt (IA extrai) ou do slots_override.itens.
    """
    from .tr_slots_llm import fill_tr_slots_with_llm
    from .tr_template import render_tr_from_slots

    slots_override = _merge_user_context_into_tr_slots(body.slots_override, body.context)
    try:
        slots, llm_usage = await fill_tr_slots_with_llm(
            user_prompt=body.user_prompt,
            slots_override=slots_override,
            user_context=body.context,
        )
        template_paths = _resolve_tr_dfd_template_paths(
            body.context, slots, body.slots_override
        )
        # Gera TR
        docx_tr_path = render_tr_from_slots(slots, template_path=template_paths["tr"])
        if not Path(docx_tr_path).exists():
            raise HTTPException(status_code=500, detail="DOCX do TR não foi gerado.")

        # Gera DFD complementar (não altera a resposta; TR continua sendo o arquivo retornado)
        try:
            from .dfd_template import render_dfd_from_tr_slots

            render_dfd_from_tr_slots(slots, template_path=template_paths["dfd"])
        except Exception:
            # Falha na geração do DFD não deve impedir o TR; apenas registra em log.
            logger.exception("Falha ao gerar DFD complementar a partir do TR.")

        return _file_response_with_llm_token_usage(
            docx_tr_path,
            usage=llm_usage,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="termo_referencia.docx",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.exception("Erro em generate-tr-from-model: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/generate-tr-and-dfd")
async def endpoint_generate_tr_and_dfd(body: GenerateTRFromModelRequest):
    """
    Gera TR (modelo fixo) + DFD complementar e retorna os caminhos dos DOCX.

    Use este endpoint quando o chamador (por exemplo, o backend Django) precisar
    expor Termo de Referência e DFD separadamente ou montar ZIP personalizado.
    """
    from .tr_slots_llm import fill_tr_slots_with_llm
    from .tr_template import render_tr_from_slots
    from .dfd_template import render_dfd_from_tr_slots

    slots_override = _merge_user_context_into_tr_slots(body.slots_override, body.context)
    try:
        slots, llm_usage = await fill_tr_slots_with_llm(
            user_prompt=body.user_prompt,
            slots_override=slots_override,
            user_context=body.context,
        )

        template_paths = _resolve_tr_dfd_template_paths(
            body.context, slots, body.slots_override
        )
        docx_tr_path = render_tr_from_slots(slots, template_path=template_paths["tr"])
        if not Path(docx_tr_path).exists():
            raise HTTPException(status_code=500, detail="DOCX do TR não foi gerado.")

        docx_dfd_path = render_dfd_from_tr_slots(slots, template_path=template_paths["dfd"])
        if not Path(docx_dfd_path).exists():
            raise HTTPException(status_code=500, detail="DOCX do DFD não foi gerado.")

        import base64
        with open(docx_tr_path, "rb") as f:
            tr_b64 = base64.b64encode(f.read()).decode("ascii")
        with open(docx_dfd_path, "rb") as f:
            dfd_b64 = base64.b64encode(f.read()).decode("ascii")

        return {
            "ok": True,
            "tr_docx_path": docx_tr_path,
            "dfd_docx_path": docx_dfd_path,
            "tr_docx_base64": tr_b64,
            "dfd_docx_base64": dfd_b64,
            "llm_token_usage": llm_usage,
        }
    except ValueError as e:
        msg = str(e).strip()
        if any(x in msg for x in ("Orquestração", "LLM", "Resposta da LLM", "404", "modelo")):
            raise HTTPException(status_code=502, detail=msg) from e
        raise HTTPException(status_code=400, detail=msg) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.exception("Erro em generate-tr-and-dfd: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/generate-tr-and-dfd/")
async def endpoint_generate_tr_and_dfd_trailing(body: GenerateTRFromModelRequest):
    """Mesma lógica de generate-tr-and-dfd, para clientes que enviam URL com barra final."""
    return await endpoint_generate_tr_and_dfd(body)


@router.post("/generate-tr-and-dfd-zip")
async def endpoint_generate_tr_and_dfd_zip(body: GenerateTRFromModelRequest):
    """
    Endpoint de teste: gera TR (modelo fixo) + DFD complementar e devolve ambos em um único ZIP.

    Útil para testes via curl: um único request → ZIP com `termo_referencia.docx`, `dfd.docx` e `solicitacao_oficio.docx`.
    """
    from .tr_slots_llm import fill_tr_slots_with_llm
    from .tr_template import render_tr_from_slots
    from .dfd_template import render_dfd_from_tr_slots
    from .oficio_template import render_oficio_from_slots

    skip_ctx = bool(getattr(body, "skip_context_in_prompt", False))
    # Cidade/UF/fiscal vêm do context Django mesmo quando o prompt da LLM não usa perfil.
    slots_override = _merge_user_context_into_tr_slots(body.slots_override, body.context)
    try:
        slots, llm_usage = await fill_tr_slots_with_llm(
            user_prompt=body.user_prompt,
            slots_override=slots_override,
            user_context=body.context if not skip_ctx else None,
            skip_context_in_prompt=skip_ctx,
        )

        template_paths = _resolve_tr_dfd_template_paths(
            body.context, slots, body.slots_override
        )
        docx_tr_path = render_tr_from_slots(slots, template_path=template_paths["tr"])
        if not Path(docx_tr_path).exists():
            raise HTTPException(status_code=500, detail="DOCX do TR não foi gerado.")

        docx_dfd_path = render_dfd_from_tr_slots(slots, template_path=template_paths["dfd"])
        if not Path(docx_dfd_path).exists():
            raise HTTPException(status_code=500, detail="DOCX do DFD não foi gerado.")
        docx_oficio_path = render_oficio_from_slots(
            slots,
            template_path=_resolve_oficio_template_path(body.context, body.slots_override),
        )
        if not Path(docx_oficio_path).exists():
            raise HTTPException(status_code=500, detail="DOCX da Solicitação/Ofício não foi gerado.")

        with tempfile.NamedTemporaryFile(
            prefix="tr_dfd_oficio_bundle_", suffix=".zip", delete=False
        ) as tmp_zip:
            zip_path = tmp_zip.name
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(docx_tr_path, arcname="termo_referencia.docx")
            zf.write(docx_dfd_path, arcname="dfd.docx")
            zf.write(docx_oficio_path, arcname="solicitacao_oficio.docx")

        if not Path(zip_path).exists():
            raise HTTPException(
                status_code=500,
                detail="ZIP com TR, DFD e Solicitação/Ofício não foi gerado.",
            )

        return _file_response_with_llm_token_usage(
            zip_path,
            usage=llm_usage,
            media_type="application/zip",
            filename="tr_dfd_oficio.zip",
        )
    except ValueError as e:
        msg = str(e).strip()
        if any(x in msg for x in ("Orquestração", "LLM", "Resposta da LLM", "404", "modelo")):
            raise HTTPException(status_code=502, detail=msg) from e
        raise HTTPException(status_code=400, detail=msg) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.exception("Erro em generate-tr-and-dfd-zip: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/fill-tr-slots")
async def endpoint_fill_tr_slots(body: GenerateTRFromModelRequest):
    """
    Executa apenas fill_tr_slots_with_llm (mesmo fluxo de IA da geração TR/DFD/Ofício),
    sem renderizar DOCX. Retorna os slots em JSON para preencher objeto/justificativa no formulário.
    """
    from dataclasses import asdict

    from .tr_slots_llm import fill_tr_slots_with_llm

    skip_ctx = bool(getattr(body, "skip_context_in_prompt", False))
    slots_override = _merge_user_context_into_tr_slots(body.slots_override, body.context)
    try:
        slots, llm_usage = await fill_tr_slots_with_llm(
            user_prompt=body.user_prompt,
            slots_override=slots_override,
            user_context=body.context if not skip_ctx else None,
            skip_context_in_prompt=skip_ctx,
        )
        return {"ok": True, "slots": asdict(slots), "llm_token_usage": llm_usage}
    except ValueError as e:
        msg = str(e).strip()
        if any(x in msg for x in ("Orquestração", "LLM", "Resposta da LLM", "404", "modelo")):
            raise HTTPException(status_code=502, detail=msg) from e
        raise HTTPException(status_code=400, detail=msg) from e
    except Exception as e:
        logger.exception("Erro em fill-tr-slots: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


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


@router.post("/ingest-manual")
async def endpoint_ingest_manual(
    file: Optional[UploadFile] = File(None),
    path: Optional[str] = Form(None),
    collection: Optional[str] = Form(None),
) -> dict:
    """
    Ingere manual/guia (ex.: manual de licitações, ETP, DFD, TR) como base de conhecimento.

    Envie `file` (upload) OU `path` (caminho no servidor).
    Chunks são marcados com document_type=guia e tipo_documento (etp, dfd, termo_referencia, geral).
    O analisador usará como contexto sem citar o manual diretamente.
    """
    from .loaders import load_document_text
    from .manual_ingest import ingest_manual

    if file and path:
        raise HTTPException(status_code=400, detail="Informe apenas file OU path.")
    if not file and not path:
        raise HTTPException(status_code=400, detail="Informe file (upload) ou path.")

    try:
        if file:
            suffix = Path(file.filename or "manual.pdf").suffix.lower()
            if suffix not in (".pdf", ".docx", ".doc"):
                raise HTTPException(status_code=400, detail="Use PDF ou DOCX.")
            contents = await file.read()
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(contents)
                tmp_path = tmp.name
            try:
                result = ingest_manual(path=tmp_path, collection_name=collection)
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        else:
            result = ingest_manual(path=path, collection_name=collection)
        return {"ok": True, **result}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Erro em ingest-manual: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


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
            document_type=body.document_type,
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


@router.post("/analyze-document", response_model=AnalyzeDocumentResponse)
async def endpoint_analyze_document(
    file: Optional[UploadFile] = File(None, description="DOCX ou PDF (upload)"),
    path: Optional[str] = Form(None, description="Caminho do arquivo (alternativa ao upload)"),
    top_k: int = Query(8, description="Trechos da Lei 14.133 a recuperar"),
    collection: Optional[str] = Form(None),
) -> AnalyzeDocumentResponse:
    """
    Analisa documento contra a Lei 14.133/2021.

    Envie `file` (upload) OU `path` (caminho no servidor).
    Retorna pontos importantes, acertos, ressalvas (itens ambíguos), erros e conformidade.
    Sem OCR – apenas documentos com texto nativo.
    """
    from .document_analyzer import analyze_document
    from .loaders import load_document_text

    if file and path:
        raise HTTPException(
            status_code=400,
            detail="Informe apenas file (upload) OU path.",
        )
    if not file and not path:
        raise HTTPException(
            status_code=400,
            detail="Informe file (upload) ou path do arquivo DOCX/PDF.",
        )

    try:
        if file:
            suffix = Path(file.filename or "doc.pdf").suffix.lower()
            if suffix not in (".pdf", ".docx", ".doc"):
                raise HTTPException(
                    status_code=400,
                    detail="Formato não suportado. Use DOCX ou PDF.",
                )
            contents = await file.read()
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(contents)
                tmp_path = tmp.name
            try:
                text = load_document_text(tmp_path)
                result = await analyze_document(
                    text=text,
                    collection_name=collection,
                    top_k=top_k,
                )
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        else:
            result = await analyze_document(
                path=path,
                collection_name=collection,
                top_k=top_k,
            )
        return AnalyzeDocumentResponse(ok=True, **{k: v for k, v in result.items() if k != "ok"})
    except FileNotFoundError:
        return AnalyzeDocumentResponse(ok=False, error=f"Arquivo não encontrado: {path}")
    except ValueError as e:
        return AnalyzeDocumentResponse(ok=False, error=str(e))
    except Exception as e:
        logger.exception("Erro em analyze-document: %s", e)
        return AnalyzeDocumentResponse(ok=False, error=str(e))


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
