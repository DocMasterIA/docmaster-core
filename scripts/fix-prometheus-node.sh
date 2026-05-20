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

link_node_exporter_to_prometheus_network() {
  if ! docker container inspect prometheus node_exporter >/dev/null 2>&1; then
    return 0
  fi
  local net
  net="$(docker inspect prometheus --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' | awk '{print $1}')"
  if [[ -z "$net" ]]; then
    echo "AVISO: rede do prometheus não encontrada"
    return 0
  fi
  if docker inspect node_exporter --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' | grep -qF "$net"; then
    echo "node_exporter — já na rede $net (scrape node_exporter:9100)"
  elif docker network connect "$net" node_exporter 2>/dev/null; then
    echo "node_exporter — ligado à rede $net do prometheus"
  else
    echo "AVISO: não ligou à rede $net; scrape pode falhar (up=0)"
  fi
}

ensure_node_exporter
ensure_prometheus
link_node_exporter_to_prometheus_network

verify_prometheus_node_target() {
  local in_container
  in_container="$(docker exec prometheus cat /etc/prometheus/prometheus.yml 2>/dev/null || true)"
  if echo "$in_container" | grep -q 'host.docker.internal:9100'; then
    echo "ERRO: dentro do contentor ainda há host.docker.internal:9100"
    echo "  git pull && confira config/prometheus.yml no host:"
    grep -A2 'job_name: node' "$PROM_CFG" || true
    return 1
  fi
  if ! echo "$in_container" | grep -q 'node_exporter:9100'; then
    echo "ERRO: config no contentor sem node_exporter:9100"
    return 1
  fi
  return 0
}

apply_prometheus_config() {
  if ! verify_prometheus_node_target; then
    echo "prometheus — recriar contentor para montar config atual..."
    docker rm -f prometheus
    "${COMPOSE[@]}" up -d --no-deps prometheus
    sleep 3
    verify_prometheus_node_target || exit 1
  fi
  reload_prometheus_config 2>/dev/null || true
  sleep 2
  local scrape_url
  scrape_url="$(curl -sf http://127.0.0.1:9090/api/v1/targets 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
for t in d.get('data',{}).get('activeTargets',[]):
    if t.get('labels',{}).get('job')=='node':
        print(t.get('scrapeUrl',''))
        break
" 2>/dev/null || true)"
  if [[ "$scrape_url" == *host.docker.internal* ]]; then
    echo "ERRO: target node ainda aponta para $scrape_url"
    echo "  docker rm -f prometheus && docker compose -f $REPO_ROOT/docker-compose.yml up -d --no-deps prometheus"
    exit 1
  fi
  echo "prometheus — scrape node: ${scrape_url:-?}"
}

apply_prometheus_config

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
