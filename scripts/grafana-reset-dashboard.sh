#!/usr/bin/env bash
# Força o Grafana a recarregar o dashboard provisionado.
# Funciona com docker compose na raiz do projeto OU stack em ~/ com config separado.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="${DOCMASTER_ROOT:-$SCRIPT_DIR/..}"
REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"

GRAFANA_URL="${GRAFANA_URL:-http://127.0.0.1:3000}"
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASS="${GRAFANA_PASS:-changeme}"
DASH_UID="docmaster-backend"
REPO_DASH="${REPO_ROOT}/config/grafana/provisioning/dashboards/json/docmaster-backend.json"

# Caminho que o contentor Grafana monta (pode ser ~/config, não ~/docmaster-core/config)
PROVISION_MOUNT=""
if docker inspect grafana >/dev/null 2>&1; then
  PROVISION_MOUNT="$(docker inspect grafana --format '{{range .Mounts}}{{if eq .Destination "/etc/grafana/provisioning"}}{{.Source}}{{end}}{{end}}')"
fi

LIVE_DASH=""
if [[ -n "$PROVISION_MOUNT" ]]; then
  LIVE_DASH="${PROVISION_MOUNT}/dashboards/json/docmaster-backend.json"
fi

echo "Repo:              ${REPO_ROOT}"
echo "JSON no repo:      ${REPO_DASH}"
[[ -n "$PROVISION_MOUNT" ]] && echo "Grafana monta:     ${PROVISION_MOUNT}"
[[ -n "$LIVE_DASH" ]] && echo "JSON no contentor: ${LIVE_DASH}"
echo ""

if [[ ! -f "$REPO_DASH" ]]; then
  echo "ERRO: não encontrei o dashboard no repo."
  exit 1
fi

if ! grep -qE 'layout-v(6|7|8|9|10|11|12|13|14|15|16|17|18|19|20|21|22)' "$REPO_DASH"; then
  echo "ERRO: JSON no repo desatualizado. Faça git pull em ${REPO_ROOT}"
  exit 1
fi

# Diretório onde corre docker compose (label ou cwd do contentor)
COMPOSE_DIR="${DOCMASTER_COMPOSE_DIR:-}"
if [[ -z "$COMPOSE_DIR" ]] && docker inspect grafana >/dev/null 2>&1; then
  COMPOSE_DIR="$(docker inspect grafana --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}' 2>/dev/null || true)"
fi
if [[ -z "$COMPOSE_DIR" || ! -f "${COMPOSE_DIR}/docker-compose.yml" ]]; then
  if [[ -f "${REPO_ROOT}/docker-compose.yml" ]]; then
    COMPOSE_DIR="$REPO_ROOT"
  elif [[ -f "${HOME}/docker-compose.yml" ]]; then
    COMPOSE_DIR="$HOME"
  else
    COMPOSE_DIR="$REPO_ROOT"
  fi
fi

echo "Docker Compose em: ${COMPOSE_DIR}"

# Sincronizar provisioning do repo → pasta que o Grafana realmente lê
if [[ -n "$PROVISION_MOUNT" && "$PROVISION_MOUNT" != "${REPO_ROOT}/config/grafana/provisioning" ]]; then
  echo ""
  echo "==> A copiar config Grafana do repo para a pasta do contentor..."
  mkdir -p "${PROVISION_MOUNT}/dashboards/json" "${PROVISION_MOUNT}/datasources"
  cp -f "${REPO_ROOT}/config/grafana/provisioning/dashboards/default.yml" \
    "${PROVISION_MOUNT}/dashboards/default.yml"
  cp -f "$REPO_DASH" "$LIVE_DASH"
  if [[ -f "${REPO_ROOT}/config/grafana/provisioning/datasources/prometheus.yml" ]]; then
    cp -f "${REPO_ROOT}/config/grafana/provisioning/datasources/prometheus.yml" \
      "${PROVISION_MOUNT}/datasources/prometheus.yml"
  fi
  if grep -qE 'layout-v(6|7|8|9|10|11|12|13|14|15|16|17|18|19|20|21|22)' "$LIVE_DASH"; then
    echo "    Copiado OK ($(basename "$LIVE_DASH"))"
  else
    echo "ERRO: cópia falhou — ${LIVE_DASH} ainda desatualizado"
    exit 1
  fi
elif [[ -f "$LIVE_DASH" ]] && ! grep -qE 'layout-v(6|7|8|9|10|11|12|13)' "$LIVE_DASH"; then
  echo "ERRO: ${LIVE_DASH} está antigo e não é o mesmo path do repo."
  echo "Copie manualmente:"
  echo "  mkdir -p $(dirname "$LIVE_DASH")"
  echo "  cp -f ${REPO_DASH} ${LIVE_DASH}"
  exit 1
fi

echo ""
echo "==> A recriar contentor Grafana..."
(cd "$COMPOSE_DIR" && docker compose up -d --no-deps --force-recreate grafana)

echo "==> A aguardar Grafana..."
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  curl -sf "${GRAFANA_URL}/api/health" >/dev/null 2>&1 && break
  sleep 2
done

for _ in 1 2 3 4 5 6 7 8 9 10; do
  curl -sf -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
    "${GRAFANA_URL}/api/dashboards/uid/${DASH_UID}" >/tmp/grafana-dash.json 2>/dev/null && break
  sleep 2
done

VERIFY_OK=0
python3 - <<'PY' || VERIFY_OK=1
import json
import sys

with open("/tmp/grafana-dash.json") as f:
    data = json.load(f)
d = data.get("dashboard") or data

tags = d.get("tags") or []
panels = d.get("panels") or []
rows = [p.get("title") for p in panels if p.get("type") == "row"]

print("Dashboard:", d.get("title"))
print("Tags:", tags)
print("Painéis:", len(panels))
print("Secções:", rows[:3])

if not any(t in tags for t in ("layout-v6", "layout-v7", "layout-v8", "layout-v9", "layout-v10", "layout-v11", "layout-v12", "layout-v13", "layout-v14", "layout-v15", "layout-v16", "layout-v17", "layout-v18", "layout-v19", "layout-v20", "layout-v22")):
    sys.exit("ERRO: Grafana ainda sem layout novo (layout-v22).")
if len(panels) < 10:
    sys.exit("ERRO: dashboard incompleto.")
print("\nOK — dashboard atualizado (layout-v22).")
PY

if [[ "$VERIFY_OK" -ne 0 ]]; then
  echo ""
  echo "Último recurso (apaga utilizadores/dashboards guardados no volume):"
  echo "  cd ${COMPOSE_DIR}"
  echo "  docker compose stop grafana && docker rm grafana"
  echo "  docker volume ls | grep grafana"
  echo "  docker volume rm <nome_do_volume_grafana_data>"
  echo "  docker compose up -d grafana"
  echo "  DOCMASTER_ROOT=${REPO_ROOT} $0"
  exit 1
fi

echo ""
echo "Abra: ${GRAFANA_URL}/d/${DASH_UID}"
echo "Tokens LLM — média por operação — layout-v22"
