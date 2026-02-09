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

import ast
import json
from typing import Any, Dict, List, Tuple

from pydantic import ValidationError

from .catalog_filter import filter_eligible_sections
from .client import OrchestrationError, call_generate
from .config import AGENT_MAX_RETRIES
from .prompts import (
    CATALOG_SELECTION_SYSTEM_PROMPT,
    CATALOG_SELECTION_WITH_MATCHES_SYSTEM_PROMPT,
    DOCUMENT_CLAUSE_STRUCTURE_SYSTEM_PROMPT,
    INTERPRETER_SYSTEM_PROMPT,
    build_catalog_selection_user_prompt,
    build_interpreter_user_prompt,
    build_system_prompt,
    build_user_prompt,
)
from .registry import get_catalog_from_registry
from .schemas import (
    ClauseStructureRequest,
    ClauseStructureResponse,
    ContextoBasico,
    DocumentStructure,
    SectionCatalogEntry,
    SectionMatchAnnotation,
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
    """Converte uma entrada do catálogo em SectionNode (nível estrutural apenas)."""
    return SectionNode(
        key=entry.key,
        title=entry.title,
        required=entry.required,
        content_type=entry.content_type,
        table_schema=entry.table_schema,
        children=[],
    )


def _collect_keys_in_order(nodes: List[SectionNode]) -> List[str]:
    """Coleta keys em ordem (DFS) a partir dos nós raiz."""
    out: List[str] = []
    for n in nodes:
        out.append(n.key)
        if n.children:
            out.extend(_collect_keys_in_order(n.children))
    return out


def _enrich_node_from_catalog(
    node: SectionNode, eligible_by_key: Dict[str, SectionCatalogEntry]
) -> None:
    """Enriquece um SectionNode com título/content_type/table_schema/required do catálogo (in-place)."""
    if node.key in eligible_by_key:
        e = eligible_by_key[node.key]
        node.title = e.title
        node.content_type = e.content_type
        node.required = e.required
        node.table_schema = e.table_schema
    for ch in node.children:
        _enrich_node_from_catalog(ch, eligible_by_key)


def _merge_base_with_catalog(
    base_structure: DocumentStructure,
    eligible: List[SectionCatalogEntry],
    selected_keys: List[str],
    context: ContextoBasico,
) -> DocumentStructure:
    """
    Base (from hints) + catálogo: enriquece nós da base com dados do catálogo quando a key
    existe em ambos; adiciona ao final as seções só do catálogo (selected_keys não presentes na base).
    """
    eligible_by_key = {e.key: e for e in eligible}
    base_keys_ordered = _collect_keys_in_order(base_structure.root_sections)
    catalog_only_keys = [k for k in selected_keys if k not in base_keys_ordered and k in eligible_by_key]
    for root in base_structure.root_sections:
        _enrich_node_from_catalog(root, eligible_by_key)
    extra_nodes = [
        _catalog_entry_to_section_node(eligible_by_key[k], context)
        for k in catalog_only_keys
    ]
    merged_roots = list(base_structure.root_sections) + extra_nodes
    return DocumentStructure(
        document_type=base_structure.document_type,
        root_sections=merged_roots,
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
        first_line = text.split("\n", 1)[0]
        if first_line.startswith("```"):
            text = text[len(first_line) :].lstrip("\n")
        if text.endswith("```"):
            text = text[: text.rfind("```")].rstrip()
    return text


def _extract_code_fence(text: str, fence: str = "```") -> str | None:
    """Extrai o primeiro bloco entre ``` e ``` (ou entre fence e fence). Retorna None se não achar."""
    idx = text.find(fence)
    if idx < 0:
        return None
    idx2 = text.find(fence, idx + len(fence))
    if idx2 < 0:
        return None
    block = text[idx + len(fence) : idx2].strip()
    if block.lower().startswith("json"):
        block = block[4:].lstrip()
    return block if block.startswith("{") else None


def _extract_json_object_respecting_strings(text: str) -> str:
    """
    Extrai o primeiro objeto { ... } respeitando strings (não conta { } dentro de "..." ou '...').
    Evita quebra quando o modelo coloca chaves no título ou em valores.
    """
    start = text.find("{")
    if start < 0:
        return text
    i = start
    depth = 0
    in_double = False
    in_single = False
    escape = False
    quote_char: str | None = None
    n = len(text)
    while i < n:
        c = text[i]
        if escape:
            escape = False
            i += 1
            continue
        if c == "\\" and (in_double or in_single):
            escape = True
            i += 1
            continue
        if in_double or in_single:
            if c == quote_char:
                in_double = False
                in_single = False
                quote_char = None
            i += 1
            continue
        if c == '"':
            in_double = True
            quote_char = '"'
            i += 1
            continue
        if c == "'":
            in_single = True
            quote_char = "'"
            i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        i += 1
    return text[start:].rstrip()


def _raw_to_structure_candidate(raw: Any) -> dict:
    """
    Converte resposta bruta (string ou dict) em dict para DocumentStructure.
    Tenta: parse direto, bloco ```json```, extração { } respeitando strings, ast.literal_eval.
    """
    if isinstance(raw, dict):
        return raw
    text = str(raw).strip()
    # 1) Parse direto (após remover markdown genérico)
    cleaned = _strip_markdown_json(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # 2) Bloco explícito ```json ... ```
    fence_block = _extract_code_fence(text)
    if fence_block:
        try:
            return json.loads(fence_block)
        except json.JSONDecodeError:
            pass
        if fence_block.strip().startswith("{") and "'" in fence_block:
            try:
                obj = ast.literal_eval(fence_block)
                if isinstance(obj, dict):
                    return obj
            except (ValueError, SyntaxError):
                pass
    # 3) Extrair { } respeitando strings (evita quebrar em títulos/valores com { ou })
    extracted = _extract_json_object_respecting_strings(cleaned)
    if extracted and extracted != cleaned:
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            pass
        if extracted.strip().startswith("{") and "'" in extracted:
            try:
                obj = ast.literal_eval(extracted)
                if isinstance(obj, dict):
                    return obj
            except (ValueError, SyntaxError):
                pass
    # 4) Última tentativa: extração por chaves sem respeitar strings (comportamento antigo)
    start = cleaned.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(cleaned)):
            if cleaned[i] == "{":
                depth += 1
            elif cleaned[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(cleaned[start : i + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError("JSON inválido: não foi possível extrair objeto da resposta.")


def _parse_structure(raw: Any, document_type: str) -> DocumentStructure:
    """
    Converte a resposta bruta do modelo em DocumentStructure, validando o schema.
    """
    try:
        candidate = _raw_to_structure_candidate(raw)
    except ValueError as e:
        raise e from e

    if not isinstance(candidate, dict):
        raise ValueError("Resposta não é um objeto JSON.")

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


def _parse_catalog_selection_matches(
    raw: Any, eligible_keys: set
) -> List[SectionMatchAnnotation]:
    """
    Extrai a lista matches da resposta (key, user_phrase, confidence).
    Só retorna entradas cuja key está em eligible_keys e confidence é high/medium/low.
    """
    if isinstance(raw, str):
        raw = _strip_markdown_json(raw)
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, dict):
        return []
    matches = raw.get("matches")
    if not isinstance(matches, list):
        return []
    out: List[SectionMatchAnnotation] = []
    for m in matches:
        if not isinstance(m, dict):
            continue
        key = m.get("key")
        user_phrase = m.get("user_phrase")
        confidence = m.get("confidence")
        if (
            isinstance(key, str)
            and key.strip() in eligible_keys
            and isinstance(user_phrase, str)
            and user_phrase.strip()
            and confidence in ("high", "medium", "low")
        ):
            out.append(
                SectionMatchAnnotation(
                    key=key.strip(),
                    user_phrase=user_phrase.strip(),
                    confidence=confidence,
                )
            )
    return out


async def _generate_structure_with_catalog(
    req: StructureRequest,
    base_structure: DocumentStructure | None = None,
) -> StructureResponse:
    """
    Fluxo com catálogo: pede ao modelo a ordenação/seleção (lista de keys) entre as elegíveis.
    Se base_structure for informado, usa base (hints) + catálogo: enriquece a base e adiciona
    seções só do catálogo. Caso contrário, monta a estrutura apenas a partir do catálogo.
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

    use_matches = bool((req.user_prompt or "").strip())
    system_prompt = (
        CATALOG_SELECTION_WITH_MATCHES_SYSTEM_PROMPT.strip()
        if use_matches
        else CATALOG_SELECTION_SYSTEM_PROMPT.strip()
    )
    user_prompt_text = build_catalog_selection_user_prompt(
        eligible,
        req.document_type,
        req.context.model_dump(),
        user_prompt=req.user_prompt if use_matches else None,
    )
    full_prompt = f"<<SYSTEM>>\n{system_prompt}\n\n<<USER>>\n{user_prompt_text}"
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
                selected = [e.key for e in eligible if (e.parent_key or "").strip() == ""]
                if not selected:
                    selected = [e.key for e in eligible]
            section_matches = (
                _parse_catalog_selection_matches(raw, eligible_keys) if use_matches else None
            )
            if base_structure is not None:
                structure = _merge_base_with_catalog(
                    base_structure, eligible, selected, req.context
                )
            else:
                structure = _build_structure_from_catalog_selection(
                    selected, eligible, req.document_type, req.context
                )
            return StructureResponse(
                ok=True,
                structure=structure,
                retries=attempt,
                section_matches=section_matches,
            )
        except (OrchestrationError, Exception) as e:
            last_error = str(e)
            continue

    selected = [e.key for e in eligible]
    if base_structure is not None:
        structure = _merge_base_with_catalog(
            base_structure, eligible, selected, req.context
        )
    else:
        structure = _build_structure_from_catalog_selection(
            selected, eligible, req.document_type, req.context
        )
    return StructureResponse(
        ok=False,
        structure=structure,
        error=last_error or "Resposta do modelo inválida; usada ordem padrão do catálogo.",
        retries=AGENT_MAX_RETRIES + 1,
        section_matches=None,
    )


async def generate_structure(req: StructureRequest) -> StructureResponse:
    """
    Função principal do agente:
    - Sempre obtém a base (LLM + DOCUMENT_TYPE_HINTS); fallback para estrutura mínima se falhar.
    - Se houver catálogo com seções elegíveis: aplica fluxo de catálogo em cima da base (enriquece
      nós com dados do catálogo e adiciona seções só do catálogo). Senão, devolve só a base.
    """
    catalog = req.sections_catalog
    if catalog is None or not catalog.entries:
        catalog = get_catalog_from_registry()
    eligible = (
        filter_eligible_sections(catalog, req.document_type, req.context)
        if catalog is not None and catalog.entries
        else []
    )

    # 1) Sempre obter base (LLM + hints)
    base_structure: DocumentStructure | None = None
    last_error: str | None = None
    base_retries = 0
    for attempt in range(AGENT_MAX_RETRIES + 1):
        try:
            payload = _build_llm_payload(req)
            data = await call_generate(payload)
            raw = data.get("response") if isinstance(data, dict) else data
            if raw is None:
                raw = data
            base_structure = _parse_structure(raw, req.document_type)
            _validate_semantics(req.document_type, base_structure)
            base_retries = attempt
            break
        except (OrchestrationError, ValidationError, Exception) as e:
            last_error = str(e)
            continue
    used_base_fallback = base_structure is None
    if base_structure is None:
        base_structure = _minimal_structure_for(req.document_type)

    # 2) Se há elegíveis, base + fluxo de catálogo (enriquecer e adicionar seções do catálogo)
    if eligible and catalog is not None:
        req_with_catalog = StructureRequest(
            document_type=req.document_type,
            context=req.context,
            sections_catalog=catalog,
            user_prompt=req.user_prompt,
        )
        return await _generate_structure_with_catalog(
            req_with_catalog, base_structure=base_structure
        )

    return StructureResponse(
        ok=not used_base_fallback,
        structure=base_structure,
        error=last_error if used_base_fallback else None,
        retries=base_retries if not used_base_fallback else AGENT_MAX_RETRIES + 1,
    )


async def generate_clause_structure(req: ClauseStructureRequest) -> ClauseStructureResponse:
    """
    Gera apenas a estrutura hierárquica de cláusulas/subcláusulas (esqueleto).

    Usa DOCUMENT_CLAUSE_STRUCTURE_SYSTEM_PROMPT e retorna uma árvore de ClauseNode
    sem texto jurídico final; decisão sobre quais subcláusulas ativar será feita
    posteriormente pelo módulo de RAG/composição.
    """
    system_prompt = DOCUMENT_CLAUSE_STRUCTURE_SYSTEM_PROMPT.strip()

    # Monta prompt de usuário com tipo, contexto e, opcionalmente, seção e descrição base.
    parts: List[str] = []
    parts.append(f"Tipo de documento: {req.document_type}")
    if req.section_key:
        parts.append(f"Seção estrutural relacionada (section_key): {req.section_key}")
    if req.base_description:
        parts.append(f"Descrição base da cláusula/assunto: {req.base_description}")
    if req.context:
        try:
            ctx_json = json.dumps(req.context, ensure_ascii=False, indent=2)
        except Exception:
            ctx_json = str(req.context)
        parts.append(f"Contexto (JSON):\n{ctx_json}")

    user_prompt = (
        "Gerar APENAS o esqueleto estrutural de cláusulas e subcláusulas "
        "(sem texto jurídico), no seguinte formato JSON:\n\n"
        "{\n"
        '  "root_clauses": [\n'
        "    {\n"
        '      "logical_id": "EXEMPLO_CLAUSULA",\n'
        '      "title": "Título apenas para cláusulas de topo",\n'
        '      "status": "active",\n'
        '      "version": "1.0",\n'
        '      "scope": { "nivel": "federal" },\n'
        '      "children": [\n'
        "        {\n"
        '          "logical_id": "EXEMPLO_SUBCLAUSULA",\n'
        '          "status": "active",\n'
        '          "children": []\n'
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Regras importantes:\n"
        "- Subcláusulas NÃO devem ter título (title ausente ou nulo).\n"
        "- Não gere texto jurídico, apenas a estrutura e identificadores lógicos.\n"
        "- Retorne APENAS o JSON, sem explicações.\n\n"
    )
    user_prompt += "\n".join(parts)

    full_prompt = f"<<SYSTEM>>\n{system_prompt}\n\n<<USER>>\n{user_prompt}"
    payload = {"prompt": full_prompt, "stream": False}

    last_error: str | None = None
    for attempt in range(AGENT_MAX_RETRIES + 1):
        try:
            data = await call_generate(payload)
            raw = data.get("response") if isinstance(data, dict) else data
            if raw is None:
                raw = data

            # Aceita string ou dict; remove ```json ``` se vier.
            if isinstance(raw, str):
                raw_clean = raw.strip()
                if raw_clean.startswith("```"):
                    # Reaproveita utilidade de limpar markdown JSON.
                    from .agent import _strip_markdown_json  # type: ignore  # local import to avoid cycle

                    raw_clean = _strip_markdown_json(raw_clean)
                candidate = json.loads(raw_clean)
            else:
                candidate = raw

            if not isinstance(candidate, dict):
                raise ValueError("Resposta não é um objeto JSON.")

            # Permitir que o modelo omita root_clauses em casos extremos; validamos via Pydantic.
            resp = ClauseStructureResponse.model_validate(candidate)
            # Se root_clauses vier vazio ou None, consideramos falha.
            if not resp.root_clauses:
                raise ValueError("root_clauses vazio ou ausente na resposta do modelo.")

            return ClauseStructureResponse(
                ok=True,
                root_clauses=resp.root_clauses,
                error=None,
                retries=attempt,
            )
        except (OrchestrationError, Exception) as e:
            last_error = str(e)
            continue

    return ClauseStructureResponse(
        ok=False,
        root_clauses=None,
        error=last_error or "Não foi possível obter estrutura de cláusulas válida do modelo.",
        retries=AGENT_MAX_RETRIES + 1,
    )

