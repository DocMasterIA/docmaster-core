#!/usr/bin/env bash
# Grafana vazio com Prometheus OK: rede Docker + datasource + dashboard.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
COMPOSE=(docker compose -f "$REPO_ROOT/docker-compose.yml")

if [[ "$(id -u)" -eq 0 ]]; then
  echo "ERRO: não use sudo."
  exit 1
fi

echo "=== fix-grafana-prometheus ==="
echo ""

# 1) Rede: grafana na mesma rede que prometheus (se contentores existirem)
if docker container inspect prometheus grafana >/dev/null 2>&1; then
  net="$(docker inspect prometheus --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' | awk '{print $1}')"
  if [[ -n "$net" ]]; then
    if docker inspect grafana --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' | grep -qF "$net"; then
      echo "grafana — já na rede $net"
    elif docker network connect "$net" grafana 2>/dev/null; then
      echo "grafana — ligado à rede $net (hostname prometheus:9090 passa a resolver)"
    fi
  fi
fi

# 2) Datasource provisionado: host.docker.internal:9090
echo "Datasource: http://host.docker.internal:9090 (ficheiro em config/grafana/provisioning/)"

# 3) Dashboard host (range queries)
python3 scripts/build-grafana-dashboard.py

# 4) Recriar grafana para montar provisioning + extra_hosts (sem conflito prometheus)
if docker container inspect grafana >/dev/null 2>&1; then
  echo "grafana — recriar contentor (--no-deps)"
  docker rm -f grafana
fi
"${COMPOSE[@]}" up -d --no-deps grafana

echo "Aguardando Grafana..."
for i in $(seq 1 30); do
  if curl -sf -o /dev/null -w '' http://127.0.0.1:3000/api/health 2>/dev/null; then
    echo "Grafana ready (${i}s)"
    break
  fi
  sleep 1
done

# 5) Copiar JSON para volume de provisioning se reset não for usado
if [[ -x "$REPO_ROOT/scripts/grafana-reset-dashboard.sh" ]]; then
  echo ""
  echo "Aplicar dashboard na API Grafana..."
  GRAFANA_URL=http://127.0.0.1:3000 "$REPO_ROOT/scripts/grafana-reset-dashboard.sh" || true
fi

echo ""
./scripts/verify-host-grafana.sh
