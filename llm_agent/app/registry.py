"""
Registro manual de seções: carregar/salvar JSON com declarações lógicas e
atualização via chave (X-Update-Key). Normaliza para SectionCatalog para
uso no agente.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import REGISTRY_UPDATE_KEY, SECTIONS_REGISTRY_PATH
from .schemas import (
    ApplicabilityScope,
    ConditionalRule,
    SectionCatalog,
    SectionCatalogEntry,
    SectionsRegistry,
    TableSchema,
)


# Cache em memória após carregar do arquivo
_cached_catalog: Optional[SectionCatalog] = None


def _normalize_legal_basis(v: Optional[Any]) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, str):
        return v.strip() or None
    if isinstance(v, list):
        parts = [str(x).strip() for x in v if x is not None and str(x).strip()]
        return ", ".join(parts) if parts else None
    return None


def _normalize_conditional_rules(
    v: Optional[Any],
    default_if_path: str = "extras.tipo_objeto",
) -> List[ConditionalRule]:
    if v is None:
        return []
    if isinstance(v, list):
        return [ConditionalRule.model_validate(r) for r in v]
    if isinstance(v, dict):
        # Atalho: { "if": ["obra", "servico_continuado"], "if_path": "extras.tipo_objeto" }
        if_list = v.get("if")
        path = v.get("if_path") or default_if_path
        if isinstance(if_list, list) and if_list:
            return [
                ConditionalRule(rule_type="field_in", path=path, values=if_list)
            ]
    return []


def _normalize_scope(scope: Optional[Any]) -> Optional[ApplicabilityScope]:
    if scope is None:
        return None
    if isinstance(scope, ApplicabilityScope):
        return scope
    if isinstance(scope, dict):
        return ApplicabilityScope.model_validate(scope)
    return None


def registry_entry_to_catalog_entry(reg: Any) -> SectionCatalogEntry:
    """Converte uma entrada do registro (JSON/RegistrySectionEntry) para SectionCatalogEntry."""
    if hasattr(reg, "model_dump"):
        reg = reg.model_dump()
    required = bool(reg.get("required", False))
    if reg.get("status") == "required":
        required = True
    elif reg.get("status") == "optional":
        required = False

    conditional_rules = _normalize_conditional_rules(reg.get("conditional_rules"))
    table_schema = reg.get("table_schema")
    if table_schema is not None:
        table_schema = TableSchema.model_validate(table_schema)

    return SectionCatalogEntry(
        key=reg["key"],
        title=reg["title"],
        document_types=list(reg["document_types"]),
        content_type=reg.get("content_type", "text"),
        required=required,
        required_by=reg.get("required_by"),
        table_schema=table_schema,
        legal_basis=_normalize_legal_basis(reg.get("legal_basis")),
        conditional_rules=conditional_rules,
        applicability_scope=_normalize_scope(reg.get("applicability_scope")),
        version=str(reg.get("version", "1")),
        is_active=bool(reg.get("enabled", True)),
        effective_from=reg.get("effective_from"),
        parent_key=reg.get("parent_key"),
    )


def sections_registry_to_catalog(registry: SectionsRegistry) -> SectionCatalog:
    """Converte o registro completo (formato arquivo) em SectionCatalog para o agente."""
    entries = [registry_entry_to_catalog_entry(e) for e in registry.entries]
    return SectionCatalog(
        catalog_id=registry.catalog_id,
        catalog_version=registry.catalog_version,
        entries=entries,
    )


def load_registry_from_path(path: str) -> Optional[SectionsRegistry]:
    """Carrega e valida o JSON do arquivo; retorna None se arquivo não existir ou for inválido."""
    p = Path(path)
    if not p.is_file():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if not data or not isinstance(data, dict):
        return None
    entries = data.get("entries")
    if not isinstance(entries, list):
        return None
    try:
        return SectionsRegistry.model_validate(data)
    except Exception:
        return None


def save_registry_to_path(registry: SectionsRegistry, path: str) -> None:
    """Persiste o registro em JSON no caminho indicado (cria diretório se necessário)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = registry.model_dump(mode="json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)


def get_catalog_from_registry(reload: bool = False) -> Optional[SectionCatalog]:
    """
    Retorna o catálogo (SectionCatalog) a partir do registro em arquivo.
    Usa cache em memória; pass reload=True para forçar nova leitura do disco.
    """
    global _cached_catalog
    if reload:
        _cached_catalog = None
    if _cached_catalog is not None:
        return _cached_catalog
    reg = load_registry_from_path(SECTIONS_REGISTRY_PATH)
    if reg is None:
        return None
    _cached_catalog = sections_registry_to_catalog(reg)
    return _cached_catalog


def update_registry(new_registry: SectionsRegistry) -> None:
    """Salva o novo registro no arquivo configurado e invalida o cache."""
    save_registry_to_path(new_registry, SECTIONS_REGISTRY_PATH)
    get_catalog_from_registry(reload=True)


def is_valid_update_key(key: Optional[str]) -> bool:
    """Verifica se a chave de atualização é válida (e está configurada)."""
    if not REGISTRY_UPDATE_KEY or not REGISTRY_UPDATE_KEY.strip():
        return False
    return key is not None and key.strip() == REGISTRY_UPDATE_KEY.strip()
