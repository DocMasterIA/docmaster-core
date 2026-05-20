#!/usr/bin/env bash
# Sobe (ou recupera) Grafana + Prometheus + node_exporter após reboot ou queda.
# Uso: cd DEPLOY && ./scripts/ensure-observability.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY="${DOCMASTER_DEPLOY_DIR:-$SCRIPT_DIR/..}"
DEPLOY="$(cd "$DEPLOY" && pwd)"
COMPOSE_FILE="${DOCMASTER_COMPOSE_FILE:-$DEPLOY/docker-compose.yml}"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "ERRO: docker-compose não encontrado em $DEPLOY"
  exit 1
fi

cd "$DEPLOY"
COMPOSE=(docker compose -f "$COMPOSE_FILE")

echo "==> Observabilidade em $DEPLOY"
"${COMPOSE[@]}" up -d node_exporter prometheus grafana

echo ""
echo "==> Estado"
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E '^(NAMES|node_exporter|prometheus|grafana)' || true

echo ""
for url in "http://127.0.0.1:3000/api/health" "http://127.0.0.1:9090/-/ready" "http://127.0.0.1:9100/metrics"; do
  if curl -sf --max-time 5 "$url" >/dev/null 2>&1; then
    echo "OK  $url"
  else
    echo "OFF $url"
  fi
done

echo ""
echo "Grafana: http://127.0.0.1:3000/d/docmaster-backend"
