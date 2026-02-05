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
from typing import Any, Dict, List, Tuple

from pydantic import ValidationError

from .catalog_filter import filter_eligible_sections
from .client import OrchestrationError, call_generate
from .config import AGENT_MAX_RETRIES
from .prompts import (
    CATALOG_SELECTION_SYSTEM_PROMPT,
    INTERPRETER_SYSTEM_PROMPT,
    build_catalog_selection_user_prompt,
    build_interpreter_user_prompt,
    build_system_prompt,
    build_user_prompt,
)
from .registry import get_catalog_from_registry
from .schemas import (
    ContextoBasico,
    DocumentStructure,
    SectionCatalogEntry,
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
                raise ValueError(f"content_type inválido em seção '{node.key}'.")
            if node.content_type == "table" and node.table_schema is None:
                raise ValueError(f"Seção '{node.key}' marcada como 'table' deve conter table_schema.")
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
            raise ValueError(f"Seções obrigatórias ausentes para '{dt}': {', '.join(missing)}.")


def _catalog_entry_to_section_node(
    entry: SectionCatalogEntry,
    context: ContextoBasico,
) -> SectionNode:
    """Converte uma entrada do catálogo em SectionNode; required considera required_by e contexto."""
    required = entry.required
    if entry.required_by and (context.extras or {}).get("requiring_authority") in entry.required_by:
        required = True
    return SectionNode(
        key=entry.key,
        title=entry.title,
        required=required,
        content_type=entry.content_type,
        table_schema=entry.table_schema,
        children=[],
    )


def _build_structure_from_catalog_selection(
    selected_keys: List[str],
    eligible_entries: List[SectionCatalogEntry],
    document_type: str,
    context: ContextoBasico,
) -> DocumentStructure:
    """
    Monta DocumentStructure a partir da lista ordenada de keys retornada pelo modelo,
    usando apenas definições do catálogo (sem invenção).
    """
    by_key = {e.key: _catalog_entry_to_section_node(e, context) for e in eligible_entries}
    selected_set = set(selected_keys)
    # Só considera keys que estão no catálogo elegível
    ordered = [k for k in selected_keys if k in by_key]
    if not ordered:
        # Fallback mínimo: pelo menos as raízes na ordem do catálogo
        ordered = [e.key for e in eligible_entries if (e.parent_key or "").strip() == ""]

    # Monta árvore: nós raiz (parent_key None ou não selecionado) e filhos
    roots: List[SectionNode] = []
    key_to_node = dict(by_key)
    for k in ordered:
        node = key_to_node.get(k)
        if not node:
            continue
        entry = next((e for e in eligible_entries if e.key == k), None)
        if not entry:
            continue
        parent_key = (entry.parent_key or "").strip() or None
        if not parent_key or parent_key not in selected_set or parent_key not in key_to_node:
            roots.append(node)
        else:
            parent = key_to_node[parent_key]
            parent.children.append(node)

    if not roots:
        roots = [key_to_node[k] for k in ordered if k in key_to_node]

    # Ordena raízes pela ordem em ordered; ordena children pela ordem em ordered
    order_idx = {k: i for i, k in enumerate(ordered)}
    roots.sort(key=lambda n: order_idx.get(n.key, 999))
    for node in key_to_node.values():
        node.children.sort(key=lambda n: order_idx.get(n.key, 999))

    return DocumentStructure(document_type=document_type, root_sections=roots)


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


def _build_interpreter_payload(user_prompt: str) -> Dict[str, Any]:
    """Monta o payload para chamar o LLM no papel de interpretador (texto livre → StructureRequest)."""
    full_prompt = (
        f"<<SYSTEM>>\n{INTERPRETER_SYSTEM_PROMPT.strip()}\n\n<<USER>>\n{build_interpreter_user_prompt(user_prompt)}"
    )
    return {"prompt": full_prompt, "stream": False}


async def interpret_user_prompt(user_prompt: str) -> StructureRequest:
    """
    Interpreta o texto livre do usuário e retorna um StructureRequest válido.

    Chama o LLM para extrair document_type e context; em falha de parsing ou
    orquestração, retorna fallback: termo_referencia com context.objeto = trecho do prompt.
    """
    try:
        payload = _build_interpreter_payload(user_prompt)
        data = await call_generate(payload)
        raw = data.get("response") if isinstance(data, dict) else data
        if raw is None:
            raw = data
        if isinstance(raw, dict):
            return StructureRequest.model_validate(raw)
        text = _strip_markdown_json(str(raw))
        candidate = json.loads(text)
        return StructureRequest.model_validate(candidate)
    except Exception:
        return StructureRequest(
            document_type="termo_referencia",
            context=ContextoBasico(
                objeto=(user_prompt[:500].strip() or "Documento solicitado pelo usuário.")
            ),
        )


def _strip_markdown_json(text: str) -> str:
    """
    Remove envoltório de bloco markdown (```json ... ```) se presente.
    Muitos modelos retornam JSON dentro de code fence.
    """
    text = text.strip()
    if text.startswith("```"):
        # Remove abertura: ```json ou ```
        first_line = text.split("\n", 1)[0]
        if first_line.startswith("```"):
            text = text[len(first_line) :].lstrip("\n")
        if text.endswith("```"):
            text = text[: text.rfind("```")].rstrip()
    return text


def _parse_structure(raw: Any, document_type: str) -> DocumentStructure:
    """
    Converte a resposta bruta do modelo em DocumentStructure, validando o schema.
    """
    # raw deve ser um dict JSON; se vier string, removemos markdown e tentamos json.loads.
    if isinstance(raw, str):
        raw = _strip_markdown_json(raw)
        try:
            candidate = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON inválido: {e}") from e
    else:
        candidate = raw

    if not isinstance(candidate, dict):
        raise ValueError("Resposta não é um objeto JSON.")

    # Se o modelo não preencher document_type, garantimos o eco do tipo solicitado.
    candidate.setdefault("document_type", document_type)

    return DocumentStructure.model_validate(candidate)


def _parse_catalog_selection_response(raw: Any, eligible_keys: set) -> List[str]:
    """
    Extrai a lista section_keys da resposta do modelo (catálogo versionável).
    Retorna apenas keys que estão em eligible_keys; ordem preservada.
    """
    if isinstance(raw, str):
        raw = _strip_markdown_json(raw)
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, dict):
        return []
    keys = raw.get("section_keys")
    if not isinstance(keys, list):
        return []
    return [k for k in keys if isinstance(k, str) and k.strip() in eligible_keys]


async def _generate_structure_with_catalog(req: StructureRequest) -> StructureResponse:
    """
    Fluxo com catálogo versionável: filtra seções elegíveis de forma determinística,
    pede ao modelo apenas a ordenação/seleção (lista de keys), monta estrutura do catálogo.
    """
    eligible = filter_eligible_sections(
        req.sections_catalog, req.document_type, req.context
    )
    eligible_keys = {e.key for e in eligible}
    if not eligible:
        fallback = _minimal_structure_for(req.document_type)
        return StructureResponse(
            ok=False,
            structure=fallback,
            error="Nenhuma seção do catálogo elegível para o tipo e contexto informados.",
            retries=0,
        )

    system_prompt = CATALOG_SELECTION_SYSTEM_PROMPT.strip()
    user_prompt = build_catalog_selection_user_prompt(
        eligible, req.document_type, req.context.model_dump()
    )
    full_prompt = f"<<SYSTEM>>\n{system_prompt}\n\n<<USER>>\n{user_prompt}"
    payload = {"prompt": full_prompt, "stream": False}

    last_error: str | None = None
    for attempt in range(AGENT_MAX_RETRIES + 1):
        try:
            data = await call_generate(payload)
            raw = data.get("response") if isinstance(data, dict) else data
            if raw is None:
                raw = data
            selected = _parse_catalog_selection_response(raw, eligible_keys)
            if not selected:
                # Fallback: ordem do catálogo (raízes primeiro)
                selected = [e.key for e in eligible if (e.parent_key or "").strip() == ""]
                if not selected:
                    selected = [e.key for e in eligible]
            structure = _build_structure_from_catalog_selection(
                selected, eligible, req.document_type, req.context
            )
            return StructureResponse(ok=True, structure=structure, retries=attempt)
        except (OrchestrationError, Exception) as e:
            last_error = str(e)
            continue

    # Fallback: todas as elegíveis na ordem do catálogo
    selected = [e.key for e in eligible]
    structure = _build_structure_from_catalog_selection(
        selected, eligible, req.document_type, req.context
    )
    return StructureResponse(
        ok=False,
        structure=structure,
        error=last_error or "Resposta do modelo inválida; usada ordem padrão do catálogo.",
        retries=AGENT_MAX_RETRIES + 1,
    )


async def generate_structure(req: StructureRequest) -> StructureResponse:
    """
    Função principal do agente:
    - Se sections_catalog for informado: fluxo versionável (seleção/ordenação apenas).
    - Se não, mas existir registro em arquivo (SECTIONS_REGISTRY_PATH): usa catálogo do registro.
    - Caso contrário: geração livre com hints; fallback para estrutura mínima.
    """
    catalog = req.sections_catalog
    if catalog is None or not catalog.entries:
        catalog = get_catalog_from_registry()
    if catalog is not None and catalog.entries:
        req_with_catalog = StructureRequest(
            document_type=req.document_type,
            context=req.context,
            sections_catalog=catalog,
        )
        return await _generate_structure_with_catalog(req_with_catalog)

    last_error: str | None = None

    for attempt in range(AGENT_MAX_RETRIES + 1):
        try:
            payload = _build_llm_payload(req)
            data = await call_generate(payload)

            # A orquestração devolve algo em "data"; esperamos algo como {"response": "..."} ou similar.
            raw = data.get("response") if isinstance(data, dict) else data
            if raw is None:
                raw = data

            structure = _parse_structure(raw, req.document_type)
            _validate_semantics(req.document_type, structure)
            return StructureResponse(ok=True, structure=structure, retries=attempt)

        except (OrchestrationError, ValidationError, Exception) as e:
            last_error = str(e)
            continue

    # Fallback: estrutura mínima
    fallback = _minimal_structure_for(req.document_type)
    return StructureResponse(
        ok=False,
        structure=fallback,
        error=last_error or "Não foi possível obter estrutura válida do modelo.",
        retries=AGENT_MAX_RETRIES + 1,
    )

