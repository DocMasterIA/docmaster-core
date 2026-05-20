#!/usr/bin/env bash
# Sobe o PNCP Researcher na stack isolada (não é afetado por «docker compose up -d backend»).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY="${DOCMASTER_DEPLOY_DIR:-$SCRIPT_DIR/..}"
DEPLOY="$(cd "$DEPLOY" && pwd)"
COMPOSE_FILE="${DOCMASTER_PNCP_COMPOSE_FILE:-$DEPLOY/docker-compose.pncp.yml}"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "ERRO: $COMPOSE_FILE não encontrado"
  echo "Copie docker-compose.pncp.yml e scripts/ para DEPLOY ou defina DOCMASTER_PNCP_COMPOSE_FILE."
  exit 1
fi

if [[ -d "$DEPLOY/docmaster-core/pncp_researcher_service" ]]; then
  export PNCP_BUILD_CONTEXT=docmaster-core
elif [[ -d "$DEPLOY/pncp_researcher_service" ]]; then
  export PNCP_BUILD_CONTEXT=.
else
  echo "ERRO: pasta pncp_researcher_service não encontrada em $DEPLOY (nem em docmaster-core/)"
  exit 1
fi

cd "$DEPLOY"
PNCP_HEALTH_URL="${PNCP_HEALTH_URL:-http://127.0.0.1:8012/api/pncp-research/health}"

if ! docker network inspect docmaster_net >/dev/null 2>&1; then
  echo "==> A criar rede docmaster_net..."
  docker network create docmaster_net
fi

echo "==> PNCP Researcher (projeto docmaster-pncp)"
echo "    compose: $COMPOSE_FILE"
echo "    build context: $PNCP_BUILD_CONTEXT"
docker compose -f "$COMPOSE_FILE" up -d

echo ""
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E '^(NAMES|pncp_researcher)' || true

echo ""
echo "==> A aguardar /health (até ~45s na 1ª subida)..."
ok=0
for _ in $(seq 1 15); do
  if curl -sf --max-time 5 "$PNCP_HEALTH_URL" >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 3
done

if [[ "$ok" -eq 1 ]]; then
  curl -sf "$PNCP_HEALTH_URL" | head -c 200
  echo ""
  echo "OK  $PNCP_HEALTH_URL"
else
  echo "OFF $PNCP_HEALTH_URL"
  echo "Logs: docker compose -f $COMPOSE_FILE logs --tail 50"
fi

echo ""
echo "Backfill: POST http://127.0.0.1:8012/local-index/backfill"
echo "Outros serviços: docker compose up -d --no-recreate backend  (não recria o PNCP)"
