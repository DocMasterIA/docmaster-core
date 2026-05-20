#!/usr/bin/env bash
# Sobe o PNCP Researcher na stack isolada (não é afetado por «docker compose up -d backend»).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY="${DOCMASTER_DEPLOY_DIR:-$SCRIPT_DIR/..}"
DEPLOY="$(cd "$DEPLOY" && pwd)"
COMPOSE_FILE="${DOCMASTER_PNCP_COMPOSE_FILE:-$DEPLOY/docker-compose.pncp.yml}"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "ERRO: $COMPOSE_FILE não encontrado"
  exit 1
fi

cd "$DEPLOY"
echo "==> PNCP Researcher ($COMPOSE_FILE)"
docker compose -f "$COMPOSE_FILE" up -d

echo ""
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E '^(NAMES|pncp_researcher)' || true

if curl -sf --max-time 5 http://127.0.0.1:8012/health >/dev/null; then
  echo "OK  http://127.0.0.1:8012/health"
else
  echo "OFF http://127.0.0.1:8012/health (aguarde healthcheck ou: docker compose -f docker-compose.pncp.yml logs --tail 40)"
fi

echo ""
echo "Backfill / índice: POST http://127.0.0.1:8012/local-index/backfill (não pare este contentor com up -d noutros serviços)."
