"""
API interna (FastAPI) do llm_agent.

Exposta apenas para outros módulos do sistema (ex.: backend Django),
NÃO para consumo público direto.
"""
from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException

from .agent import generate_structure, interpret_user_prompt
from .schemas import PromptStructureRequest, StructureRequest, StructureResponse


router = APIRouter(prefix="/agent", tags=["llm_agent"])


@router.post("/structure-from-prompt", response_model=StructureResponse)
async def endpoint_structure_from_prompt(body: PromptStructureRequest) -> StructureResponse:
    """
    Interpreta um prompt livre do usuário, extrai tipo e contexto e gera a estrutura.

    Fluxo: user_prompt → interpretador LLM → StructureRequest → generate_structure → StructureResponse.
    """
    try:
        req = await interpret_user_prompt(body.user_prompt)
        return await generate_structure(req)
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

