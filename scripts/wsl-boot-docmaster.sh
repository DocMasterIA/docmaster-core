#!/usr/bin/env bash
# Acorda a stack DocMaster quando o Windows inicia a sessão WSL (Task Scheduler).
# Não substitui docmaster-stack.service — chama-o depois do Docker estar pronto.
set -euo pipefail

DEPLOY="${DOCMASTER_DEPLOY_DIR:-/home/docmaster}"
LOG="${DOCMASTER_WSL_BOOT_LOG:-$DEPLOY/wsl-boot.log}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$(dirname "$LOG")"
exec >>"$LOG" 2>&1

log() { echo "$(date -Is) $*"; }

log "==> wsl-boot-docmaster (DEPLOY=$DEPLOY)"

for i in $(seq 1 120); do
  if docker info >/dev/null 2>&1; then
    log "Docker OK (${i} tentativas)"
    break
  fi
  sleep 2
done

if ! docker info >/dev/null 2>&1; then
  log "ERRO: Docker não respondeu em ~240s — ative Docker Desktop «Start when you sign in»"
  exit 1
fi

if command -v systemctl >/dev/null 2>&1 && systemctl is-system-running >/dev/null 2>&1; then
  log "systemctl start docmaster-stack.service"
  systemctl start docmaster-stack.service || true
else
  log "systemd indisponível — ensure-docmaster-stack.sh"
  export DOCMASTER_DEPLOY_DIR="$DEPLOY"
  "$SCRIPT_DIR/ensure-docmaster-stack.sh" || exit 1
fi

if docker ps --format '{{.Names}}' | grep -qx cloudflared-tunnel; then
  log "OK cloudflared-tunnel"
else
  log "AVISO cloudflared-tunnel não está Up"
fi

log "Concluído"
