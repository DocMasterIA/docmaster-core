#!/usr/bin/env bash
# Recria Prometheus com job node + valida scrape (correr SEM sudo, em docmaster-core).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "ERRO: não execute com sudo. Use: ./scripts/fix-prometheus-node.sh"
  exit 1
fi

PROM_YML="$REPO_ROOT/config/prometheus.yml"
if ! grep -q 'job_name: node' "$PROM_YML"; then
  echo "ERRO: $PROM_YML sem job_name: node — faça git pull."
  exit 1
fi

echo "Repo: $REPO_ROOT"
echo "Subindo node_exporter + recriando prometheus..."
docker compose up -d node_exporter
docker compose up -d --force-recreate prometheus

echo "Aguardando API do Prometheus (até 30s)..."
for i in $(seq 1 30); do
  if curl -sf --max-time 2 http://127.0.0.1:9090/-/ready >/dev/null 2>&1; then
    echo "Prometheus ready (${i}s)"
    break
  fi
  sleep 1
  if [[ "$i" -eq 30 ]]; then
    echo "ERRO: Prometheus não responde em :9090"
    docker compose ps prometheus
    docker compose logs prometheus --tail 40
    exit 1
  fi
done

echo ""
echo "Command do contentor:"
docker inspect prometheus --format '{{range .Config.Cmd}}{{.}} {{end}}' 2>/dev/null || true
echo ""

echo "Targets (resumo):"
curl -sf http://127.0.0.1:9090/api/v1/targets 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
for t in d.get('data',{}).get('activeTargets',[]):
    print(t.get('labels',{}).get('job','?'), t.get('health','?'), t.get('scrapeUrl',''))
" || echo "(falha ao ler /api/v1/targets)"

echo ""
echo "up{job=\"node\"}:"
curl -sf 'http://127.0.0.1:9090/api/v1/query?query=up%7Bjob%3D%22node%22%7D' | python3 -m json.tool

echo ""
curl -sf --max-time 3 http://127.0.0.1:9100/metrics 2>/dev/null | grep -m1 '^node_memory' \
  && echo "OK — node_exporter no host :9100" \
  || echo "AVISO — curl 127.0.0.1:9100 falhou no host (no WSL tente sem sudo; scrape Docker pode funcionar mesmo assim)"
