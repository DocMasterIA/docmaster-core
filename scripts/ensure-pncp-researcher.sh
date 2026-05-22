#!/usr/bin/env bash
# Sobe/mantém o PNCP Researcher 24/7 (stack isolada docmaster-pncp).
# Não usa «down -v». Por padrão «up -d --no-recreate» para não matar backfill em andamento.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY="${DOCMASTER_DEPLOY_DIR:-$SCRIPT_DIR/..}"
DEPLOY="$(cd "$DEPLOY" && pwd)"
COMPOSE_FILE="${DOCMASTER_PNCP_COMPOSE_FILE:-$DEPLOY/docker-compose.pncp.yml}"
OVERRIDE_FILE="${DEPLOY}/docker-compose.pncp.override.yml"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "ERRO: $COMPOSE_FILE não encontrado"
  exit 1
fi

if [[ -d "$DEPLOY/docmaster-core/pncp_researcher_service" ]]; then
  export PNCP_BUILD_CONTEXT=docmaster-core
elif [[ -d "$DEPLOY/pncp_researcher_service" ]]; then
  export PNCP_BUILD_CONTEXT=.
else
  echo "ERRO: pasta pncp_researcher_service não encontrada em $DEPLOY"
  exit 1
fi

cd "$DEPLOY"
PNCP_HEALTH_URL="${PNCP_HEALTH_URL:-http://127.0.0.1:8012/api/pncp-research/health}"
PNCP_STATS_URL="${PNCP_STATS_URL:-http://127.0.0.1:8012/api/pncp-research/local-index/stats}"

COMPOSE_ARGS=(-f "$COMPOSE_FILE")
if [[ -f "$OVERRIDE_FILE" ]]; then
  COMPOSE_ARGS+=(-f "$OVERRIDE_FILE")
  echo "==> Usando override: $OVERRIDE_FILE (volume external)"
else
  echo "==> Sem override — volume padrão do projeto docmaster-pncp"
  echo "    Se o índice sumiu após down/up: ./scripts/find-pncp-db-volumes.sh"
  echo "    PNCP_DATA_VOLUME=<volume_grande> ./scripts/attach-pncp-volume.sh"
fi

if ! docker network inspect docmaster_net >/dev/null 2>&1; then
  echo "==> A criar rede docmaster_net..."
  docker network create docmaster_net
fi

UP_FLAGS=(-d)
if [[ "${PNCP_FORCE_RECREATE:-0}" == "1" ]]; then
  UP_FLAGS+=(--force-recreate)
  echo "==> PNCP_FORCE_RECREATE=1 — a recriar contentor"
else
  UP_FLAGS+=(--no-recreate)
fi
if [[ "${PNCP_BUILD:-0}" == "1" ]]; then
  UP_FLAGS+=(--build)
fi

echo "==> PNCP Researcher 24/7 (projeto docmaster-pncp)"
docker compose "${COMPOSE_ARGS[@]}" up "${UP_FLAGS[@]}"

echo ""
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E '^(NAMES|pncp_researcher)' || true

echo ""
echo "==> /health"
ok=0
for _ in $(seq 1 15); do
  if curl -sf --max-time 5 "$PNCP_HEALTH_URL" >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 3
done

if [[ "$ok" -eq 1 ]]; then
  curl -sf "$PNCP_HEALTH_URL" | python3 -m json.tool 2>/dev/null || curl -sf "$PNCP_HEALTH_URL"
  echo ""
  if curl -sf --max-time 10 "$PNCP_STATS_URL" >/dev/null 2>&1; then
    echo "==> /local-index/stats (resumo)"
    curl -sf "$PNCP_STATS_URL" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('  db_path:', d.get('db_path'))
print('  total_contratos:', d.get('total_contratos'))
print('  total_itens:', d.get('total_itens'))
" 2>/dev/null || true
  fi
  echo ""
  echo "OK  PNCP ativo em $PNCP_HEALTH_URL"
else
  echo "OFF $PNCP_HEALTH_URL"
  echo "Logs: docker compose ${COMPOSE_ARGS[*]} logs --tail 80"
  exit 1
fi

echo ""
echo "24/7: restart=always no compose. Após reboot do host: rode este script de novo."
echo "NÃO use: docker compose -f docker-compose.pncp.yml down -v"
echo "Backend/outros: docker compose up -d --no-recreate backend  (não recria o PNCP)"
echo "Backfill (job longo, não bloqueie 24h na API): use max_paginas e UF; ver docs/deploy/PNCP-RESEARCHER-24-7.md"
