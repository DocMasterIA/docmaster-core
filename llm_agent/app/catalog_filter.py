"""
Filtragem determinística do catálogo de seções versionáveis.

Avalia escopo de aplicabilidade e regras condicionais contra o contexto;
o modelo de IA não infere essas condições — elas vêm do registro da seção.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .schemas import (
    ApplicabilityScope,
    ConditionalRule,
    ContextoBasico,
    SectionCatalog,
    SectionCatalogEntry,
)


def _context_to_dict(context: ContextoBasico) -> Dict[str, Any]:
    """Converte o contexto em dict para acesso por path (ex.: extras.valor_estimado)."""
    d: Dict[str, Any] = {
        "objeto": context.objeto or "",
        "orgao": (context.orgao or "").strip() or None,
        "modalidade": (context.modalidade or "").strip() or None,
        "extras": context.extras or {},
    }
    return d


def _get_value_by_path(data: Dict[str, Any], path: str) -> Any:
    """Obtém valor em data pelo path (ex.: 'extras.valor_estimado')."""
    parts = path.strip().split(".")
    current: Any = data
    for p in parts:
        if current is None:
            return None
        if isinstance(current, dict) and p in current:
            current = current[p]
        else:
            return None
    return current


def _is_empty(v: Any) -> bool:
    """Considera None, string vazia e lista/dict vazios como vazios."""
    if v is None:
        return True
    if isinstance(v, str):
        return not v.strip()
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return False


def evaluate_conditional_rule(rule: ConditionalRule, context_dict: Dict[str, Any]) -> bool:
    """
    Avalia uma regra condicional contra o contexto. Determinístico.
    """
    value = _get_value_by_path(context_dict, rule.path)
    if rule.rule_type == "has_field":
        return not _is_empty(value)
    if rule.rule_type == "field_equals":
        return value == rule.value
    if rule.rule_type == "field_in":
        if rule.values is None:
            return False
        return value in rule.values
    return False


def applies_to_scope(
    scope: ApplicabilityScope | None,
    context: ContextoBasico,
    context_dict: Dict[str, Any],
) -> bool:
    """
    Verifica se o contexto indica que o escopo da seção se aplica.

    Se scope for None, não há restrição (retorna True).
    Se scope tiver campos preenchidos, cada um deve bater com o contexto
    (órgão, extras.municipio, extras.estado, extras.tipo_administracao etc.).
    """
    if scope is None:
        return True
    if scope.orgao is not None and (scope.orgao or "").strip():
        ctx_orgao = (context.orgao or "").strip().lower()
        if ctx_orgao != (scope.orgao or "").strip().lower():
            return False
    if scope.municipio is not None and (scope.municipio or "").strip():
        ctx_mun = (context_dict.get("extras") or {}).get("municipio") or ""
        if isinstance(ctx_mun, str) and ctx_mun.strip():
            if ctx_mun.strip().lower() != (scope.municipio or "").strip().lower():
                return False
        else:
            return False
    if scope.estado is not None and (scope.estado or "").strip():
        ctx_est = (context_dict.get("extras") or {}).get("estado") or ""
        if isinstance(ctx_est, str) and ctx_est.strip():
            if ctx_est.strip().lower() != (scope.estado or "").strip().lower():
                return False
        else:
            return False
    if scope.tipo_administracao is not None and (scope.tipo_administracao or "").strip():
        ctx_tipo = (context_dict.get("extras") or {}).get("tipo_administracao") or ""
        if isinstance(ctx_tipo, str) and ctx_tipo.strip():
            if ctx_tipo.strip().lower() != (scope.tipo_administracao or "").strip().lower():
                return False
        else:
            return False
    return True


def filter_eligible_sections(
    catalog: SectionCatalog,
    document_type: str,
    context: ContextoBasico,
) -> List[SectionCatalogEntry]:
    """
    Retorna apenas as seções do catálogo elegíveis para o tipo de documento
    e para o contexto, segundo escopo e regras condicionais (avaliação determinística).
    """
    doc_type = document_type.strip().lower()
    context_dict = _context_to_dict(context)
    eligible: List[SectionCatalogEntry] = []

    for entry in catalog.entries:
        if not entry.is_active:
            continue
        if doc_type not in [t.strip().lower() for t in entry.document_types]:
            continue
        if not applies_to_scope(entry.applicability_scope, context, context_dict):
            continue
        if entry.conditional_rules:
            if not all(
                evaluate_conditional_rule(r, context_dict) for r in entry.conditional_rules
            ):
                continue
        eligible.append(entry)

    return eligible
