#!/usr/bin/env bash
# Diagnóstico: node_exporter + scrape Prometheus (painéis Host no Grafana).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

NODE_URL="${NODE_METRICS_URL:-http://127.0.0.1:9100/metrics}"
PROM_URL="${PROMETHEUS_URL:-http://127.0.0.1:9090}"

echo "=== Host metrics (node_exporter) ==="
echo "node_exporter: $NODE_URL"
echo ""

if curl -sf --max-time 5 "$NODE_URL" | head -3 | grep -q node_memory; then
  echo "OK — node_exporter responde (node_memory_* no /metrics)"
else
  echo "FALHOU — node_exporter inacessível em $NODE_URL"
  echo "  Suba: docker compose up -d node_exporter"
  echo "  Ou no servidor da API: curl -s http://127.0.0.1:9100/metrics | head"
fi

echo ""
echo "=== Prometheus scrape (job node) ==="
echo "Prometheus: $PROM_URL"
echo ""

if command -v python3 >/dev/null 2>&1; then
  UP="$(curl -sf --max-time 8 "${PROM_URL}/api/v1/query?query=up%7Bjob%3D%22node%22%7D" 2>/dev/null || true)"
  if echo "$UP" | python3 -c "
import json,sys
d=json.load(sys.stdin)
r=d.get('data',{}).get('result') or []
if not r:
    sys.exit(1)
v=float(r[0]['value'][1])
sys.exit(0 if v>=1 else 2)
" 2>/dev/null; then
    echo "OK — up{job=\"node\"} = 1 (Prometheus está a fazer scrape)"
  else
    echo "FALHOU — up{job=\"node\"} ausente ou 0"
    echo "  Targets: ${PROM_URL}/targets (procure job node)"
    echo "  Compose: docker compose up -d node_exporter prometheus"
    echo "  Produção remota: cp config/prometheus.d/20-node-prod.yml.example \\"
    echo "      config/prometheus.d/20-node-prod.yml  # IP:9100 do servidor API"
    echo "    Edite docker-compose.yml command do prometheus para incluir esse ficheiro:"
    echo "      --config.file=/etc/prometheus/prometheus.d/20-node-prod.yml"
    echo "    docker compose restart prometheus"
  fi
else
  curl -sf "${PROM_URL}/api/v1/query?query=up%7Bjob%3D%22node%22%7D" || echo "(sem python3/curl para validar query)"
fi

echo ""
echo "Grafana: painel «Node scrape» deve ser 1; CPU/RAM zerados com scrape DOWN é normal (não é CPU a 0%)."
