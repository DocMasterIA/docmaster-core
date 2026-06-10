#!/usr/bin/env bash
# Copia código PNCP researcher para o contentor em execução e reinicia (hotfix DESKTOP).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="${DOCMASTER_DEPLOY_DIR:-$SCRIPT_DIR/..}"
REPO="$(cd "$REPO" && pwd)"
APP="/app/pncp_researcher_service/app"
C="pncp_researcher_service"

if ! docker inspect "$C" >/dev/null 2>&1; then
  echo "ERRO: contentor $C não existe"
  exit 1
fi

for f in config.py local_index.py service.py api.py search_diagnose.py ingest_worker.py ingest_planner.py ingest_queue.py ingest_maintenance.py ingest_runtime.py schemas.py supplier_resolver.py pncp_client.py; do
  src="$REPO/pncp_researcher_service/app/$f"
  [[ -f "$src" ]] || { echo "ERRO: $src não encontrado"; exit 1; }
  docker cp "$src" "$C:$APP/$f"
  echo "OK  $f"
done

docker restart "$C"
echo "Aguardando health..."
for _ in $(seq 1 30); do
  if docker exec "$C" python -c \
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/health', timeout=5)" \
    >/dev/null 2>&1; then
    echo "OK  PNCP researcher reiniciado"
    docker exec "$C" python -c \
      "from pncp_researcher_service.app.local_index import contract_needs_items_refresh; print('skip_fn ok')"
    if docker exec "$C" grep -q 'purge_redundant_dead_tasks' "$APP/ingest_maintenance.py"; then
      echo "OK  ingest_maintenance.py (purge dead)"
    else
      echo "AVISO: ingest_maintenance.py no contentor parece desatualizado"
      exit 1
    fi
    exit 0
  fi
  sleep 2
done
echo "AVISO: health ainda não respondeu — veja docker logs $C"
exit 1
