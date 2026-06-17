#!/usr/bin/env bash
# Sobe/mantém o PNCP Researcher 24/7 (stack isolada docmaster-pncp).
# Não usa «down -v». Por padrão «up -d --no-recreate» para não matar backfill em andamento.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY="${DOCMASTER_DEPLOY_DIR:-$SCRIPT_DIR/..}"
DEPLOY="$(cd "$DEPLOY" && pwd)"
COMPOSE_FILE="${DOCMASTER_PNCP_COMPOSE_FILE:-$DEPLOY/docker-compose.pncp.yml}"
OVERRIDE_FILE="${DEPLOY}/docker-compose.pncp.override.yml"
# shellcheck source=lib/pncp-compose-args.sh
if [[ -f "${SCRIPT_DIR}/lib/pncp-compose-args.sh" ]]; then
  # shellcheck source=lib/pncp-compose-args.sh
  source "${SCRIPT_DIR}/lib/pncp-compose-args.sh"
else
  pncp_setup_compose_args() {
    local deploy="$1"
    COMPOSE_FILE="${DOCMASTER_PNCP_COMPOSE_FILE:-$deploy/docker-compose.pncp.yml}"
    OVERRIDE_FILE="${deploy}/docker-compose.pncp.override.yml"
    NOPORTS_FILE="${deploy}/docker-compose.pncp.noports.yml"
    PNCP_USE_DOCKER_HEALTH=0
    COMPOSE_ARGS=(-f "$COMPOSE_FILE")
    [[ -f "$OVERRIDE_FILE" ]] && COMPOSE_ARGS+=(-f "$OVERRIDE_FILE")
    if [[ -f "$NOPORTS_FILE" ]]; then
      COMPOSE_ARGS+=(-f "$NOPORTS_FILE")
      PNCP_USE_DOCKER_HEALTH=1
      echo "==> Sem porta 8012 no host ($NOPORTS_FILE)"
    fi
  }
  pncp_health_ok() {
    if [[ "${PNCP_USE_DOCKER_HEALTH:-0}" == "1" ]]; then
      docker exec pncp_researcher_service python -c \
        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/health', timeout=5)" \
        >/dev/null 2>&1
    else
      curl -sf --max-time 5 "$PNCP_HEALTH_URL" >/dev/null 2>&1
    fi
  }
  pncp_print_health() {
    if [[ "${PNCP_USE_DOCKER_HEALTH:-0}" == "1" ]]; then
      docker exec pncp_researcher_service python -c \
        "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/health', timeout=10).read().decode())" \
        2>/dev/null | python3 -m json.tool 2>/dev/null || true
    else
      curl -sf "$PNCP_HEALTH_URL" | python3 -m json.tool 2>/dev/null || curl -sf "$PNCP_HEALTH_URL"
    fi
  }
  pncp_print_stats_summary() {
    local stats_json
    if [[ "${PNCP_USE_DOCKER_HEALTH:-0}" == "1" ]]; then
      stats_json="$(docker exec pncp_researcher_service python -c \
        "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/local-index/stats', timeout=120).read().decode())" \
        2>/dev/null || true)"
    else
      stats_json="$(curl -sf --max-time 10 "$PNCP_STATS_URL" 2>/dev/null || true)"
    fi
    [[ -z "$stats_json" ]] && return 1
    echo "$stats_json" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('  db_path:', d.get('db_path'))
print('  total_contratos:', d.get('total_contratos'))
print('  total_itens:', d.get('total_itens'))
" 2>/dev/null
  }
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "ERRO: $COMPOSE_FILE não encontrado"
  exit 1
fi

if [[ -d "$DEPLOY/docmaster-core/pncp_researcher_service" ]]; then
  export PNCP_BUILD_CONTEXT=docmaster-core
elif [[ -d "$DEPLOY/pncp_researcher_service" ]]; then
  export PNCP_BUILD_CONTEXT=.
else
  echo "ERRO: pasta pncp_researcher_service não encontrada em $DEPLOY"
  exit 1
fi

cd "$DEPLOY"
PNCP_HEALTH_URL="${PNCP_HEALTH_URL:-http://127.0.0.1:8012/api/pncp-research/health}"
PNCP_STATS_URL="${PNCP_STATS_URL:-http://127.0.0.1:8012/api/pncp-research/local-index/stats}"

pncp_setup_compose_args "$DEPLOY"
if [[ -f "$OVERRIDE_FILE" ]]; then
  echo "==> Usando override: $OVERRIDE_FILE (volume external)"
  ext_vol="$(grep -E '^[[:space:]]*name:[[:space:]]*' "$OVERRIDE_FILE" | tail -1 | sed -E 's/^[[:space:]]*name:[[:space:]]*//; s/[[:space:]]+$//')"
  if [[ -n "${ext_vol:-}" ]] && ! docker volume inspect "$ext_vol" >/dev/null 2>&1; then
    echo ""
    echo "ERRO: volume Docker «$ext_vol» não existe (referenciado em $OVERRIDE_FILE)."
    echo "  A) Achar o índice antigo e religar:"
    echo "       ./scripts/find-pncp-db-volumes.sh"
    echo "       PNCP_DATA_VOLUME=<nome_do_volume_grande> ./scripts/attach-pncp-volume.sh"
    echo "  B) Subir com volume novo (índice vazio — reingestão depois):"
    echo "       mv $OVERRIDE_FILE ${OVERRIDE_FILE}.bak"
    echo "       ./scripts/ensure-pncp-researcher.sh"
    echo "  C) Recriar só o nome do volume (vazio; use se não houver backup):"
    echo "       docker volume create $ext_vol"
    echo "Doc: docs/deploy/PNCP-RESEARCHER-24-7.md"
    exit 1
  fi
else
  echo "==> Sem override — volume padrão do projeto docmaster-pncp"
  echo "    Se o índice sumiu após down/up: ./scripts/find-pncp-db-volumes.sh"
  echo "    PNCP_DATA_VOLUME=<volume_grande> ./scripts/attach-pncp-volume.sh"
fi

if ! docker network inspect docmaster_net >/dev/null 2>&1; then
  echo "==> A criar rede docmaster_net..."
  docker network create docmaster_net
fi

UP_FLAGS=(-d)
PNCP_SERVICE="${PNCP_SERVICE:-pncp_researcher_service}"
if [[ "${PNCP_FORCE_RECREATE:-0}" == "1" ]] || [[ "${PNCP_BUILD:-0}" == "1" ]]; then
  UP_FLAGS+=(--force-recreate)
  if [[ "${PNCP_BUILD:-0}" == "1" ]]; then
    echo "==> PNCP_BUILD=1 — rebuild da imagem + recria contentor (código novo só entra após recreate)"
  else
    echo "==> PNCP_FORCE_RECREATE=1 — a recriar contentor"
  fi
else
  UP_FLAGS+=(--no-recreate)
fi
if [[ "${PNCP_BUILD:-0}" == "1" ]]; then
  UP_FLAGS+=(--build)
fi

echo "==> PNCP Researcher 24/7 (projeto docmaster-pncp)"
if [[ "${PNCP_BUILD:-0}" == "1" ]] || [[ "${PNCP_FORCE_RECREATE:-0}" == "1" ]]; then
  echo "==> A remover contentor antigo antes do recreate (volume preservado)..."
  docker compose "${COMPOSE_ARGS[@]}" down --remove-orphans 2>/dev/null || true
  docker rm -f pncp_researcher_service 2>/dev/null || true
  while IFS= read -r cid; do
    [[ -z "$cid" ]] && continue
    docker rm -f "$cid" 2>/dev/null || true
  done < <(docker ps -aq --filter "name=pncp_researcher" 2>/dev/null || true)
fi
docker compose "${COMPOSE_ARGS[@]}" up "${UP_FLAGS[@]}" "$PNCP_SERVICE"

echo ""
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E '^(NAMES|pncp_researcher)' || true

echo ""
echo "==> /health"
ok=0
for _ in $(seq 1 15); do
  if pncp_health_ok; then
    ok=1
    break
  fi
  sleep 3
done

if [[ "$ok" -eq 1 ]]; then
  pncp_print_health
  echo ""
  echo "==> /local-index/stats (resumo)"
  pncp_print_stats_summary || true
  echo ""
  if [[ "${PNCP_USE_DOCKER_HEALTH:-0}" == "1" ]]; then
    stats_json="$(docker exec "$PNCP_SERVICE" python -c \
      "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/local-index/stats', timeout=120).read().decode())" \
      2>/dev/null || true)"
    health_json="$(docker exec "$PNCP_SERVICE" python -c \
      "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/health', timeout=30).read().decode())" \
      2>/dev/null || true)"
    items_n="$(echo "$stats_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(int(d.get('total_itens') or 0))" 2>/dev/null || echo 0)"
    db_bytes="$(echo "$health_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(int(d.get('db_bytes') or 0))" 2>/dev/null || echo 0)"
    if [[ "${items_n:-0}" -lt 1000 ]]; then
      echo ""
      echo "╔══════════════════════════════════════════════════════════════════════╗"
      echo "║  AVISO: total_itens=${items_n} — índice vazio ou volume Docker errado.          ║"
      echo "║  Recriar o contentor NÃO apaga volumes; os dados costumam estar noutro volume. ║"
      echo "║  NÃO rode «docker compose down -v».                                             ║"
      echo "║  Recuperação:                                                                   ║"
      echo "║    ./scripts/find-pncp-db-volumes.sh                                            ║"
      echo "║    PNCP_DATA_VOLUME=<volume_grande_MB> ./scripts/attach-pncp-volume.sh          ║"
      echo "╚══════════════════════════════════════════════════════════════════════╝"
      if [[ "${db_bytes:-0}" -gt 500000000 ]]; then
        echo "  (db_bytes=${db_bytes} — ficheiro grande mas 0 itens: volume correto? DB corrompido?)"
      fi
    fi
  fi
  echo ""
  echo "==> contentor (confirme «Up … seconds» — não «Up 30+ hours» após deploy com BUILD=1)"
  docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' | grep -E "^(NAMES|${PNCP_SERVICE})" || true
  if [[ "${PNCP_USE_DOCKER_HEALTH:-0}" == "1" ]]; then
    code_rev="$(docker exec "$PNCP_SERVICE" python -c \
      "from pncp_researcher_service.app.config import PNCP_SEARCH_CODE_REV; print(PNCP_SEARCH_CODE_REV)" \
      2>/dev/null || true)"
    if [[ -n "${code_rev:-}" ]]; then
      echo "==> search_code_rev (dentro do contentor): $code_rev"
    fi
  fi
  echo ""
  if [[ "${PNCP_USE_DOCKER_HEALTH:-0}" == "1" ]]; then
    echo "OK  PNCP ativo (health via docker exec; sem 127.0.0.1:8012 no host)"
  else
    echo "OK  PNCP ativo em $PNCP_HEALTH_URL"
  fi
else
  if [[ "${PNCP_USE_DOCKER_HEALTH:-0}" == "1" ]]; then
    echo "OFF PNCP /health (contentor ou API)"
  else
    echo "OFF $PNCP_HEALTH_URL"
  fi
  echo "Logs: docker compose ${COMPOSE_ARGS[*]} logs --tail 80"
  exit 1
fi

echo ""
echo "24/7: restart=always no compose. Boot automático: sudo ./scripts/install-docmaster-boot-service.sh"
echo "Ou manualmente após reboot: ./scripts/ensure-docmaster-stack.sh"
echo "NÃO use: docker compose -f docker-compose.pncp.yml down -v"
echo "Backend/outros: docker compose up -d --no-recreate backend  (não recria o PNCP)"
echo "Para total_itens SUBIR (ingestão): nohup ./scripts/run-pncp-index-ingest-loop.sh >> ~/pncp-ingest.log 2>&1 &"
echo "Doc: docs/deploy/PNCP-RESEARCHER-24-7.md"
