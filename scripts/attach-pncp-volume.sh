#!/usr/bin/env bash
# Aponta o compose PNCP para um volume Docker existente (índice antigo).
# Uso: PNCP_DATA_VOLUME=docmaster_pncp_researcher_data ./scripts/attach-pncp-volume.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY="${DOCMASTER_DEPLOY_DIR:-$SCRIPT_DIR/..}"
DEPLOY="$(cd "$DEPLOY" && pwd)"
COMPOSE_FILE="${DOCMASTER_PNCP_COMPOSE_FILE:-$DEPLOY/docker-compose.pncp.yml}"
OVERRIDE_FILE="${DEPLOY}/docker-compose.pncp.override.yml"
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

echo "Escrito: $OVERRIDE_FILE"
echo "Volume: $VOL -> /data/pncp"
echo ""
cd "$DEPLOY"
docker compose -f "$COMPOSE_FILE" -f "$OVERRIDE_FILE" up -d --force-recreate

sleep 3
curl -sf http://127.0.0.1:8012/api/pncp-research/local-index/stats | python3 -m json.tool 2>/dev/null || \
  curl -sf http://127.0.0.1:8012/api/pncp-research/local-index/stats
