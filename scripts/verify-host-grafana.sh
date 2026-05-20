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
echo "3) Grafana → Prometheus (se grafana no compose):"
if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx grafana; then
  if docker exec grafana wget -qO- -T 3 http://prometheus:9090/-/ready 2>/dev/null | grep -q Ready; then
    echo "   OK — grafana alcança http://prometheus:9090"
  else
    echo "   FALHOU — grafana não alcança prometheus:9090 (rede Docker)"
  fi
else
  echo "   (contentor grafana não encontrado — ignore se Grafana é remoto)"
fi

echo ""
echo "4) Dashboard provisionado:"
DASH="$REPO_ROOT/config/grafana/provisioning/dashboards/json/docmaster-backend.json"
if grep -q 'period": true' "$DASH" && grep -q 'node_memory_MemAvailable_bytes' "$DASH"; then
  echo "   OK — JSON com queries node (range nos Stats)"
else
  echo "   AVISO — regenere: python3 scripts/build-grafana-dashboard.py"
  echo "           depois: ./scripts/grafana-reset-dashboard.sh"
fi

echo ""
echo "Se (1) e (2) OK mas Grafana vazio: intervalo «Last 6 hours», datasource Prometheus,"
echo "e ./scripts/grafana-reset-dashboard.sh após build-grafana-dashboard.py"
