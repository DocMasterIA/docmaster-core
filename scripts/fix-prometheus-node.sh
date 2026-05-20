#!/usr/bin/env bash
# Recria Prometheus com job node + valida scrape (correr SEM sudo, a partir de docmaster-core).
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
echo ""

ensure_node_exporter() {
  if docker container inspect node_exporter >/dev/null 2>&1; then
    local state
    state="$(docker inspect -f '{{.State.Status}}' node_exporter)"
    if [[ "$state" == "running" ]]; then
      echo "node_exporter — contentor já em execução (reutilizado; evita conflito de nome)."
    else
      echo "node_exporter — a arrancar contentor existente..."
      docker start node_exporter
    fi
    return 0
  fi
  echo "node_exporter — a criar via docker compose..."
  docker compose up -d node_exporter
}

ensure_node_exporter || {
  echo ""
  echo "Conflito de nome: outro projeto Docker já criou «node_exporter»."
  echo "  Opção A (recomendado): docker start node_exporter"
  echo "  Opção B: docker rm -f node_exporter && docker compose up -d node_exporter"
  exit 1
}

echo "Prometheus — recriar só o prometheus (--no-deps; não mexe no node_exporter existente)..."
docker compose up -d --force-recreate --no-deps prometheus

echo "Aguardando API do Prometheus (até 45s)..."
ready=0
for i in $(seq 1 45); do
  if curl -sf --max-time 2 http://127.0.0.1:9090/-/ready >/dev/null 2>&1; then
    echo "Prometheus ready (${i}s)"
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" -ne 1 ]]; then
  echo "ERRO: Prometheus não responde em :9090"
  docker compose ps prometheus
  docker compose logs prometheus --tail 40
  exit 1
fi

echo ""
echo "Scrape node → $(grep -A2 'job_name: node' "$PROM_YML" | grep targets || true)"
echo "Command do contentor prometheus:"
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
if curl -sf 'http://127.0.0.1:9090/api/v1/query?query=up%7Bjob%3D%22node%22%7D' | python3 -m json.tool; then
  :
else
  echo "AVISO: job node ainda DOWN — veja http://127.0.0.1:9090/targets"
fi

echo ""
if curl -sf --max-time 3 http://127.0.0.1:9100/metrics 2>/dev/null | grep -q '^node_memory_'; then
  echo "OK — node_exporter no host :9100"
else
  echo "AVISO — curl 127.0.0.1:9100 falhou no host (sem sudo). Scrape usa host.docker.internal:9100."
fi

echo ""
echo "Próximo: ./scripts/check-host-metrics.sh"
