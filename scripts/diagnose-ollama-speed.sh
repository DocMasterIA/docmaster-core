#!/usr/bin/env bash
# Diagnóstico de latência Ollama / llm_api (VPS ou local).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY="${DOCMASTER_DEPLOY_DIR:-$SCRIPT_DIR/..}"
DEPLOY="$(cd "$DEPLOY" && pwd)"
COMPOSE_FILE="${DOCMASTER_COMPOSE_FILE:-$DEPLOY/docker-compose.yml}"
FAST_MODEL="${OLLAMA_MODEL_FAST:-qwen2.5:3b}"
HEAVY_MODEL="${OLLAMA_MODEL:-qwen2.5:7b}"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "ERRO: compose não encontrado: $COMPOSE_FILE"
  exit 1
fi

cd "$DEPLOY"
COMPOSE=(docker compose -f "$COMPOSE_FILE")

echo "==> Deploy: $DEPLOY"
echo ""

echo "==> Env llm_api (modelos)"
"${COMPOSE[@]}" exec -T llm_api printenv 2>/dev/null | grep -E '^OLLAMA_' || echo "(llm_api não está up)"
echo ""

echo "==> Modelos no Ollama"
docker exec ollama ollama list 2>/dev/null || echo "(container ollama não está up)"
echo ""

echo "==> GPU no container ollama"
docker exec ollama sh -c 'nvidia-smi 2>/dev/null | head -8 || echo "Sem NVIDIA visível — inferência em CPU"' 2>/dev/null || true
echo ""

run_bench() {
  local tag="$1"
  local model="$2"
  if ! docker exec ollama ollama list 2>/dev/null | grep -qF "$model"; then
    echo "SKIP $tag — modelo $model não está baixado (ollama pull $model)"
    return
  fi
  echo "==> Bench $tag ($model)"
  local start end elapsed
  start=$(date +%s.%N)
  docker exec ollama ollama run "$model" "Responda só:\nObjeto: aquisição genérica.\nJustificativa: necessidade administrativa." >/dev/null 2>&1 || true
  end=$(date +%s.%N)
  elapsed=$(python3 -c "print(round(float('$end')-float('$start'), 2))")
  echo "    tempo_wall=${elapsed}s"
  echo ""
}

run_bench "FAST" "$FAST_MODEL"
run_bench "HEAVY" "$HEAVY_MODEL"

echo "==> Teste llm_api fast=true (se porta 8002 exposta)"
if curl -sf --max-time 120 http://127.0.0.1:8002/api/llm/health >/dev/null 2>&1; then
  start=$(date +%s.%N)
  out=$(curl -s --max-time 120 -X POST http://127.0.0.1:8002/api/llm/generate \
    -H 'Content-Type: application/json' \
    -d "{\"prompt\":\"Objeto: teste.\\nJustificativa: teste.\",\"fast\":true,\"stream\":false,\"options\":{\"num_predict\":120}}")
  end=$(date +%s.%N)
  elapsed=$(python3 -c "print(round(float('$end')-float('$start'), 2))")
  model=$(echo "$out" | python3 -c "import sys,json; d=json.load(sys.stdin); print((d.get('data') or {}).get('model','?'))" 2>/dev/null || echo "?")
  echo "    modelo_resposta=$model tempo_wall=${elapsed}s"
else
  echo "    (health em 127.0.0.1:8002 indisponível — ignore se API só interna)"
fi
echo ""
echo "Dica: se FAST << HEAVY, defina OLLAMA_MODEL_FAST=$FAST_MODEL no .env e: docker compose up -d --force-recreate llm_api"
