#!/usr/bin/env bash
# Recuperação rápida no host Windows/WSL (conflito de nomes + Created stuck).
# Uso: bash scripts/fix-stack-now.sh
set -euo pipefail

DEPLOY="${DOCMASTER_DEPLOY_DIR:-/home/docmaster/docmaster-core}"
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-docmaster}"
cd "$DEPLOY"

CORE=(
  ollama llm_api llm_agent chromadb languagetool text_corrector_service
  rag_service backend frontend-vue cloudflared-tunnel
)

echo "==> project=$COMPOSE_PROJECT_NAME deploy=$DEPLOY"
echo "==> a remover contentores core (forçado)"
docker rm -f "${CORE[@]}" 2>/dev/null || true

echo "==> compose up core"
docker compose up -d "${CORE[@]}"

echo "==> estado"
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'NAMES|backend|frontend|cloudflared|ollama|llm_api|chromadb|rag_service' || true

for name in backend frontend-vue cloudflared-tunnel; do
  if docker ps --format '{{.Names}}' | grep -qx "$name"; then
    echo "OK  $name"
  else
    echo "FAIL $name"
    docker ps -a --filter "name=^/${name}$" --format '{{.Names}} {{.Status}}'
    exit 1
  fi
done
echo "Concluído"
