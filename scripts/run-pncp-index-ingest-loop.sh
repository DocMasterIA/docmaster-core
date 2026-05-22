#!/usr/bin/env bash
# Alimentação contínua do índice PNCP: busca no portal e grava contratos + itens no SQLite.
#
# O ensure-pncp-researcher.sh só mantém o API 24/7; este script é quem faz o total_itens subir.
#
# Uso:
#   ./scripts/run-pncp-index-ingest-loop.sh              # loop infinito (nohup recomendado)
#   PNCP_INGEST_ONCE=1 ./scripts/run-pncp-index-ingest-loop.sh   # uma volta em todas as UFs
#
# Exemplo 24/7 em background:
#   nohup ./scripts/run-pncp-index-ingest-loop.sh >> /var/log/pncp-ingest.log 2>&1 &
#
set -euo pipefail

BASE_URL="${PNCP_BASE_URL:-http://127.0.0.1:8012}"
MONTHS="${PNCP_INGEST_MONTHS:-12}"
MAX_PAGINAS="${PNCP_INGEST_MAX_PAGINAS:-25}"
TAMANHO="${PNCP_INGEST_TAMANHO_PAGINA:-50}"
SLEEP_BETWEEN_UF="${PNCP_INGEST_SLEEP_UF_SEC:-30}"
SLEEP_BETWEEN_CYCLES="${PNCP_INGEST_SLEEP_CYCLE_SEC:-600}"
CURL_MAX_TIME="${PNCP_INGEST_CURL_MAX_TIME_SEC:-7200}"

UFS=(
  AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO
)

log() {
  echo "$(date -Is) $*"
}

stats_snapshot() {
  curl -sf --max-time 30 "${BASE_URL}/api/pncp-research/local-index/stats" 2>/dev/null | python3 -c "
import json,sys
try:
  d=json.load(sys.stdin)
  print(d.get('total_contratos'), d.get('total_itens'))
except Exception:
  print('?','?')
" 2>/dev/null || echo "? ?"
}

run_backfill_uf() {
  local uf="$1"
  local body
  body=$(python3 - <<PY
import json
print(json.dumps({
    "months": int("${MONTHS}"),
    "max_paginas": int("${MAX_PAGINAS}"),
    "tamanho_pagina": int("${TAMANHO}"),
    "uf": "${uf}",
    "codigo_municipio_ibge": None,
    "include_items": True,
}))
PY
)
  log "INGEST START uf=${uf} max_paginas=${MAX_PAGINAS}"
  if curl -sS --max-time "${CURL_MAX_TIME}" -X POST "${BASE_URL}/api/pncp-research/local-index/backfill" \
    -H "Content-Type: application/json" \
    -d "${body}" >>"${PNCP_INGEST_LOG:-/dev/stdout}" 2>&1; then
    log "INGEST OK uf=${uf}"
  else
    log "INGEST FAIL uf=${uf} (curl exit $?)"
  fi
  read -r tc ti <<<"$(stats_snapshot)"
  log "STATS após ${uf}: contratos=${tc} itens=${ti}"
}

log "PNCP ingest loop — ${BASE_URL}"
read -r c0 i0 <<<"$(stats_snapshot)"
log "STATS início: contratos=${c0} itens=${i0}"

while true; do
  for uf in "${UFS[@]}"; do
    run_backfill_uf "${uf}"
    sleep "${SLEEP_BETWEEN_UF}"
  done
  read -r c1 i1 <<<"$(stats_snapshot)"
  log "STATS fim do ciclo: contratos=${c1} itens=${i1}"
  if [[ "${PNCP_INGEST_ONCE:-0}" == "1" ]]; then
    log "PNCP_INGEST_ONCE=1 — a sair."
    exit 0
  fi
  log "Pausa ${SLEEP_BETWEEN_CYCLES}s antes do próximo ciclo..."
  sleep "${SLEEP_BETWEEN_CYCLES}"
done
