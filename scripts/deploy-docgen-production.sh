#!/usr/bin/env bash
# Deploy geração de documentos (rag/backend/llm/frontend) — sem apagar volumes.
# Uso na VPS: cd ~/docmaster-core && bash scripts/deploy-docgen-production.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

log() { echo "$(date -Is) $*"; }

load_env() {
  local f
  for f in "$HOME/.env" "$ROOT/.env"; do
    if [[ -f "$f" ]]; then
      log "Carregando env: $f"
      set -a
      # shellcheck disable=SC1090
      source "$f"
      set +a
      return 0
    fi
  done
  log "AVISO: nenhum .env encontrado"
}

log "=== 1) git pull ==="
git fetch origin
git checkout main
git pull --ff-only origin main
log "HEAD=$(git rev-parse --short HEAD)"

load_env
if [[ -z "${CLOUDFLARE_TUNNEL_TOKEN:-}" ]]; then
  log "AVISO: CLOUDFLARE_TUNNEL_TOKEN vazio — túnel pode falhar ao recreate"
fi
if [[ ! -e "$ROOT/.env" && -f "$HOME/.env" ]]; then
  ln -sfn "$HOME/.env" "$ROOT/.env"
  log "symlink $ROOT/.env -> $HOME/.env"
fi

log "=== 2) build imagens docgen (context = raiz do repo) ==="
# Builds explícitos: evita path docmaster-core/docmaster-core quando o compose
# ainda tem context antigo, e evita etiquetar frontend como Django.
docker build -t docmaster-rag_service -f rag_service/Dockerfile .
docker build -t docmaster-backend -f Dockerfile .
docker build -t docmaster-llm_api -f llm_api/Dockerfile .
docker build -t docmaster-llm_agent -f llm_agent/Dockerfile .
docker build -t docmaster-frontend-vue -f frontend-vue/Dockerfile frontend-vue

log "=== 2b) libertar nomes + up --no-build ==="
docker stop rag_service backend llm_api llm_agent frontend-vue 2>/dev/null || true
docker rm rag_service backend llm_api llm_agent frontend-vue 2>/dev/null || true

# Preferir compose a partir da raiz do repo (contexts .)
if docker compose version >/dev/null 2>&1; then
  docker compose up -d --no-build --no-deps \
    rag_service backend llm_api llm_agent frontend-vue
else
  log "ERRO: docker compose indisponível"
  exit 1
fi

log "=== 3) redes túnel ==="
for c in frontend-vue backend; do
  docker network connect docmaster_default "$c" 2>/dev/null || true
  docker network connect docmaster_net "$c" 2>/dev/null || true
  docker network connect docmaster-core_default "$c" 2>/dev/null || true
done
if docker ps --format '{{.Names}}' | grep -qx qwen_llm_service; then
  for net in docmaster-core_default docmaster_default docmaster_net; do
    docker network connect "$net" qwen_llm_service 2>/dev/null || true
    docker network connect "$net" rag_service 2>/dev/null || true
    docker network connect "$net" llm_api 2>/dev/null || true
  done
fi

if [[ -n "${CLOUDFLARE_TUNNEL_TOKEN:-}" ]]; then
  docker compose up -d --no-build --no-deps --force-recreate cloudflared-tunnel 2>/dev/null \
    || docker restart cloudflared-tunnel 2>/dev/null || true
else
  docker restart cloudflared-tunnel 2>/dev/null || true
fi

log "=== 5) smoke ==="
docker images --format '{{.Repository}}:{{.Tag}} {{.CreatedAt}}' | grep -E 'docmaster-(backend|rag|llm|frontend)' || true
docker exec rag_service sh -c \
  'PYTHONPATH=/app python -c "from rag_service.app.docx_typography import ensure_signature_nome_blank_lines; print(\"ok\")"'
curl -sI https://api.docmasteria.com.br/api/me/ | head -5 || true
curl -s https://docmasteria.com.br/ | grep -oE 'assets/index-[^"]+' || true
docker exec frontend-vue ls /usr/share/nginx/html/assets | grep -i login || true
docker ps --filter name='rag_service|backend|llm_api|llm_agent|frontend-vue|cloudflared' \
  --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'

log "=== concluído ==="
log "Cloudflare: Purge Everything em docmasteria.com.br"
log "Teste manual: gerar TR/DFD numa dispensa"
