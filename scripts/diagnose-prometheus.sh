#!/usr/bin/env bash
# Prometheus em Restarting / :9090 fechado — diagnóstico rápido (sem sudo).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose -f "$REPO_ROOT/docker-compose.yml")
CFG="$REPO_ROOT/config/prometheus.yml"

echo "=== diagnose-prometheus ==="
echo "Repo: $REPO_ROOT"
echo ""

if [[ ! -f "$CFG" ]]; then
  echo "ERRO: não existe $CFG"
  echo "  Provavelmente correu «docker compose» em ~ em vez de docmaster-core."
  exit 1
fi

echo "Validar YAML:"
python3 -c "import yaml; yaml.safe_load(open('$CFG')); print('OK — prometheus.yml parseável')" 2>/dev/null \
  || echo "AVISO: instale python3-yaml ou valide o ficheiro à mão"

echo ""
echo "Estado do contentor:"
docker ps -a --filter name=^prometheus$ --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

echo ""
echo "Últimas linhas do log (procure level=ERROR ou parse error):"
docker logs prometheus --tail 35 2>&1 || echo "(sem contentor prometheus)"

if docker container inspect prometheus >/dev/null 2>&1; then
  echo ""
  echo "Mount do prometheus.yml no contentor:"
  docker inspect prometheus --format '{{range .Mounts}}{{if eq .Destination "/etc/prometheus/prometheus.yml"}}{{.Source}} -> {{.Destination}}{{end}}{{end}}'
  echo ""
  echo "Trecho job node dentro do contentor:"
  docker exec prometheus cat /etc/prometheus/prometheus.yml 2>/dev/null | sed -n '/job_name: node/,+6p' \
    || echo "(contentor parado — não foi possível cat)"
fi

echo ""
echo "Recuperação típica:"
echo "  cd $REPO_ROOT"
echo "  docker rm -f prometheus"
echo "  ${COMPOSE[*]} up -d --no-deps prometheus"
echo "  docker logs prometheus --tail 20 -f"
