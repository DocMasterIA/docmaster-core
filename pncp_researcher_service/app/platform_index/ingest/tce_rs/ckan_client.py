from __future__ import annotations

"""
Cliente CKAN TCE-RS — stub para discovery/download (1-TCE-DIS / 1-TCE-CRON).

Quando as URLs e datasets forem confirmados, implementar:
  - package_search / package_show
  - download de ZIP/CSV para TCE_RS_INGEST_DATA_DIR
"""
from typing import Any, Dict, List


async def list_licitacon_resources() -> List[Dict[str, Any]]:
    """Placeholder: retorna lista vazia até mapearmos datasets no CKAN."""
    return []


async def download_latest_licitacon(*, dest_dir: str) -> Dict[str, Any]:
    """Placeholder: falha explícita até integração CKAN estar pronta."""
    return {
        "ok": False,
        "erro": "ckan_download_not_implemented",
        "hint": "Use ingest local via data_dir ou use_sample=true",
    }
