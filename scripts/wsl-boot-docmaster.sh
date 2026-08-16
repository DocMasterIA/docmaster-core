#!/usr/bin/env bash
# Acorda a stack DocMaster quando o Windows inicia a sessão WSL (Task Scheduler).
# Usa ensure-docmaster-stack.sh (docker compose como docmaster) — systemctl start
# do unit de sistema exige polkit/sudo e falha na tarefa agendada.
set -euo pipefail

DEPLOY="${DOCMASTER_DEPLOY_DIR:-/home/docmaster/docmaster-core}"
LOG="${DOCMASTER_WSL_BOOT_LOG:-$HOME/wsl-boot.log}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Compat: boot antigo apontava para /home/docmaster (pai do repo)
if [[ ! -f "$DEPLOY/docker-compose.yml" && -f /home/docmaster/docker-compose.yml ]]; then
  DEPLOY=/home/docmaster
fi
if [[ ! -f "$DEPLOY/docker-compose.yml" && -f /home/docmaster/docmaster-core/docker-compose.yml ]]; then
  DEPLOY=/home/docmaster/docmaster-core
fi

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

ENSURE="$SCRIPT_DIR/ensure-docmaster-stack.sh"
if [[ ! -x "$ENSURE" ]]; then
  ENSURE="$DEPLOY/scripts/ensure-docmaster-stack.sh"
fi
if [[ ! -x "$ENSURE" ]]; then
  log "ERRO: ensure-docmaster-stack.sh não encontrado"
  exit 1
fi

log "ensure-docmaster-stack.sh (sem systemctl — evita «Interactive authentication required»)"
export DOCMASTER_DEPLOY_DIR="$DEPLOY"
"$ENSURE" || exit 1

for name in cloudflared-tunnel backend frontend-vue; do
  if docker ps --format '{{.Names}}' | grep -qx "$name"; then
    log "OK  $name"
  else
    log "ERRO $name não está Up"
    exit 1
  fi
done

if docker ps --format '{{.Names}}' | grep -qx 'pncp_researcher_service'; then
  if curl -sf --max-time 5 http://127.0.0.1:8012/api/pncp-research/health >/dev/null 2>&1; then
    log "OK  pncp_researcher_service (/health)"
  else
    log "AVISO pncp_researcher_service Up mas /health falhou — logs: docker logs pncp_researcher_service --tail 80"
  fi
else
  log "AVISO pncp_researcher_service não está Up — rode: DOCMASTER_DEPLOY_DIR=$DEPLOY $SCRIPT_DIR/ensure-pncp-researcher.sh"
fi

log "Concluído"
