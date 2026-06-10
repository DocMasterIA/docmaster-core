"""Estado runtime da ingestão: heartbeat, detecção de parada e logs visíveis no Docker."""
from __future__ import annotations

import logging
import sys
import time
from typing import Any, Dict, Optional

from . import config

logger = logging.getLogger(__name__)

_logging_configured = False
_worker_started_at: float = 0.0
_last_batch_at: float = 0.0
_last_progress_at: float = 0.0
_last_pending: Optional[int] = None
_last_batch_summary: Dict[str, Any] = {}
_stall_recoveries: int = 0
_last_stall_recovery_at: float = 0.0


def configure_service_logging() -> None:
    """Garante INFO do worker/maintenance no stdout (visível em docker logs)."""
    global _logging_configured
    if _logging_configured:
        return
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)
    for name in (
        "pncp_researcher_service.app.ingest_worker",
        "pncp_researcher_service.app.ingest_maintenance",
        "pncp_researcher_service.app.ingest_planner",
        "pncp_researcher_service.app.ingest_runtime",
    ):
        lg = logging.getLogger(name)
        lg.setLevel(logging.INFO)
        if not any(isinstance(h, logging.StreamHandler) for h in lg.handlers):
            lg.addHandler(handler)
        lg.propagate = False
    _logging_configured = True


def mark_worker_started() -> None:
    global _worker_started_at, _last_progress_at, _last_batch_at
    now = time.monotonic()
    _worker_started_at = now
    _last_progress_at = now
    _last_batch_at = now


def record_batch_result(result: Dict[str, Any]) -> None:
    """Atualiza heartbeat após cada tick do worker."""
    global _last_batch_at, _last_progress_at, _last_pending, _last_batch_summary
    now = time.monotonic()
    _last_batch_at = now
    _last_batch_summary = dict(result or {})

    queue = result.get("queue") if isinstance(result.get("queue"), dict) else {}
    pending = int(queue.get("pending") or 0)
    progress_units = int(result.get("items_ok") or 0) + int(result.get("catalog_ok") or 0)

    if progress_units > 0:
        _last_progress_at = now
    elif _last_pending is not None and pending < _last_pending:
        _last_progress_at = now

    _last_pending = pending


def seconds_since_progress() -> float:
    if _last_progress_at <= 0:
        return 0.0
    return max(0.0, time.monotonic() - _last_progress_at)


def is_ingest_stalled() -> bool:
    if not config.PNCP_INGEST_WORKER_ENABLED or not config.PNCP_INGEST_QUEUE_ENABLED:
        return False
    pending = int(_last_pending or 0)
    if pending < max(1, int(config.PNCP_INGEST_STALL_MIN_PENDING)):
        return False
    return seconds_since_progress() >= float(config.PNCP_INGEST_STALL_SECONDS)


def maybe_log_heartbeat(*, force: bool = False) -> None:
    """Log periódico para docker logs — prova de vida sem monitor manual."""
    interval = max(60.0, float(config.PNCP_INGEST_HEARTBEAT_LOG_SECONDS))
    now = time.monotonic()
    last_log = float(_last_batch_summary.get("_last_heartbeat_mono") or 0.0)
    if not force and (now - last_log) < interval:
        return
    _last_batch_summary["_last_heartbeat_mono"] = now
    stalled = is_ingest_stalled()
    logger.info(
        "ingest heartbeat pending=%s processing=%s items_ok=%s errors=%s "
        "since_progress=%.0fs stalled=%s stall_recoveries=%s",
        _last_pending,
        (_last_batch_summary.get("queue") or {}).get("processing"),
        _last_batch_summary.get("items_ok"),
        _last_batch_summary.get("errors"),
        seconds_since_progress(),
        stalled,
        _stall_recoveries,
    )


def run_stall_recovery_if_needed() -> Optional[Dict[str, Any]]:
    """
    Se a fila tem trabalho mas não há progresso há N minutos, autocura agressiva + replanejamento.
    Retorna dict de ações se recuperou; None se não estava parada.
    """
    global _stall_recoveries, _last_stall_recovery_at, _last_progress_at

    if not config.PNCP_INGEST_STALL_RECOVERY_ENABLED or not is_ingest_stalled():
        return None

    # Evita rajada de recovery a cada 2s do poll.
    if time.monotonic() - _last_stall_recovery_at < 120.0:
        return None

    from .ingest_maintenance import run_ingest_self_healing
    from .ingest_planner import plan_ingest_queue

    logger.warning(
        "ingest PARADA detectada (pending=%s, sem progresso há %.0fs) — autocura agressiva",
        _last_pending,
        seconds_since_progress(),
    )
    heal = run_ingest_self_healing(mode="stall")
    try:
        plan = plan_ingest_queue()
    except Exception:
        logger.exception("ingest stall recovery: planner falhou")
        plan = {}

    _stall_recoveries += 1
    _last_stall_recovery_at = time.monotonic()
    _last_progress_at = time.monotonic()

    out = {
        "ok": True,
        "stall_recovery": True,
        "heal": heal,
        "plan": {
            "catalog_pages_enqueued": plan.get("catalog_pages_enqueued"),
            "contract_items_enqueued": plan.get("contract_items_enqueued"),
            "catalog_scopes_paused": plan.get("catalog_scopes_paused"),
        },
        "stall_recoveries_total": _stall_recoveries,
    }
    logger.warning("ingest stall recovery concluída: %s", out)
    return out


def ingest_runtime_status() -> Dict[str, Any]:
    stalled = is_ingest_stalled()
    return {
        "worker_enabled": bool(config.PNCP_INGEST_WORKER_ENABLED),
        "queue_enabled": bool(config.PNCP_INGEST_QUEUE_ENABLED),
        "worker_started": _worker_started_at > 0,
        "stalled": stalled,
        "seconds_since_progress": round(seconds_since_progress(), 1),
        "seconds_since_batch": round(max(0.0, time.monotonic() - _last_batch_at), 1)
        if _last_batch_at
        else None,
        "pending_last": _last_pending,
        "stall_recoveries": _stall_recoveries,
        "last_batch": {
            "catalog_ok": _last_batch_summary.get("catalog_ok"),
            "items_ok": _last_batch_summary.get("items_ok"),
            "errors": _last_batch_summary.get("errors"),
        },
    }
