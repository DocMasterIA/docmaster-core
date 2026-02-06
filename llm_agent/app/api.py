"""
API interna (FastAPI) do llm_agent.

Exposta apenas para outros módulos do sistema (ex.: backend Django),
NÃO para consumo público direto.
"""
from __future__ import annotations

from fastapi import APIRouter, FastAPI, Header, HTTPException

from .agent import generate_structure, interpret_user_prompt
from .registry import is_valid_update_key, update_registry
from .schemas import PromptStructureRequest, SectionsRegistry, StructureRequest, StructureResponse


router = APIRouter(prefix="/agent", tags=["llm_agent"])


@router.post("/registry")
async def endpoint_update_registry(
    body: SectionsRegistry,
    x_update_key: str | None = Header(None, alias="X-Update-Key"),
) -> dict:
    """
    Atualiza o registro de seções (JSON) persistido em arquivo.

    Envie o JSON completo do registro no body e a chave de atualização no header
    X-Update-Key. A chave deve ser configurada em REGISTRY_UPDATE_KEY.
    Após sucesso, o próximo generate_structure usará o novo catálogo.
    """
    if not is_valid_update_key(x_update_key):
        raise HTTPException(
            status_code=401,
            detail="Chave de atualização inválida ou não configurada (X-Update-Key).",
        )
    try:
        update_registry(body)
        return {"ok": True, "message": "Registro de seções atualizado."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/structure-from-prompt", response_model=StructureResponse)
async def endpoint_structure_from_prompt(body: PromptStructureRequest) -> StructureResponse:
    """
    Interpreta um prompt livre do usuário, extrai tipo e contexto e gera a estrutura.

    Fluxo: user_prompt → interpretador LLM → StructureRequest → generate_structure → StructureResponse.
    Quando há catálogo/registro, a IA calcula section_matches (correspondência pedido ↔ seção com nível de certeza).
    """
    try:
        req = await interpret_user_prompt(body.user_prompt)
        req_with_prompt = StructureRequest(
            document_type=req.document_type,
            context=req.context,
            sections_catalog=req.sections_catalog,
            user_prompt=body.user_prompt,
        )
        return await generate_structure(req_with_prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar prompt: {e}") from e


@router.post("/structure", response_model=StructureResponse)
async def endpoint_structure(body: StructureRequest) -> StructureResponse:
    """
    Gera a estrutura lógica de um documento de licitação, sem texto jurídico.

    Entrada:
    - document_type: identificador técnico do tipo de documento.
    - context: objeto, órgão, modalidade e extras.

    Saída:
    - Estrutura em JSON (seções, subseções) conforme schema DocumentStructure.
    """
    # Validação mínima já é feita via Pydantic (document_type + context.objeto).
    # Aqui poderíamos aplicar regras adicionais específicas de negócio se necessário.
    try:
        return await generate_structure(body)
    except Exception as e:  # Último fallback defensivo
        raise HTTPException(status_code=500, detail=f"Erro no agente de estrutura: {e}") from e


def create_app() -> FastAPI:
    """
    Cria a aplicação FastAPI do módulo llm_agent.

    Pensado para ser embutido em outra aplicação ou exposto em porta própria.
    """
    app = FastAPI(
        title="DocMaster IA – Agente de Estrutura Documental",
        description=(
            "Agente interno responsável por gerar APENAS a estrutura lógica de "
            "documentos de licitação (seções, tópicos, subseções) em formato JSON."
        ),
        version="0.1.0",
    )
    app.include_router(router, prefix="/api")
    return app

