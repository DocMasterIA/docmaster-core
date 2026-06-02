# shellcheck shell=bash
# Monta COMPOSE_ARGS para docker compose PNCP. Fonte: ensure-pncp-researcher.sh, attach-pncp-volume.sh
pncp_setup_compose_args() {
  local deploy="$1"
  COMPOSE_FILE="${DOCMASTER_PNCP_COMPOSE_FILE:-$deploy/docker-compose.pncp.yml}"
  OVERRIDE_FILE="${deploy}/docker-compose.pncp.override.yml"
  NOPORTS_FILE="${deploy}/docker-compose.pncp.noports.yml"
  PNCP_USE_DOCKER_HEALTH=0

  COMPOSE_ARGS=(-f "$COMPOSE_FILE")
  if [[ -f "$OVERRIDE_FILE" ]]; then
    COMPOSE_ARGS+=(-f "$OVERRIDE_FILE")
  fi
  if [[ "${PNCP_NO_HOST_PORT:-0}" == "1" ]] || [[ -f "$NOPORTS_FILE" ]]; then
    if [[ ! -f "$NOPORTS_FILE" ]]; then
      cat >"$NOPORTS_FILE" <<'EOF'
# Criado automaticamente (PNCP_NO_HOST_PORT ou falha na porta 8012 no host).
services:
  pncp_researcher_service:
    ports: !reset []
EOF
      echo "==> Criado $NOPORTS_FILE (sem porta 8012 no host)"
    fi
    COMPOSE_ARGS+=(-f "$NOPORTS_FILE")
    PNCP_USE_DOCKER_HEALTH=1
    echo "==> Sem porta 8012 no host (rede Docker docmaster_net)"
  fi
}

pncp_health_ok() {
  if [[ "${PNCP_USE_DOCKER_HEALTH:-0}" == "1" ]]; then
    docker exec pncp_researcher_service python -c \
      "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/health', timeout=5)" \
      >/dev/null 2>&1
  else
    curl -sf --max-time 5 "${PNCP_HEALTH_URL:-http://127.0.0.1:8012/api/pncp-research/health}" >/dev/null 2>&1
  fi
}

pncp_print_health() {
  if [[ "${PNCP_USE_DOCKER_HEALTH:-0}" == "1" ]]; then
    docker exec pncp_researcher_service python -c \
      "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/health', timeout=10).read().decode())" \
      2>/dev/null | python3 -m json.tool 2>/dev/null || true
  else
    curl -sf "${PNCP_HEALTH_URL:-http://127.0.0.1:8012/api/pncp-research/health}" \
      | python3 -m json.tool 2>/dev/null || \
      curl -sf "${PNCP_HEALTH_URL:-http://127.0.0.1:8012/api/pncp-research/health}"
  fi
}

pncp_print_stats_summary() {
  local stats_json
  if [[ "${PNCP_USE_DOCKER_HEALTH:-0}" == "1" ]]; then
    stats_json="$(docker exec pncp_researcher_service python -c \
      "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/local-index/stats', timeout=120).read().decode())" \
      2>/dev/null || true)"
  else
    stats_json="$(curl -sf --max-time 10 "${PNCP_STATS_URL:-http://127.0.0.1:8012/api/pncp-research/local-index/stats}" 2>/dev/null || true)"
  fi
  [[ -z "$stats_json" ]] && return 1
  echo "$stats_json" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('  db_path:', d.get('db_path'))
print('  total_contratos:', d.get('total_contratos'))
print('  total_itens:', d.get('total_itens'))
" 2>/dev/null
}
