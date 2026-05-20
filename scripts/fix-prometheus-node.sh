#!/usr/bin/env bash
# Host metrics: node_exporter + Prometheus job «node».
# Usa SEMPRE o docker-compose deste repo (evita conflito ~/ vs docmaster-core).
# Correr SEM sudo: cd ~/docmaster-core && ./scripts/fix-prometheus-node.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
COMPOSE=(docker compose -f "$REPO_ROOT/docker-compose.yml")
PROM_CFG="$REPO_ROOT/config/prometheus.yml"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "ERRO: não execute com sudo."
  exit 1
fi

if ! grep -q 'job_name: node' "$PROM_CFG"; then
  echo "ERRO: $PROM_CFG sem job node — git pull."
  exit 1
fi

echo "Repo: $REPO_ROOT"
echo "Compose: ${COMPOSE[*]}"
echo ""

container_config_mount() {
  local name="$1"
  docker inspect "$name" --format '{{range .Mounts}}{{if eq .Destination "/etc/prometheus/prometheus.yml"}}{{.Source}}{{end}}{{end}}' 2>/dev/null || true
}

ensure_node_exporter() {
  if docker container inspect node_exporter >/dev/null 2>&1; then
    if [[ "$(docker inspect -f '{{.State.Status}}' node_exporter)" != "running" ]]; then
      echo "node_exporter — docker start"
      docker start node_exporter
    else
      echo "node_exporter — já em execução"
    fi
    return 0
  fi
  echo "node_exporter — criar (${COMPOSE[*]} up -d node_exporter)"
  "${COMPOSE[@]}" up -d node_exporter
}

ensure_prometheus() {
  local mount expected
  expected="$PROM_CFG"

  if docker container inspect prometheus >/dev/null 2>&1; then
    mount="$(container_config_mount prometheus)"
    if [[ "$mount" == "$expected" ]]; then
      if [[ "$(docker inspect -f '{{.State.Status}}' prometheus)" != "running" ]]; then
        echo "prometheus — docker start"
        docker start prometheus
        sleep 2
      else
        echo "prometheus — já em execução com config deste repo"
      fi
      reload_prometheus_config
      return 0
    fi
    echo "prometheus — contentor antigo (config: ${mount:-desconhecido})"
    echo "  Esperado: $expected"
    echo "  A remover e recriar com o compose deste repo..."
    docker rm -f prometheus
  fi

  echo "prometheus — criar (${COMPOSE[*]} up -d --no-deps prometheus)"
  "${COMPOSE[@]}" up -d --no-deps prometheus
}

reload_prometheus_config() {
  if curl -sf -X POST http://127.0.0.1:9090/-/reload >/dev/null 2>&1; then
    echo "prometheus — config recarregada (POST /-/reload)"
    return 0
  fi
  if docker kill -s HUP prometheus >/dev/null 2>&1; then
    echo "prometheus — config recarregada (SIGHUP; na próxima recriação use --web.enable-lifecycle)"
    sleep 2
    return 0
  fi
  echo "AVISO: não foi possível reload; recrie uma vez: docker rm -f prometheus && ${COMPOSE[*]} up -d --no-deps prometheus"
}

ensure_node_exporter
ensure_prometheus

echo ""
echo "Aguardando Prometheus (até 45s)..."
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
  echo "ERRO: :9090 sem resposta"
  docker logs prometheus --tail 40
  exit 1
fi

echo ""
echo "Targets:"
curl -sf http://127.0.0.1:9090/api/v1/targets 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
for t in d.get('data',{}).get('activeTargets',[]):
    print(' ', t.get('labels',{}).get('job','?'), t.get('health','?'), t.get('scrapeUrl',''))
" || true

echo ""
echo 'up{job="node"}:'
curl -sf 'http://127.0.0.1:9090/api/v1/query?query=up%7Bjob%3D%22node%22%7D' | python3 -m json.tool || echo "  (job node ainda ausente — confira config e targets)"

echo ""
echo "Regra: use sempre «docker compose -f ~/docmaster-core/docker-compose.yml» ou cd ~/docmaster-core."
echo "Não misture «docker compose» em ~ e em docmaster-core (mesmos container_name)."
