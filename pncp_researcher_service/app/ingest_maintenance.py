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


def purge_redundant_dead_tasks() -> int:
    """
    Remove tarefas dead redundantes:
    - já existe pending/processing com a mesma chave lógica;
    - outra dead mais antiga (menor id) com a mesma chave.
    """
    with _queue_conn() as c:
        cur = c.execute(
            """
            DELETE FROM pncp_ingest_queue
            WHERE status = 'dead'
            AND (
                (task_type = 'catalog_page' AND (
                    EXISTS (
                        SELECT 1 FROM pncp_ingest_queue q2
                        WHERE q2.task_type = 'catalog_page'
                          AND q2.status IN ('pending', 'processing')
                          AND q2.uf = pncp_ingest_queue.uf
                          AND q2.modalidade = pncp_ingest_queue.modalidade
                          AND q2.pagina = pncp_ingest_queue.pagina
                          AND q2.data_inicial = pncp_ingest_queue.data_inicial
                          AND q2.data_final = pncp_ingest_queue.data_final
                          AND q2.id != pncp_ingest_queue.id
                    )
                    OR EXISTS (
                        SELECT 1 FROM pncp_ingest_queue d2
                        WHERE d2.status = 'dead'
                          AND d2.task_type = 'catalog_page'
                          AND d2.uf = pncp_ingest_queue.uf
                          AND d2.modalidade = pncp_ingest_queue.modalidade
                          AND d2.pagina = pncp_ingest_queue.pagina
                          AND d2.data_inicial = pncp_ingest_queue.data_inicial
                          AND d2.data_final = pncp_ingest_queue.data_final
                          AND d2.id < pncp_ingest_queue.id
                    )
                ))
                OR (task_type = 'contract_items' AND (
                    EXISTS (
                        SELECT 1 FROM pncp_ingest_queue q2
                        WHERE q2.task_type = 'contract_items'
                          AND q2.status IN ('pending', 'processing')
                          AND q2.numero_pncp = pncp_ingest_queue.numero_pncp
                          AND q2.id != pncp_ingest_queue.id
                    )
                    OR EXISTS (
                        SELECT 1 FROM pncp_ingest_queue d2
                        WHERE d2.status = 'dead'
                          AND d2.task_type = 'contract_items'
                          AND d2.numero_pncp = pncp_ingest_queue.numero_pncp
                          AND d2.id < pncp_ingest_queue.id
                    )
                ))
            )
            """
        )
        n = int(cur.rowcount or 0)
        c.commit()
    if n:
        logger.info("ingest purge dead redundantes removidas=%s", n)
    return n


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
                  AND (last_error IS NULL OR (
                    last_error NOT LIKE 'manual:%'
                    AND last_error NOT LIKE 'skip:%'
                    AND last_error NOT LIKE 'purge:%'
                  ))
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


def purge_redundant_pending_item_tasks(*, limit: int = 5000) -> int:
    """Remove da fila pending contract_items que já não precisam refresh (itens recentes)."""
    from .local_index import contract_needs_items_refresh, contract_has_items_needing_resultados

    lim = max(1, int(limit))
    with _queue_conn() as c:
        rows = c.execute(
            """
            SELECT id, numero_pncp FROM pncp_ingest_queue
            WHERE task_type = 'contract_items' AND status = 'pending'
            ORDER BY priority DESC, id ASC
            LIMIT ?
            """,
            (lim,),
        ).fetchall()
    ids = []
    for r in rows:
        numero = str(r["numero_pncp"] or "")
        if contract_needs_items_refresh(numero):
            continue
        if contract_has_items_needing_resultados(numero):
            continue
        ids.append(int(r["id"]))
    if not ids:
        return 0
    now = _utc_now_iso()
    with _queue_conn() as c:
        placeholders = ",".join("?" for _ in ids)
        cur = c.execute(
            f"""
            UPDATE pncp_ingest_queue
            SET status = 'done', updated_at = ?, last_error = 'purge: refresh desnecessário'
            WHERE id IN ({placeholders}) AND status = 'pending'
            """,
            (now, *ids),
        )
        n = int(cur.rowcount or 0)
        c.commit()
    if n:
        logger.info("ingest purge pending itens redundantes=%s", n)
    return n


def reconcile_gap_contracts_after_done_items() -> int:
    """
    Contratos ainda no gap SQLite com tarefa contract_items já concluída (done).
    Marca como verificados — corrige bases onde items_ok>0 mas item_rows=0 antes do fix.
    """
    from .local_index import mark_contract_items_verified

    with _queue_conn() as c:
        rows = c.execute(
            """
            SELECT c.numero_pncp
            FROM pncp_contratos c
            WHERE NOT EXISTS (
                SELECT 1 FROM pncp_itens i WHERE i.numero_pncp = c.numero_pncp LIMIT 1
            )
            AND (c.itens_verificados_at IS NULL OR TRIM(c.itens_verificados_at) = '')
            AND EXISTS (
                SELECT 1 FROM pncp_ingest_queue q
                WHERE q.task_type = 'contract_items'
                  AND q.numero_pncp = c.numero_pncp
                  AND q.status = 'done'
            )
            """
        ).fetchall()
    n = 0
    for r in rows:
        mark_contract_items_verified(str(r["numero_pncp"]))
        n += 1
    if n:
        logger.info("ingest reconcile gap: contratos marcados verificados=%s", n)
    return n


def run_ingest_self_healing(*, mode: str = "periodic") -> Dict[str, Any]:
    """
    mode=startup: requeue total + scopes + dead (batch maior).
    mode=periodic: só processing stale + scopes expirados + dead antigas.
    """
    if not PNCP_INGEST_SELF_HEAL_ENABLED:
        return {"ok": True, "skipped": True}

    ensure_local_index()
    mode_s = str(mode or "").strip().lower()
    startup = mode_s == "startup"
    stall = mode_s == "stall"
    stale_sec = int(PNCP_INGEST_PROCESSING_STALE_SECONDS)
    dead_batch = int(PNCP_INGEST_DEAD_REVIVE_BATCH)
    dead_min_age = int(PNCP_INGEST_DEAD_REVIVE_MIN_AGE_SECONDS)
    if startup or stall:
        dead_batch = max(dead_batch, 2000)
        dead_min_age = min(dead_min_age, 120 if startup else 60)

    requeue_all = startup or stall
    requeued = requeue_processing_tasks(stale_only=not requeue_all, stale_seconds=stale_sec)
    scopes = resume_expired_ingest_scopes()
    purged = purge_redundant_dead_tasks()
    revived = revive_dead_tasks(limit=dead_batch, min_dead_age_seconds=dead_min_age)
    gap_reconciled = 0
    items_purged = 0
    if startup or stall:
        gap_reconciled = reconcile_gap_contracts_after_done_items()
        items_purged = purge_redundant_pending_item_tasks()

    out = {
        "ok": True,
        "mode": mode,
        "requeued_processing": requeued,
        "scopes_resumed": scopes,
        "dead_purged": purged,
        "dead_revived": revived,
        "gap_reconciled": gap_reconciled,
        "items_purged": items_purged,
    }
    if requeued or scopes or purged or revived or gap_reconciled or items_purged:
        logger.info("ingest self-heal (%s): %s", mode, out)
    return out
