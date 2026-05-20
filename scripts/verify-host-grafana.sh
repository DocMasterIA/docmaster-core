#!/usr/bin/env bash
# Prometheus tem métricas node_*? Grafana alcança o mesmo Prometheus?
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROM="${PROMETHEUS_URL:-http://127.0.0.1:9090}"

echo "=== verify-host-grafana ==="
echo "Prometheus: $PROM"
echo ""

if ! curl -sf "$PROM/-/ready" >/dev/null; then
  echo "ERRO: Prometheus não responde em $PROM"
  exit 1
fi

echo "1) Job node no Prometheus:"
curl -sfG "$PROM/api/v1/query" --data-urlencode 'query=up{job="node"}' | python3 -c "
import json,sys
d=json.load(sys.stdin)
r=d.get('data',{}).get('result') or []
if not r:
    print('   FALHOU — sem série up{job=\"node\"}. Rode ./scripts/fix-prometheus-node.sh')
    sys.exit(1)
v=r[0]['value'][1]
print(f'   up{{job=\"node\"}} = {v}', 'OK' if v=='1' else 'DOWN (scrape falhou)')
"

echo ""
echo "2) Métricas host (amostra):"
for q in \
  'node_memory_MemTotal_bytes{job="node"}' \
  'node_load1{job="node"}' \
  '100 * (1 - (node_memory_MemAvailable_bytes{job="node"} / node_memory_MemTotal_bytes{job="node"}))'
do
  n=$(curl -sfG "$PROM/api/v1/query" --data-urlencode "query=$q" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(len(d.get('data',{}).get('result') or []))
")
  if [[ "$n" -ge 1 ]]; then
    echo "   OK  $q"
  else
    echo "   —   $q (sem dados)"
  fi
done

echo ""
echo "3) Grafana → Prometheus:"
if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx grafana; then
  _g_ok=0
  for url in http://host.docker.internal:9090/-/ready http://prometheus:9090/-/ready; do
    if docker exec grafana wget -qO- -T 3 "$url" 2>/dev/null | grep -q Ready; then
      echo "   OK — grafana alcança $url"
      _g_ok=1
      break
    fi
  done
  if [[ "$_g_ok" -ne 1 ]]; then
    echo "   FALHOU — recrie Grafana só de docmaster-core:"
    echo "   docker rm -f grafana && docker compose -f ~/docmaster-core/docker-compose.yml up -d --no-deps grafana"
  fi
else
  echo "   (contentor grafana não encontrado)"
fi

echo ""
echo "4) Dashboard provisionado:"
DASH="$REPO_ROOT/config/grafana/provisioning/dashboards/json/docmaster-backend.json"
if grep -q 'node_memory_MemAvailable_bytes' "$DASH" && grep -q '"range": true' "$DASH"; then
  echo "   OK — JSON com queries node + Stats em modo range"
else
  echo "   AVISO — python3 scripts/build-grafana-dashboard.py && ./scripts/grafana-reset-dashboard.sh"
fi

echo ""
echo "Se (1) e (2) OK mas Grafana vazio: intervalo «Last 6 hours», datasource Prometheus,"
echo "e ./scripts/grafana-reset-dashboard.sh após build-grafana-dashboard.py"
