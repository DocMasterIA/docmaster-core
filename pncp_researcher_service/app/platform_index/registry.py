from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional

from ..config import (
    PNCP_LOCAL_DB_PATH,
    PRICE_CROSSLINK_DB_PATH,
    PRICE_PLATFORM_DATA_ROOT,
    TCE_RS_LOCAL_DB_PATH,
)

SchemaKind = Literal["legacy_pncp", "platform_index", "api_only"]


@dataclass(frozen=True)
class PlatformIndexSpec:
    """Metadados de uma plataforma cadastrada e seu arquivo SQLite (se houver)."""

    id: str
    label: str
    db_path: Optional[str]
    schema_kind: SchemaKind
    inciso_default: str
    esfera_default: str
    uf_scope: Optional[str] = None
    enabled: bool = True
    search_ready: bool = False
    # feed = alimentação/ingest; researcher = leitura na busca; both = PNCP legacy monolito
    index_writer: Literal["feed", "researcher", "both"] = "feed"

    def db_exists(self) -> bool:
        if not self.db_path:
            return False
        return os.path.isfile(self.db_path)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "db_path": self.db_path,
            "schema_kind": self.schema_kind,
            "inciso_default": self.inciso_default,
            "esfera_default": self.esfera_default,
            "uf_scope": self.uf_scope,
            "enabled": self.enabled,
            "search_ready": self.search_ready,
            "index_writer": self.index_writer,
            "db_exists": self.db_exists(),
        }


def _platform_db_path(platform_id: str) -> str:
    safe = platform_id.strip().lower().replace("/", "_")
    return os.path.join(PRICE_PLATFORM_DATA_ROOT, f"{safe}_local.db")


_PLATFORM_SPECS: Dict[str, PlatformIndexSpec] = {
    "pncp": PlatformIndexSpec(
        id="pncp",
        label="PNCP",
        db_path=PNCP_LOCAL_DB_PATH,
        schema_kind="legacy_pncp",
        inciso_default="inciso_i",
        esfera_default="federal",
        search_ready=True,
        index_writer="feed",
    ),
    "tce_rs": PlatformIndexSpec(
        id="tce_rs",
        label="TCE-RS (LicitaCon)",
        db_path=TCE_RS_LOCAL_DB_PATH,
        schema_kind="platform_index",
        inciso_default="inciso_ii",
        esfera_default="estadual",
        uf_scope="RS",
        enabled=True,
        search_ready=False,
    ),
}


def register_platform_spec(spec: PlatformIndexSpec) -> None:
    _PLATFORM_SPECS[spec.id] = spec


def list_platform_specs(*, include_disabled: bool = False) -> List[PlatformIndexSpec]:
    specs = list(_PLATFORM_SPECS.values())
    if not include_disabled:
        specs = [s for s in specs if s.enabled]
    return sorted(specs, key=lambda s: s.id)


def get_platform_spec(platform_id: str) -> Optional[PlatformIndexSpec]:
    key = str(platform_id or "").strip().lower()
    return _PLATFORM_SPECS.get(key)


def crosslink_db_path() -> str:
    return PRICE_CROSSLINK_DB_PATH


def default_platform_db_path(platform_id: str) -> str:
    """Caminho padrão para nova plataforma com índice local."""
    return _platform_db_path(platform_id)
