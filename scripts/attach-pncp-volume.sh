#!/usr/bin/env bash
# Aponta o compose PNCP para um volume Docker existente (índice antigo).
# Uso: PNCP_DATA_VOLUME=docmaster-pncp_pncp_researcher_data ./scripts/attach-pncp-volume.sh
#
# Docker Desktop (WSL): cria/usa docker-compose.pncp.noports.yml (porta 8012 no host falha com 500).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY="${DOCMASTER_DEPLOY_DIR:-$SCRIPT_DIR/..}"
DEPLOY="$(cd "$DEPLOY" && pwd)"
COMPOSE_FILE="${DOCMASTER_PNCP_COMPOSE_FILE:-$DEPLOY/docker-compose.pncp.yml}"
OVERRIDE_FILE="${DEPLOY}/docker-compose.pncp.override.yml"
NOPORTS_FILE="${DEPLOY}/docker-compose.pncp.noports.yml"
VOL="${PNCP_DATA_VOLUME:-}"

if [[ -z "$VOL" ]]; then
  echo "ERRO: defina PNCP_DATA_VOLUME (nome do volume com o .db grande)."
  echo "Liste volumes: ./scripts/find-pncp-db-volumes.sh"
  exit 1
fi

if ! docker volume inspect "$VOL" >/dev/null 2>&1; then
  echo "ERRO: volume $VOL não existe"
  exit 1
fi

cat >"$OVERRIDE_FILE" <<EOF
# Gerado por attach-pncp-volume.sh — reutiliza volume com índice PNCP existente.
volumes:
  pncp_researcher_data:
    external: true
    name: ${VOL}
EOF

# Sem porta no host: site usa pncp_researcher_service:8012 na docmaster_net.
if [[ "${PNCP_PUBLISH_HOST_PORT:-0}" != "1" ]]; then
  cat >"$NOPORTS_FILE" <<'EOF'
# Gerado por attach-pncp-volume.sh — evita bind 127.0.0.1:8012 (Docker Desktop WSL).
services:
  pncp_researcher_service:
    ports: !reset []
EOF
fi

echo "Escrito: $OVERRIDE_FILE"
echo "Volume: $VOL -> /data/pncp"
[[ -f "$NOPORTS_FILE" ]] && echo "Usando: $NOPORTS_FILE (sem porta 8012 no host)"
echo ""
cd "$DEPLOY"
COMPOSE_ARGS=(-f "$COMPOSE_FILE" -f "$OVERRIDE_FILE")
[[ -f "$NOPORTS_FILE" ]] && COMPOSE_ARGS+=(-f "$NOPORTS_FILE")

echo "==> A remover contentores PNCP antigos (volumes intactos — sem -v)..."
docker compose "${COMPOSE_ARGS[@]}" down --remove-orphans 2>/dev/null || true
docker rm -f pncp_researcher_service 2>/dev/null || true
while IFS= read -r cid; do
  [[ -z "$cid" ]] && continue
  docker rm -f "$cid" 2>/dev/null || true
done < <(docker ps -aq --filter "name=pncp_researcher" 2>/dev/null || true)

echo "==> A subir pncp_researcher_service com volume ${VOL}..."
docker compose "${COMPOSE_ARGS[@]}" up -d --force-recreate pncp_researcher_service

sleep 5
echo "==> /health"
docker exec pncp_researcher_service python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/health', timeout=30).read().decode())" \
  | python3 -m json.tool 2>/dev/null || true
echo ""
echo "==> /local-index/stats (resumo)"
docker exec pncp_researcher_service python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/local-index/stats', timeout=120).read().decode())" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('  total_contratos:', d.get('total_contratos')); print('  total_itens:', d.get('total_itens'))" \
  2>/dev/null || true
echo ""
echo "Mantenha 24/7: ./scripts/ensure-pncp-researcher.sh  (não use down -v)"
echo "NÃO rode attach de novo sem precisar — use o compose com override + noports."
