#!/usr/bin/env bash
# Garante uma única instância do loop de ingestão PNCP (idempotente para cron/systemd).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOOP_SCRIPT="$SCRIPT_DIR/run-pncp-index-ingest-loop.sh"
LOCK_FILE="${PNCP_INGEST_LOCK_FILE:-${HOME}/.pncp-index-ingest.lock}"
LOG_FILE="${PNCP_INGEST_LOG:-${HOME}/pncp-ingest.log}"
PID_FILE="${PNCP_INGEST_PID_FILE:-${HOME}/.pncp-index-ingest.pid}"

log() {
  echo "$(date -Is) $*"
}

if [[ ! -x "$LOOP_SCRIPT" ]]; then
  log "ERRO: $LOOP_SCRIPT não encontrado ou não executável"
  exit 1
fi

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    log "Ingestão PNCP já em execução (pid=$old_pid)"
    exit 0
  fi
fi

exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
  log "Ingestão PNCP já em execução (lock: $LOCK_FILE)"
  exit 0
fi

for _ in $(seq 1 30); do
  if curl -sf --max-time 5 "http://127.0.0.1:8012/api/pncp-research/health" >/dev/null 2>&1; then
    break
  fi
  sleep 4
done

log "A iniciar loop de ingestão PNCP (log: $LOG_FILE)"
nohup env PNCP_INGEST_LOG="$LOG_FILE" "$LOOP_SCRIPT" >>"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"
log "OK  pid=$(cat "$PID_FILE")"
