#!/usr/bin/env bash
# grafana-reset-dashboard v3 — exige layout-v29 no repo e copia JSON para o volume do contentor.
#
#   cd ~/docmaster-core
#   python3 scripts/build-grafana-dashboard.py
#   ./scripts/grafana-reset-dashboard.sh
#
# NÃO use ~/scripts/grafana-reset-dashboard.sh (cópia antiga sem v29).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="${DOCMASTER_ROOT:-$SCRIPT_DIR/..}"
REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
REQUIRED_LAYOUT_TAG="${GRAFANA_REQUIRED_LAYOUT:-layout-v30}"

if [[ "$SCRIPT_DIR" != *"docmaster-core"* ]]; then
  echo "ERRO: este script está em ${SCRIPT_DIR}"
  echo "Use o script DENTRO do repo (não uma cópia em ~/scripts/):"
  echo ""
  echo "  cd ~/docmaster-core"
  echo "  python3 scripts/build-grafana-dashboard.py"
  echo "  ./scripts/grafana-reset-dashboard.sh"
  echo ""
  exit 1
fi

GRAFANA_URL="${GRAFANA_URL:-http://127.0.0.1:3000}"
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASS="${GRAFANA_PASS:-changeme}"
DASH_UID="docmaster-backend"
REPO_DASH="${REPO_ROOT}/config/grafana/provisioning/dashboards/json/docmaster-backend.json"
BUILD_SCRIPT="${REPO_ROOT}/scripts/build-grafana-dashboard.py"

echo "Script:            ${SCRIPT_DIR}/$(basename "$0")"
echo "Repo:              ${REPO_ROOT}"
echo "JSON no repo:      ${REPO_DASH}"
echo "Layout exigido:    ${REQUIRED_LAYOUT_TAG}"
echo ""

if [[ ! -f "$REPO_DASH" ]]; then
  echo "ERRO: dashboard JSON ausente. Corra:"
  echo "  cd ${REPO_ROOT} && python3 scripts/build-grafana-dashboard.py"
  exit 1
fi

if ! grep -q "\"${REQUIRED_LAYOUT_TAG}\"" "$REPO_DASH"; then
  echo "ERRO: ${REPO_DASH} não contém tag ${REQUIRED_LAYOUT_TAG}."
  echo "  cd ${REPO_ROOT} && git pull && python3 scripts/build-grafana-dashboard.py"
  exit 1
fi

if ! grep -q 'clausulas_llm' "$REPO_DASH"; then
  echo "ERRO: JSON antigo (sem fluxo clausulas_llm). Corra build-grafana-dashboard.py após git pull."
  exit 1
fi

PROVISION_MOUNT=""
if docker inspect grafana >/dev/null 2>&1; then
  PROVISION_MOUNT="$(docker inspect grafana --format '{{range .Mounts}}{{if eq .Destination "/etc/grafana/provisioning"}}{{.Source}}{{end}}{{end}}')"
fi

LIVE_DASH=""
if [[ -n "$PROVISION_MOUNT" ]]; then
  LIVE_DASH="${PROVISION_MOUNT}/dashboards/json/docmaster-backend.json"
  echo "Grafana monta:     ${PROVISION_MOUNT}"
  echo "JSON no contentor: ${LIVE_DASH}"
fi
echo ""

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
echo ""

# Sempre sincronizar repo → pasta montada no contentor (evita ~/config preso em v26)
if [[ -n "$PROVISION_MOUNT" ]]; then
  echo "==> A copiar provisioning do repo para o volume do Grafana..."
  mkdir -p "${PROVISION_MOUNT}/dashboards/json" "${PROVISION_MOUNT}/datasources"
  if [[ -f "${REPO_ROOT}/config/grafana/provisioning/dashboards/default.yml" ]]; then
    cp -f "${REPO_ROOT}/config/grafana/provisioning/dashboards/default.yml" \
      "${PROVISION_MOUNT}/dashboards/default.yml"
  fi
  if [[ -f "${REPO_ROOT}/config/grafana/provisioning/datasources/prometheus.yml" ]]; then
    cp -f "${REPO_ROOT}/config/grafana/provisioning/datasources/prometheus.yml" \
      "${PROVISION_MOUNT}/datasources/prometheus.yml"
  fi
  cp -f "$REPO_DASH" "$LIVE_DASH"
  if ! grep -q "\"${REQUIRED_LAYOUT_TAG}\"" "$LIVE_DASH"; then
    echo "ERRO: cópia para ${LIVE_DASH} falhou — ainda sem ${REQUIRED_LAYOUT_TAG}"
    exit 1
  fi
  echo "    OK — $(basename "$LIVE_DASH") com ${REQUIRED_LAYOUT_TAG}"
fi

echo ""
echo "==> A apagar dashboard em cache (uid=${DASH_UID})..."
curl -sf -u "${GRAFANA_USER}:${GRAFANA_PASS}" -X DELETE \
  "${GRAFANA_URL}/api/dashboards/uid/${DASH_UID}" >/dev/null 2>&1 \
  && echo "    Removido da base Grafana." \
  || echo "    (ainda não existia na base — ok)"

echo ""
echo "==> A recriar contentor Grafana..."
(cd "$COMPOSE_DIR" && docker compose up -d --no-deps --force-recreate grafana)

echo "==> A aguardar Grafana..."
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  curl -sf "${GRAFANA_URL}/api/health" >/dev/null 2>&1 && break
  sleep 2
done

GRAFANA_DASH_TMP="$(mktemp "${TMPDIR:-/tmp}/grafana-dash-${USER:-user}.XXXXXX.json")"
chmod 600 "$GRAFANA_DASH_TMP"
trap 'rm -f "$GRAFANA_DASH_TMP"' EXIT

for _ in 1 2 3 4 5 6 7 8 9 10 12 13 14 15; do
  curl -sf -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
    "${GRAFANA_URL}/api/dashboards/uid/${DASH_UID}" >"$GRAFANA_DASH_TMP" 2>/dev/null && break
  sleep 2
done

VERIFY_OK=0
REQUIRED_TAG="$REQUIRED_LAYOUT_TAG" GRAFANA_DASH_TMP="$GRAFANA_DASH_TMP" python3 - <<'PY' || VERIFY_OK=1
import json
import os
import sys

required = os.environ.get("REQUIRED_TAG", "layout-v27")
path = os.environ.get("GRAFANA_DASH_TMP", "")
if not path or not os.path.isfile(path):
    sys.exit("ERRO: não foi possível ler a resposta da API Grafana.")

with open(path) as f:
    data = json.load(f)
d = data.get("dashboard") or data

tags = d.get("tags") or []
panels = d.get("panels") or []
rows = [p.get("title") for p in panels if p.get("type") == "row"]

print("Dashboard:", d.get("title"))
print("Tags:", tags)
print("Painéis:", len(panels))
print("Secções:", rows[:4])

if required not in tags:
    sys.exit(
        f"ERRO: Grafana ainda sem {required} (tags={tags}). "
        "Confirme: git pull, python3 scripts/build-grafana-dashboard.py, "
        "e use docmaster-core/scripts/grafana-reset-dashboard.sh (não cópia em ~/scripts)."
    )
if len(panels) < 60:
    sys.exit(f"ERRO: dashboard incompleto ({len(panels)} painéis).")
blob = json.dumps(panels)
if "clausulas_llm" not in blob:
    sys.exit("ERRO: painéis sem clausulas_llm — JSON provisionado ainda é antigo.")
print(f"\nOK — dashboard atualizado ({required}, {len(panels)} painéis).")
PY

if [[ "$VERIFY_OK" -ne 0 ]]; then
  echo ""
  echo "Diagnóstico rápido no servidor:"
  echo "  grep layout ${REPO_DASH} | tail -1"
  echo "  grep layout ${LIVE_DASH:-'(sem mount)'} 2>/dev/null | tail -1"
  echo ""
  echo "Se o repo já tem v27 mas o Grafana mostra v26, a pasta montada não era a do repo."
  echo "Este script agora copia sempre ${REPO_DASH} → volume do contentor antes do recreate."
  exit 1
fi

echo ""
echo "Abra: ${GRAFANA_URL}/d/${DASH_UID}"
echo "Tag esperada: ${REQUIRED_LAYOUT_TAG}"
