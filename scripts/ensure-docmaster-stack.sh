#!/usr/bin/env bash
# Sobe a stack DocMaster após reboot ou queda: app + túnel Cloudflare + PNCP + observabilidade.
#
# Uso:
#   ./scripts/ensure-docmaster-stack.sh
#   DOCMASTER_DEPLOY_DIR=/home/adryan ./scripts/ensure-docmaster-stack.sh
#
# Boot automático (Linux):
#   sudo ./scripts/install-docmaster-boot-service.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY="${DOCMASTER_DEPLOY_DIR:-$SCRIPT_DIR/..}"
DEPLOY="$(cd "$DEPLOY" && pwd)"
COMPOSE_FILE="${DOCMASTER_COMPOSE_FILE:-$DEPLOY/docker-compose.yml}"

log() {
  echo "$(date -Is) $*"
}

wait_for_docker() {
  local i
  for i in $(seq 1 60); do
    if docker info >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  log "ERRO: Docker não respondeu após 120s"
  return 1
}

load_env_file() {
  local f
  for f in \
    "${DOCMASTER_ENV_FILE:-}" \
    "$DEPLOY/.env" \
    "$DEPLOY/docmaster-core/.env"
  do
    [[ -n "$f" && -f "$f" ]] || continue
    log "Carregando env: $f"
    set -a
    # shellcheck disable=SC1090
    source "$f"
    set +a
    return 0
  done
}

ensure_network() {
  if ! docker network inspect docmaster_net >/dev/null 2>&1; then
    log "A criar rede docmaster_net..."
    docker network create docmaster_net
  fi
}

main_compose_up() {
  if [[ ! -f "$COMPOSE_FILE" ]]; then
    log "ERRO: compose não encontrado: $COMPOSE_FILE"
    exit 1
  fi

  cd "$DEPLOY"
  local up_flags=(-d --no-recreate)
  if [[ "${DOCMASTER_FORCE_RECREATE:-0}" == "1" ]]; then
    up_flags=(-d --force-recreate)
    log "DOCMASTER_FORCE_RECREATE=1 — a recriar contentores"
  fi
  if [[ "${DOCMASTER_BUILD:-0}" == "1" ]]; then
    up_flags+=(--build)
  fi

  log "Stack principal em $DEPLOY"
  docker compose -f "$COMPOSE_FILE" up "${up_flags[@]}"
}

wait_http() {
  local url="$1"
  local label="$2"
  local tries="${3:-20}"
  local i
  for i in $(seq 1 "$tries"); do
    if curl -sf --max-time 5 "$url" >/dev/null 2>&1; then
      log "OK  $label"
      return 0
    fi
    sleep 3
  done
  log "OFF $label"
  return 1
}

report_status() {
  echo ""
  docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E \
    '^(NAMES|backend|frontend-vue|cloudflared|ollama|llm_api|rag_service|pncp_researcher|grafana|prometheus|node_exporter)' \
    || true
}

log "==> DocMaster stack ensure (DEPLOY=$DEPLOY)"
wait_for_docker
load_env_file
ensure_network
main_compose_up

if [[ -x "$SCRIPT_DIR/ensure-pncp-researcher.sh" ]]; then
  log "==> PNCP Researcher (stack isolada)"
  DOCMASTER_DEPLOY_DIR="$DEPLOY" "$SCRIPT_DIR/ensure-pncp-researcher.sh" || {
    log "AVISO: PNCP ensure falhou — stack principal pode estar OK"
  }
else
  log "AVISO: ensure-pncp-researcher.sh não encontrado — a ignorar PNCP"
fi

if [[ "${DOCMASTER_START_PNCP_INGEST:-0}" == "1" ]]; then
  if [[ -x "$SCRIPT_DIR/ensure-pncp-ingest-loop.sh" ]]; then
    log "==> PNCP ingest loop"
    DOCMASTER_DEPLOY_DIR="$DEPLOY" "$SCRIPT_DIR/ensure-pncp-ingest-loop.sh" || true
  fi
fi

echo ""
log "==> Health checks"
wait_http "http://127.0.0.1:8001/metrics" "backend /metrics" 25 || true
wait_http "http://127.0.0.1:8012/api/pncp-research/health" "PNCP /health" 15 || true
wait_http "http://127.0.0.1:3000/api/health" "Grafana" 15 || true

if docker ps --format '{{.Names}}' | grep -qx 'cloudflared-tunnel'; then
  log "OK  cloudflared-tunnel (contentor ativo)"
else
  log "OFF cloudflared-tunnel — verifique CLOUDFLARE_TUNNEL_TOKEN no .env"
fi

report_status
echo ""
log "Concluído. Boot automático: sudo ./scripts/install-docmaster-boot-service.sh"
log "Doc: docs/deploy/BOOT-AUTOMATICO.md"
