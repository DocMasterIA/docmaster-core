"""
Núcleo do agente de estrutura documental.

Responsável por:
- Validar entrada mínima (tipo + contexto).
- Construir prompts (sistema + usuário) padronizados.
- Chamar o módulo de orquestração LLM.
- Interpretar e validar a estrutura retornada.
- Aplicar fallbacks (re-prompt ou estrutura mínima) em caso de falha.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Tuple

from pydantic import ValidationError

from .client import OrchestrationError, call_generate
from .config import AGENT_MAX_RETRIES
from .prompts import build_system_prompt, build_user_prompt
from .schemas import (
    DocumentStructure,
    SectionNode,
    StructureRequest,
    StructureResponse,
    TableColumn,
    TableSchema,
)


def _minimal_structure_for(document_type: str) -> DocumentStructure:
    """
    Estrutura mínima de fallback por tipo de documento.

    Mantém algo utilizável mesmo se o modelo falhar completamente.
    """
    dt = document_type.strip().lower()

    if dt == "termo_referencia":
        sections = [
            SectionNode(
                key="objeto",
                title="DO OBJETO",
                required=True,
                content_type="text",
            ),
            SectionNode(
                key="justificativa",
                title="DA JUSTIFICATIVA",
                required=True,
                content_type="text",
            ),
            SectionNode(
                key="descricao_detalhada_objeto",
                title="DA DESCRIÇÃO DETALHADA DO OBJETO",
                required=True,
                content_type="text",
            ),
        ]
    elif dt == "estudo_tecnico_preliminar":
        sections = [
            SectionNode(
                key="objeto",
                title="DO OBJETO",
                required=True,
                content_type="text",
            ),
            SectionNode(
                key="necessidade",
                title="DA NECESSIDADE",
                required=True,
                content_type="text",
            ),
            SectionNode(
                key="estimativa_custos",
                title="DA ESTIMATIVA DE CUSTOS",
                required=True,
                content_type="table",
                table_schema=TableSchema(
                    columns=[
                        TableColumn(key="item", label="Item"),
                        TableColumn(key="quantidade", label="Quantidade"),
                        TableColumn(key="valor_unitario", label="Valor Unitário"),
                        TableColumn(key="valor_total_estimado", label="Valor Total Estimado"),
                    ]
                ),
            ),
        ]
    elif dt == "documento_formalizacao_demanda":
        sections = [
            SectionNode(
                key="identificacao_demanda",
                title="DA IDENTIFICAÇÃO DA DEMANDA",
                required=True,
                content_type="table",
                table_schema=TableSchema(
                    columns=[
                        TableColumn(key="item", label="Item"),
                        TableColumn(key="descricao", label="Descrição"),
                        TableColumn(key="unidade", label="Unidade"),
                        TableColumn(key="quantidade", label="Quantidade"),
                        TableColumn(key="periodo", label="Período"),
                    ]
                ),
            ),
            SectionNode(
                key="justificativa",
                title="DA JUSTIFICATIVA",
                required=True,
                content_type="text",
            ),
            SectionNode(
                key="escopo_demanda",
                title="DO ESCOPO DA DEMANDA",
                required=True,
                content_type="text",
            ),
        ]
    else:
        sections = [
            SectionNode(
                key="objeto",
                title="DO OBJETO",
                required=True,
                content_type="text",
            ),
            SectionNode(
                key="disposicoes_gerais",
                title="DAS DISPOSIÇÕES GERAIS",
                required=True,
                content_type="text",
            ),
        ]

    return DocumentStructure(document_type=document_type, root_sections=sections)


def _collect_keys(sections: list[SectionNode]) -> set[str]:
    """Coleta todas as keys (incluindo subseções)."""
    found: set[str] = set()
    for s in sections:
        found.add(s.key)
        if s.children:
            found |= _collect_keys(s.children)
    return found


def _validate_semantics(document_type: str, structure: DocumentStructure) -> None:
    """
    Valida invariantes semânticas:
    - content_type definido e coerente com table_schema.
    - presença de seções obrigatórias mínimas por tipo.
    """
    # 1) content_type e table_schema coerentes (já validados em nível de schema,
    # mas reiteramos aqui para mensagens mais claras se necessário).
    for section in structure.root_sections:
        stack = [section]
        while stack:
            node = stack.pop()
            if node.content_type not in {"text", "table", "list"}:
                raise ValidationError(
                    [
                        {
                            "loc": ("content_type",),
                            "msg": f"content_type inválido em seção '{node.key}'.",
                            "type": "value_error",
                        }
                    ],
                    DocumentStructure,
                )
            if node.content_type == "table" and node.table_schema is None:
                raise ValidationError(
                    [
                        {
                            "loc": ("table_schema",),
                            "msg": f"Seção '{node.key}' marcada como 'table' deve conter table_schema.",
                            "type": "value_error",
                        }
                    ],
                    DocumentStructure,
                )
            stack.extend(node.children)

    # 2) seções mínimas obrigatórias por tipo de documento (chaves técnicas)
    required_by_type: dict[str, list[str]] = {
        "termo_referencia": ["objeto", "justificativa", "descricao_detalhada_objeto"],
        "estudo_tecnico_preliminar": ["objeto", "necessidade", "estimativa_custos"],
        "documento_formalizacao_demanda": ["identificacao_demanda", "justificativa"],
    }
    dt = document_type.strip().lower()
    expected_keys = required_by_type.get(dt)
    if expected_keys:
        keys = _collect_keys(structure.root_sections)
        missing = [k for k in expected_keys if k not in keys]
        if missing:
            raise ValidationError(
                [
                    {
                        "loc": ("root_sections",),
                        "msg": f"Seções obrigatórias ausentes para '{dt}': {', '.join(missing)}.",
                        "type": "value_error",
                    }
                ],
                DocumentStructure,
            )


def _build_llm_payload(req: StructureRequest) -> Dict[str, Any]:
    """Monta o payload para o /api/llm/generate da orquestração."""
    system_prompt = build_system_prompt(req.document_type)
    user_prompt = build_user_prompt(req.document_type, req.context.model_dump())

    # O módulo de orquestração espera: prompt, model?, stream?
    # Usamos um prompt concatenado (system + user) para simplificar.
    full_prompt = f"<<SYSTEM>>\\n{system_prompt}\\n\\n<<USER>>\\n{user_prompt}"
    return {
        "prompt": full_prompt,
        # Deixamos o modelo padrão a cargo do llm_api (OLLAMA_MODEL).
        "stream": False,
    }


def _parse_structure(raw: Any, document_type: str) -> DocumentStructure:
    """
    Converte a resposta bruta do modelo em DocumentStructure, validando o schema.
    """
    # raw deve ser um dict JSON; se vier string, tentamos dar json.loads.
    if isinstance(raw, str):
        raw = raw.strip()
        try:
            candidate = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValidationError([{"loc": ("__root__",), "msg": f"JSON inválido: {e}", "type": "value_error"}], DocumentStructure)
    else:
        candidate = raw

    if not isinstance(candidate, dict):
        raise ValidationError(
            [{"loc": ("__root__",), "msg": "Resposta não é um objeto JSON.", "type": "type_error"}],
            DocumentStructure,
        )

    # Se o modelo não preencher document_type, garantimos o eco do tipo solicitado.
    candidate.setdefault("document_type", document_type)

    return DocumentStructure.model_validate(candidate)


async def generate_structure(req: StructureRequest) -> StructureResponse:
    """
    Função principal do agente:
    - Tenta AGENT_MAX_RETRIES+1 vezes obter uma estrutura válida do modelo.
    - Em falha, retorna estrutura mínima de fallback.
    """
    last_error: str | None = None

    for attempt in range(AGENT_MAX_RETRIES + 1):
        try:
            payload = _build_llm_payload(req)
            data = await call_generate(payload)

            # A orquestração devolve algo em "data"; esperamos algo como {"response": "..."} ou similar.
            # Procuramos um campo óbvio de texto longo; se não houver, tentamos usar o próprio data.
            raw = data.get("response") if isinstance(data, dict) else data
            if raw is None:
                raw = data

            structure = _parse_structure(raw, req.document_type)
            _validate_semantics(req.document_type, structure)
            return StructureResponse(ok=True, structure=structure, retries=attempt)

        except (OrchestrationError, ValidationError, Exception) as e:
            last_error = str(e)
            # Nas tentativas seguintes, o prompt já vem mais forte via BASE_SYSTEM_PROMPT;
            # aqui poderíamos reforçar ainda mais conforme necessidade futura.
            continue

    # Fallback: estrutura mínima
    fallback = _minimal_structure_for(req.document_type)
    return StructureResponse(
        ok=False,
        structure=fallback,
        error=last_error or "Não foi possível obter estrutura válida do modelo.",
        retries=AGENT_MAX_RETRIES + 1,
    )

