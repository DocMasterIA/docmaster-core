"""Autocura da fila e dos scopes de ingestão — sem intervenção manual."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from .config import (
    PNCP_INGEST_DEAD_REVIVE_BATCH,
    PNCP_INGEST_DEAD_REVIVE_MIN_AGE_SECONDS,
    PNCP_INGEST_PROCESSING_STALE_SECONDS,
    PNCP_INGEST_SELF_HEAL_ENABLED,
)
from .ingest_queue import _queue_conn, _utc_now_iso
from .local_index import ensure_local_index, resume_expired_ingest_scopes

logger = logging.getLogger(__name__)


def requeue_processing_tasks(*, stale_only: bool, stale_seconds: int) -> int:
    """Devolve tarefas em processing para pending (crash/restart ou presas)."""
    now = _utc_now_iso()
    with _queue_conn() as c:
        if stale_only:
            cutoff = (
                datetime.utcnow() - timedelta(seconds=max(60, int(stale_seconds)))
            ).isoformat(timespec="seconds") + "Z"
            cur = c.execute(
                """
                UPDATE pncp_ingest_queue
                SET status = 'pending', updated_at = ?
                WHERE status = 'processing' AND updated_at <= ?
                """,
                (now, cutoff),
            )
        else:
            cur = c.execute(
                """
                UPDATE pncp_ingest_queue
                SET status = 'pending', updated_at = ?
                WHERE status = 'processing'
                """,
                (now,),
            )
        n = int(cur.rowcount or 0)
        c.commit()
    return n


def revive_dead_tasks(*, limit: int, min_dead_age_seconds: int) -> int:
    """Reabre tarefas dead após cooldown — nova rodada de tentativas."""
    lim = max(1, int(limit))
    min_age = max(300, int(min_dead_age_seconds))
    now_dt = datetime.utcnow()
    now = now_dt.isoformat(timespec="seconds") + "Z"
    cutoff = (now_dt - timedelta(seconds=min_age)).isoformat(timespec="seconds") + "Z"
    with _queue_conn() as c:
        ids = [
            int(r[0])
            for r in c.execute(
                """
                SELECT id FROM pncp_ingest_queue
                WHERE status = 'dead' AND updated_at <= ?
                ORDER BY priority ASC, id ASC
                LIMIT ?
                """,
                (cutoff, lim),
            ).fetchall()
        ]
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        cur = c.execute(
            f"""
            UPDATE pncp_ingest_queue
            SET status = 'pending', attempts = 0, last_error = NULL,
                available_at = ?, updated_at = ?
            WHERE id IN ({placeholders}) AND status = 'dead'
            """,
            (now, now, *ids),
        )
        n = int(cur.rowcount or 0)
        c.commit()
    return n


def run_ingest_self_healing(*, mode: str = "periodic") -> Dict[str, Any]:
    """
    mode=startup: requeue total + scopes + dead (batch maior).
    mode=periodic: só processing stale + scopes expirados + dead antigas.
    """
    if not PNCP_INGEST_SELF_HEAL_ENABLED:
        return {"ok": True, "skipped": True}

    ensure_local_index()
    startup = str(mode or "").strip().lower() == "startup"
    stale_sec = int(PNCP_INGEST_PROCESSING_STALE_SECONDS)
    dead_batch = int(PNCP_INGEST_DEAD_REVIVE_BATCH)
    dead_min_age = int(PNCP_INGEST_DEAD_REVIVE_MIN_AGE_SECONDS)
    if startup:
        dead_batch = max(dead_batch, 2000)
        dead_min_age = min(dead_min_age, 120)

    requeued = requeue_processing_tasks(stale_only=not startup, stale_seconds=stale_sec)
    scopes = resume_expired_ingest_scopes()
    revived = revive_dead_tasks(limit=dead_batch, min_dead_age_seconds=dead_min_age)

    out = {
        "ok": True,
        "mode": mode,
        "requeued_processing": requeued,
        "scopes_resumed": scopes,
        "dead_revived": revived,
    }
    if requeued or scopes or revived:
        logger.info("ingest self-heal (%s): %s", mode, out)
    return out
