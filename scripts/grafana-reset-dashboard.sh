#!/usr/bin/env bash
# Atualiza dashboard DocMaster no Grafana (provisioning + API).
#
# VPS: compose e config/ na pasta de deploy (cópia do repo), não precisa de clone git no servidor.
# PC:  GRAFANA_SKIP_COMPOSE=1 ./scripts/grafana-reset-dashboard.sh
#      (defaults: https://api.docmasteria.com.br/grafana/)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${DOCMASTER_ROOT:-$SCRIPT_DIR/..}" && pwd)"
REQUIRED_LAYOUT_TAG="${GRAFANA_REQUIRED_LAYOUT:-layout-v42-tokens}"

GRAFANA_URL="${GRAFANA_URL:-http://127.0.0.1:3000}"
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASS="${GRAFANA_PASS:-changeme}"
DASH_UID="docmaster-backend"
REPO_DASH="${REPO_ROOT}/config/grafana/provisioning/dashboards/json/docmaster-backend.json"
BUILD_SCRIPT="${REPO_ROOT}/scripts/build-grafana-dashboard.py"

# Pasta onde o docker-compose.yml da VPS/ambiente está (default: detecta pelo contentor grafana).
DEPLOY_DIR="${DOCMASTER_DEPLOY_DIR:-}"
if [[ -z "$DEPLOY_DIR" ]] && docker inspect grafana >/dev/null 2>&1; then
  DEPLOY_DIR="$(docker inspect grafana --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}' 2>/dev/null || true)"
fi
DEPLOY_DIR="${DEPLOY_DIR:-$REPO_ROOT}"
DEPLOY_DIR="$(cd "$DEPLOY_DIR" 2>/dev/null && pwd || echo "$DEPLOY_DIR")"
EXPECTED_PROVISION="${DEPLOY_DIR}/config/grafana/provisioning"
COMPOSE_FILE="${DOCMASTER_COMPOSE_FILE:-${DEPLOY_DIR}/docker-compose.yml}"

_grafana_local() {
  case "$GRAFANA_URL" in
    http://127.0.0.1:*|http://localhost:*|http://[::1]:*|https://127.0.0.1:*|https://localhost:*) return 0 ;;
    *) return 1 ;;
  esac
}

SKIP_COMPOSE="${GRAFANA_SKIP_COMPOSE:-}"
if [[ -z "$SKIP_COMPOSE" ]]; then
  if _grafana_local; then
    SKIP_COMPOSE=0
  else
    SKIP_COMPOSE=1
  fi
fi

# host.docker.internal:9090 → 172.17.0.1 no Linux; Prometheus publica 127.0.0.1:9090 no host → connection refused.
PROM_PUBLIC_URL="${GRAFANA_PROMETHEUS_URL:-http://prometheus:9090}"

echo "Script:            ${SCRIPT_DIR}/$(basename "$0")"
echo "Repo (JSON):       ${REPO_ROOT}"
echo "Deploy (compose):  ${DEPLOY_DIR}"
echo "Grafana:           ${GRAFANA_URL}"
echo "Skip compose:      ${SKIP_COMPOSE}"
echo "Layout exigido:    ${REQUIRED_LAYOUT_TAG}"
echo ""

if [[ ! -f "$REPO_DASH" ]]; then
  echo "ERRO: dashboard JSON ausente. Corra:"
  echo "  python3 ${BUILD_SCRIPT}"
  exit 1
fi

if ! grep -q "\"${REQUIRED_LAYOUT_TAG}\"" "$REPO_DASH"; then
  echo "ERRO: ${REPO_DASH} sem tag ${REQUIRED_LAYOUT_TAG}. Corra: python3 ${BUILD_SCRIPT}"
  exit 1
fi

PROVISION_MOUNT=""
if docker inspect grafana >/dev/null 2>&1; then
  PROVISION_MOUNT="$(docker inspect grafana --format '{{range .Mounts}}{{if eq .Destination "/etc/grafana/provisioning"}}{{.Source}}{{end}}{{end}}')"
fi

if [[ "$SKIP_COMPOSE" == "0" && -f "$COMPOSE_FILE" ]]; then
  COMPOSE=(docker compose -f "$COMPOSE_FILE")
  if [[ -n "$PROVISION_MOUNT" ]]; then
    norm_mount="$(readlink -f "$PROVISION_MOUNT" 2>/dev/null || echo "$PROVISION_MOUNT")"
    norm_expected="$(readlink -f "$EXPECTED_PROVISION" 2>/dev/null || echo "$EXPECTED_PROVISION")"
    if [[ "$norm_mount" != "$norm_expected" ]]; then
      echo "==> Mount de provisioning diferente de ${EXPECTED_PROVISION}"
      echo "    Recriando Grafana a partir de ${DEPLOY_DIR}..."
      docker rm -f grafana 2>/dev/null || true
      PROVISION_MOUNT=""
    fi
  fi

  if [[ -n "$PROVISION_MOUNT" && "$PROVISION_MOUNT" != "${EXPECTED_PROVISION}"* ]]; then
    echo "==> A sincronizar provisioning → ${PROVISION_MOUNT}"
    mkdir -p "${PROVISION_MOUNT}/dashboards/json" "${PROVISION_MOUNT}/datasources"
    for pair in dashboards/default.yml datasources/prometheus.yml dashboards/json/docmaster-backend.json; do
      src="${REPO_ROOT}/config/grafana/provisioning/${pair}"
      [[ -f "$src" ]] || continue
      cp -f "$src" "${PROVISION_MOUNT}/${pair}" || {
        echo "ERRO: cp falhou (permissões?). Na VPS: copie config/grafana para ${DEPLOY_DIR}/config/ e:"
        echo "  cd ${DEPLOY_DIR} && docker compose up -d --force-recreate grafana"
        exit 1
      }
    done
  fi

  echo "==> docker compose (${COMPOSE_FILE}) — recreate grafana"
  "${COMPOSE[@]}" up -d --no-deps --force-recreate grafana

  if docker container inspect prometheus >/dev/null 2>&1; then
    net="$(docker inspect prometheus --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' | awk '{print $1}')"
    [[ -n "$net" ]] && docker network connect "$net" grafana 2>/dev/null || true
  fi
elif [[ "$SKIP_COMPOSE" == "1" ]]; then
  echo "==> Modo remoto: sem docker compose nesta máquina (só API Grafana)."
fi

echo ""
echo "==> Datasource Prometheus → ${PROM_PUBLIC_URL}"
DS_ID="$(curl -sf -u "${GRAFANA_USER}:${GRAFANA_PASS}" "${GRAFANA_URL}/api/datasources/uid/prometheus" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || true)"
if [[ -n "$DS_ID" ]]; then
  curl -sf -u "${GRAFANA_USER}:${GRAFANA_PASS}" -X PUT \
    "${GRAFANA_URL}/api/datasources/${DS_ID}" \
    -H 'Content-Type: application/json' \
    -d '{"id":'"${DS_ID}"',"uid":"prometheus","orgId":1,"name":"Prometheus","type":"prometheus","access":"proxy","url":"'"${PROM_PUBLIC_URL}"'","isDefault":true,"jsonData":{}}' >/dev/null || true
  sleep 1
fi

DS_HEALTH="$(curl -sf -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
  "${GRAFANA_URL}/api/datasources/uid/prometheus/health" 2>/dev/null || echo '{}')"
echo "$DS_HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print('   status:', d.get('status','?'), d.get('message','')[:120])" 2>/dev/null || echo "   (sem resposta — credenciais?)"

if echo "$DS_HEALTH" | grep -q '"status":"ERROR"'; then
  echo "==> Datasource com erro — a testar URLs alternativas..."
  DS_ID="$(curl -sf -u "${GRAFANA_USER}:${GRAFANA_PASS}" "${GRAFANA_URL}/api/datasources/uid/prometheus" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")"
  PROM_URLS=("$PROM_PUBLIC_URL")
  GRAFANA_HOST="$(python3 -c "from urllib.parse import urlparse; print(urlparse('${GRAFANA_URL}').hostname or '')")"
  if [[ -n "$GRAFANA_HOST" && "$GRAFANA_HOST" != "127.0.0.1" && "$GRAFANA_HOST" != "localhost" ]]; then
    PROM_URLS+=("https://${GRAFANA_HOST}/prometheus" "http://${GRAFANA_HOST}:9090")
  fi
  PROM_URLS+=("http://127.0.0.1:9090" "http://prometheus:9090")
  for prom_url in "${PROM_URLS[@]}"; do
    echo "    tentativa: ${prom_url}"
    curl -sf -u "${GRAFANA_USER}:${GRAFANA_PASS}" -X PUT \
      "${GRAFANA_URL}/api/datasources/${DS_ID}" \
      -H 'Content-Type: application/json' \
      -d '{"id":'"${DS_ID}"',"uid":"prometheus","orgId":1,"name":"Prometheus","type":"prometheus","access":"proxy","url":"'"${prom_url}"'","isDefault":true,"jsonData":{}}' >/dev/null || continue
    sleep 1
    DS_HEALTH="$(curl -sf -u "${GRAFANA_USER}:${GRAFANA_PASS}" "${GRAFANA_URL}/api/datasources/uid/prometheus/health" || echo '{}')"
    if echo "$DS_HEALTH" | grep -q '"status":"OK"'; then
      echo "    OK — ${prom_url}"
      break
    fi
  done
fi

echo ""
echo "==> A remover dashboard em cache (uid=${DASH_UID})..."
curl -sf -u "${GRAFANA_USER}:${GRAFANA_PASS}" -X DELETE \
  "${GRAFANA_URL}/api/dashboards/uid/${DASH_UID}" >/dev/null 2>&1 || true

echo "==> A importar JSON do repo (se não for só provisioning)..."
IMPORT_ERR="$(python3 - "$REPO_DASH" <<'PY' 2>&1 || true
import base64, json, sys, urllib.error, urllib.request

path = sys.argv[1]
with open(path) as f:
    dash = json.load(f)
dash["id"] = None
payload = json.dumps({"dashboard": dash, "overwrite": True, "message": "grafana-reset-dashboard"}).encode()
user, password = "admin", "changeme"
import os
user = os.environ.get("GRAFANA_USER", user)
password = os.environ.get("GRAFANA_PASS", password)
url = os.environ.get("GRAFANA_URL", "http://127.0.0.1:3000").rstrip("/") + "/api/dashboards/db"
auth = base64.b64encode(f"{user}:{password}".encode()).decode()
req = urllib.request.Request(
    url, data=payload, method="POST",
    headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"},
)
try:
    with urllib.request.urlopen(req) as r:
        print("import_ok", r.status)
except urllib.error.HTTPError as e:
    body = e.read().decode(errors="replace")
    if "provisioned" in body.lower():
        print("provisioned_skip")
    else:
        print("import_fail", e.code, body[:200])
        sys.exit(1)
PY
)"
echo "$IMPORT_ERR" | sed 's/^/    /'
if echo "$IMPORT_ERR" | grep -q provisioned_skip; then
  echo "    Dashboard vem de ficheiro em config/grafana/ — copie para DEPLOY na VPS e:"
  echo "      cd DEPLOY && docker compose restart grafana"
fi

echo "==> A aguardar Grafana..."
for _ in $(seq 1 15); do
  curl -sf "${GRAFANA_URL}/api/health" >/dev/null 2>&1 && break
  sleep 2
done

GRAFANA_DASH_TMP="$(mktemp "${TMPDIR:-/tmp}/grafana-dash.XXXXXX.json")"
chmod 600 "$GRAFANA_DASH_TMP"
trap 'rm -f "$GRAFANA_DASH_TMP"' EXIT

curl -sf -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
  "${GRAFANA_URL}/api/dashboards/uid/${DASH_UID}" >"$GRAFANA_DASH_TMP"

REQUIRED_TAG="$REQUIRED_LAYOUT_TAG" GRAFANA_DASH_TMP="$GRAFANA_DASH_TMP" python3 - <<'PY'
import json, os, sys
required = os.environ["REQUIRED_TAG"]
with open(os.environ["GRAFANA_DASH_TMP"]) as f:
    d = json.load(f).get("dashboard") or {}
tags = d.get("tags") or []
panels = d.get("panels") or []
if required not in tags:
    sys.exit(f"ERRO: tags={tags}, esperado {required}")
if len(panels) < 14:
    sys.exit(f"ERRO: só {len(panels)} painéis")
if "node_memory_MemAvailable_bytes" not in json.dumps(panels):
    sys.exit("ERRO: sem queries node_exporter")
if "docmaster_llm_tokens_total" not in json.dumps(panels):
    sys.exit("ERRO: sem docmaster_llm_tokens_total — corra build-grafana-dashboard.py")
print(f"OK — {len(panels)} painéis, tags={tags}")
PY

echo ""
echo "Abra: ${GRAFANA_URL%/}/d/${DASH_UID}"
echo "Prometheus: ${PROM_PUBLIC_URL%/}/"
echo "Datasource: ${GRAFANA_URL}/connections/datasources"
