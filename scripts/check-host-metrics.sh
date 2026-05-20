#!/usr/bin/env bash
# Diagnóstico: node_exporter + scrape Prometheus (painéis Host no Grafana).
#
# URL padrão 127.0.0.1:9100 = porta publicada em docker-compose.yml:
#   ports: "127.0.0.1:9100:9100"  (9100 é a porta padrão do node_exporter)
# O Prometheus no Compose scrape node_exporter:9100 (rede Docker), não 127.0.0.1.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

NODE_URL="${NODE_METRICS_URL:-http://127.0.0.1:9100/metrics}"
PROM_URL="${PROMETHEUS_URL:-http://127.0.0.1:9090}"

echo "=== Host metrics (node_exporter) ==="
echo "Teste no host: $NODE_URL"
echo "  (definido em docker-compose.yml → ports: \"127.0.0.1:9100:9100\")"
echo "  Outra URL: NODE_METRICS_URL=http://IP:9100/metrics $0"
echo ""

_metrics_has_node() {
  grep -q '^node_memory_' 2>/dev/null
}

_node_ok=0
if curl -sf --max-time 5 "$NODE_URL" 2>/dev/null | _metrics_has_node; then
  echo "OK — node_exporter responde no host ($NODE_URL)"
  _node_ok=1
elif docker ps --format '{{.Names}}' 2>/dev/null | grep -qx node_exporter; then
  echo "Container node_exporter existe; testando scrape pela rede Docker (prometheus → node_exporter)..."
  if docker exec prometheus wget -qO- http://host.docker.internal:9100/metrics 2>/dev/null | _metrics_has_node; then
    echo "OK — node_exporter alcançável como o Prometheus vê (host.docker.internal:9100)"
    _node_ok=1
  fi
fi

if [[ "$_node_ok" -ne 1 ]]; then
  echo "FALHOU — nada em $NODE_URL"
  echo "  Não use sudo (docker do root ≠ docker do user docmaster)."
  echo "  docker compose ps node_exporter"
  echo "  docker compose up -d node_exporter"
  echo "  docker compose logs --tail 30 node_exporter"
fi

echo ""
echo "=== Prometheus scrape (job node) ==="
echo "Prometheus: $PROM_URL"
echo ""

if ! curl -sf --max-time 3 "${PROM_URL}/-/ready" >/dev/null 2>&1; then
  echo "FALHOU — Prometheus não responde em ${PROM_URL} (API vazia = ainda a subir ou crash)"
  echo "  cd $(pwd) && docker compose ps prometheus"
  echo "  docker compose logs prometheus --tail 50"
  echo "  ./scripts/fix-prometheus-node.sh"
elif command -v python3 >/dev/null 2>&1; then
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
    echo "  O contentor prometheus precisa RECRIAR para ler config nova (restart não basta):"
    echo "    cd $REPO_ROOT && docker compose up -d node_exporter"
    echo "    docker compose up -d --force-recreate prometheus"
    echo "  ./scripts/fix-prometheus-node.sh"
    echo "  Confirme job node em config/prometheus.yml e git pull"
  fi
else
  curl -sf "${PROM_URL}/api/v1/query?query=up%7Bjob%3D%22node%22%7D" || echo "(sem python3/curl para validar query)"
fi

echo ""
echo "Grafana: painel «Node scrape» deve ser 1; CPU/RAM zerados com scrape DOWN é normal (não é CPU a 0%)."
