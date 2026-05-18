#!/usr/bin/env bash
# Força o Grafana a reler o dashboard provisionado (ficheiro JSON no repo).
# Dashboards provisionados NÃO podem ser apagados/importados pela API.
set -euo pipefail
cd "$(dirname "$0")/.."

GRAFANA_URL="${GRAFANA_URL:-http://127.0.0.1:3000}"
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASS="${GRAFANA_PASS:-changeme}"
DASH_UID="docmaster-backend"
DASH_FILE="config/grafana/provisioning/dashboards/json/docmaster-backend.json"

if [[ ! -f "$DASH_FILE" ]]; then
  echo "ERRO: não encontrei ${DASH_FILE}"
  exit 1
fi

if ! grep -q 'layout-v6' "$DASH_FILE"; then
  echo "ERRO: o JSON local está ANTIGO (sem tag layout-v6)."
  echo ""
  echo "Corra primeiro:"
  echo "  cd ~/docmaster-core   # ou o caminho do clone no servidor"
  echo "  git fetch origin main && git pull origin main"
  echo "  grep layout-v6 ${DASH_FILE} && echo 'ficheiro OK'"
  echo ""
  echo "Só depois: ./scripts/grafana-reset-dashboard.sh"
  exit 1
fi

echo "==> Ficheiro local OK ($(grep -o '"version": [0-9]*' "$DASH_FILE" | head -1), tag layout-v6)"

echo "==> A recriar contentor Grafana (relê provisioning + overwrite)..."
docker compose up -d --no-deps --force-recreate grafana

echo "==> A aguardar Grafana..."
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  if curl -sf "${GRAFANA_URL}/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sf -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
    "${GRAFANA_URL}/api/dashboards/uid/${DASH_UID}" >/tmp/grafana-dash.json 2>/dev/null; then
    break
  fi
  sleep 2
done

VERIFY_OK=0
python3 - <<'PY' || VERIFY_OK=1
import json
import sys

with open("/tmp/grafana-dash.json") as f:
    data = json.load(f)
d = data.get("dashboard") or data
meta = data.get("meta") or {}

tags = d.get("tags") or []
panels = d.get("panels") or []
rows = [p.get("title") for p in panels if p.get("type") == "row"]
titles = [p.get("title") for p in panels if p.get("type") != "row"][:5]

print("Dashboard:", d.get("title"))
print("Provisionado:", meta.get("provisioned"))
print("Tags:", tags)
print("Painéis:", len(panels))
print("Secções:", rows[:3])
print("Exemplos:", titles)

if "layout-v6" not in tags:
    print("\nO Grafana ainda não tem o layout novo.", file=sys.stderr)
    sys.exit(1)
if not any("Layout v6" in (r or "") for r in rows):
    print("\nSecções sem 'Layout v6' — JSON no contentor pode estar desatualizado.", file=sys.stderr)
    sys.exit(1)
print("\nOK — layout v6 activo.")
PY

if [[ "$VERIFY_OK" -ne 0 ]]; then
  echo ""
  echo "O volume grafana_data pode ter bloqueado o overwrite. Último recurso:"
  echo "  docker compose stop grafana"
  echo "  docker rm grafana"
  echo "  docker volume rm \$(docker volume ls -q | grep grafana_data)"
  echo "  docker compose up -d grafana"
  echo "  ./scripts/grafana-reset-dashboard.sh"
  exit 1
fi

echo ""
echo "Abra: ${GRAFANA_URL}/d/${DASH_UID}"
echo "Primeira secção deve ser: «Layout v6 — Visão geral — tráfego HTTP»"
