#!/usr/bin/env bash
# Alimentação contínua do índice PNCP: busca no portal e grava contratos + itens no SQLite.
#
# O ensure-pncp-researcher.sh só mantém o API 24/7; este script alimenta o índice local.
# Com PNCP_INGEST_WATERMARK_RESUME (default), cada UF avança páginas no PNCP — cobertura de busca
# cresce mesmo quando total_itens sobe devagar (refresh + páginas novas).
#
# Uso:
#   ./scripts/run-pncp-index-ingest-loop.sh              # loop infinito (nohup recomendado)
#   PNCP_INGEST_ONCE=1 ./scripts/run-pncp-index-ingest-loop.sh   # uma volta em todas as UFs
#
# Exemplo 24/7 em background:
#   nohup ./scripts/run-pncp-index-ingest-loop.sh >> /var/log/pncp-ingest.log 2>&1 &
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY="${DOCMASTER_DEPLOY_DIR:-$SCRIPT_DIR/..}"
DEPLOY="$(cd "$DEPLOY" && pwd)"

LOCK_FILE="${PNCP_INGEST_LOCK_FILE:-${HOME}/.pncp-index-ingest.lock}"
exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
  echo "$(date -Is) ERRO: ingestão PNCP já em execução (lock: ${LOCK_FILE})."
  echo "  ps aux | grep run-pncp-index-ingest"
  echo "  kill <pid>  # ou: rm -f ${LOCK_FILE}  (só se tiver certeza)"
  exit 1
fi

BASE_URL="${PNCP_FEED_BASE_URL:-http://127.0.0.1:8013}"
FEED_CONTAINER="${PNCP_FEED_CONTAINER:-price_index_feed_pncp}"
FEED_PORT="${PNCP_FEED_PORT:-8013}"
# Com docker-compose.pncp.noports.yml não há 8012 no host — curl no host trava/falha o backfill.
# Preferir docker exec quando o contentor existe (mesmo se DEPLOY=docmaster-core/ sem noports.yml).
PNCP_INGEST_VIA_DOCKER="${PNCP_INGEST_VIA_DOCKER:-}"
_pncp_compose_home="${DOCMASTER_DEPLOY_DIR:-${HOME}}"
if [[ -z "${PNCP_INGEST_VIA_DOCKER}" ]]; then
  if docker inspect "${FEED_CONTAINER}" >/dev/null 2>&1; then
    PNCP_INGEST_VIA_DOCKER=1
  elif docker inspect price_index_feed_service >/dev/null 2>&1; then
    PNCP_INGEST_VIA_DOCKER=1
    FEED_CONTAINER=price_index_feed_service
    FEED_PORT=8013
  elif docker inspect pncp_researcher_service >/dev/null 2>&1; then
    PNCP_INGEST_VIA_DOCKER=1
    FEED_CONTAINER=pncp_researcher_service
    FEED_PORT=8012
  elif [[ -f "${DEPLOY}/docker-compose.pncp.noports.yml" ]] \
    || [[ -f "${_pncp_compose_home}/docker-compose.pncp.noports.yml" ]]; then
    PNCP_INGEST_VIA_DOCKER=1
  elif ! curl -sf --max-time 5 "${BASE_URL}/api/pncp-feed/health" >/dev/null 2>&1 \
    && ! curl -sf --max-time 5 "http://127.0.0.1:8012/api/pncp-research/health" >/dev/null 2>&1; then
    PNCP_INGEST_VIA_DOCKER=1
  else
    PNCP_INGEST_VIA_DOCKER=0
  fi
fi
MONTHS="${PNCP_INGEST_MONTHS:-12}"
DAYS="${PNCP_INGEST_DAYS:-365}"
MAX_PAGINAS="${PNCP_INGEST_MAX_PAGINAS:-60}"
TAMANHO="${PNCP_INGEST_TAMANHO_PAGINA:-50}"
SLEEP_BETWEEN_UF="${PNCP_INGEST_SLEEP_UF_SEC:-10}"
SLEEP_BETWEEN_CYCLES="${PNCP_INGEST_SLEEP_CYCLE_SEC:-180}"
CURL_MAX_TIME="${PNCP_INGEST_CURL_MAX_TIME_SEC:-7200}"

UFS=(
  AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO
)

log() {
  echo "$(date -Is) $*"
}

# GET/POST no PNCP: host (curl) ou dentro do contentor (noports / porta 8012 indisponível).
pncp_http() {
  local method="$1"
  local path="$2"
  local body="${3:-}"
  local timeout_sec="${4:-30}"
  if [[ "${PNCP_INGEST_VIA_DOCKER}" == "1" ]]; then
    docker exec "${FEED_CONTAINER}" python -c "
import json, sys, urllib.request
method, path, body, timeout, port = sys.argv[1], sys.argv[2], sys.argv[3] or '', int(sys.argv[4]), sys.argv[5]
url = 'http://127.0.0.1:' + port + path
data = body.encode('utf-8') if body else None
req = urllib.request.Request(url, data=data, method=method)
if body:
    req.add_header('Content-Type', 'application/json')
with urllib.request.urlopen(req, timeout=timeout) as resp:
    sys.stdout.write(resp.read().decode('utf-8', errors='replace'))
" "$method" "$path" "$body" "$timeout_sec" "$FEED_PORT"
  elif [[ "$method" == "GET" ]]; then
    curl -sf --max-time "${timeout_sec}" "${BASE_URL}${path}"
  else
    curl -sS --max-time "${timeout_sec}" -X "$method" "${BASE_URL}${path}" \
      -H "Content-Type: application/json" \
      -d "$body"
  fi
}

stats_snapshot() {
  pncp_http GET "/api/pncp-research/local-index/stats" "" 30 2>/dev/null | python3 -c "
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
_days = int("${DAYS}")
_body = {
    "max_paginas": int("${MAX_PAGINAS}"),
    "tamanho_pagina": int("${TAMANHO}"),
    "uf": "${uf}",
    "codigo_municipio_ibge": None,
    "include_items": True,
}
if _days > 0:
    _body["days"] = _days
else:
    _body["months"] = int("${MONTHS}")
print(json.dumps(_body))
PY
)
  log "INGEST START uf=${uf} max_paginas=${MAX_PAGINAS} (timeout ${CURL_MAX_TIME}s — aguarde)"
  local json_log="${PNCP_INGEST_JSON_LOG:-${HOME}/pncp-ingest-responses.jsonl}"
  if pncp_http POST "/api/pncp-research/local-index/backfill" "${body}" "${CURL_MAX_TIME}" \
    >>"${json_log}" 2>&1; then
    log "INGEST OK uf=${uf}"
  else
    log "INGEST FAIL uf=${uf} (exit $?)"
  fi
  read -r tc ti <<<"$(stats_snapshot)"
  log "STATS após ${uf}: contratos=${tc} itens=${ti}"
}

if [[ "${PNCP_INGEST_VIA_DOCKER}" == "1" ]]; then
  log "PNCP ingest loop — via docker exec ${FEED_CONTAINER}:${FEED_PORT}"
else
  log "PNCP ingest loop — feed ${BASE_URL}"
fi
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
