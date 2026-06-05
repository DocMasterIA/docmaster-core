"""Métricas de cobertura da caça de itens PNCP (janela 365d + fila + buracos)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from .ingest_dates import resolve_backfill_window
from .ingest_queue import count_contracts_without_items, queue_stats
from .local_index import ensure_local_index, ingest_operational_status, local_index_stats


def ingest_coverage_status() -> Dict[str, Any]:
    ensure_local_index()
    data_inicial, data_final, dias = resolve_backfill_window()
    stats = local_index_stats()
    ingest = ingest_operational_status()
    queue = queue_stats()
    contracts_sem_itens = count_contracts_without_items()

    scopes = ingest.get("scopes") or []
    json_invalid = sum(
        1 for s in scopes if (s.get("last_error_kind") or "") == "json_invalid"
    )
    paused = int(ingest.get("scopes_paused") or 0)

    total_contratos = int(stats.get("total_contratos") or 0)
    cobertura_itens_pct = None
    if total_contratos > 0:
        cobertura_itens_pct = round(
            100.0 * (total_contratos - contracts_sem_itens) / total_contratos,
            2,
        )

    return {
        "ok": True,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "window": {
            "data_inicial": data_inicial,
            "data_final": data_final,
            "dias": dias,
        },
        "index": {
            "total_itens": int(stats.get("total_itens") or 0),
            "total_contratos": total_contratos,
            "fornecedor": stats.get("fornecedor"),
        },
        "gaps": {
            "contratos_sem_itens": contracts_sem_itens,
            "cobertura_itens_contratos_pct": cobertura_itens_pct,
            "scopes_json_invalid": json_invalid,
            "scopes_paused": paused,
        },
        "queue": queue,
        "ingest": {
            "overall_status": ingest.get("overall_status"),
            "scopes_total": ingest.get("scopes_total"),
            "scopes_active": ingest.get("scopes_active"),
        },
    }
