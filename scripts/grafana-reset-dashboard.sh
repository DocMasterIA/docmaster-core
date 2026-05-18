#!/usr/bin/env bash
# Remove o dashboard em cache no volume Grafana e reimporta o JSON provisionado.
set -euo pipefail
cd "$(dirname "$0")/.."

GRAFANA_URL="${GRAFANA_URL:-http://127.0.0.1:3000}"
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASS="${GRAFANA_PASS:-changeme}"
DASH_UID="docmaster-backend"

echo "==> A apagar dashboard em cache (uid=${DASH_UID})..."
curl -sf -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
  -X DELETE "${GRAFANA_URL}/api/dashboards/uid/${DASH_UID}" \
  || echo "    (ainda não existia na base — ok)"

echo "==> A reiniciar Grafana..."
docker compose restart grafana

echo "==> A aguardar provisionamento..."
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sf -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
    "${GRAFANA_URL}/api/dashboards/uid/${DASH_UID}" >/tmp/grafana-dash.json 2>/dev/null; then
    break
  fi
  sleep 2
done

python3 - <<'PY'
import json
with open("/tmp/grafana-dash.json") as f:
    d = json.load(f)["dashboard"]
rows = [p["title"] for p in d.get("panels", []) if p.get("type") == "row"]
tags = d.get("tags", [])
print("Dashboard:", d.get("title"))
print("Tags:", tags)
print("Primeiras secções:", rows[:3])
if not any("Layout v6" in r for r in rows):
    raise SystemExit("ERRO: layout antigo — confirme git pull e o ficheiro em config/grafana/provisioning/")
print("OK — layout v6 activo.")
PY

echo ""
echo "Abra: ${GRAFANA_URL}/d/${DASH_UID}/docmaster-backend"
echo "Pasta: DocMaster → DocMaster — Backend Django"
