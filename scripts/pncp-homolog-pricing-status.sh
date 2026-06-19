#!/usr/bin/env bash
# Cobertura de preço homologado no índice PNCP local (SQLite).
# Uso na VPS (SSH):
#   ./scripts/pncp-homolog-pricing-status.sh
#   DOCMASTER_DEPLOY_DIR=/home/docmaster ./scripts/pncp-homolog-pricing-status.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY="${DOCMASTER_DEPLOY_DIR:-$SCRIPT_DIR/..}"
DEPLOY="$(cd "$DEPLOY" && pwd)"
COMPOSE_FILE="${DOCMASTER_PNCP_COMPOSE_FILE:-$DEPLOY/docker-compose.pncp.yml}"
CONTAINER="${PNCP_CONTAINER:-pncp_researcher_service}"
DB_PATH="${PNCP_LOCAL_DB_PATH:-/data/pncp/pncp_researcher_local.db}"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "ERRO: container $CONTAINER não está Up." >&2
  docker ps --format 'table {{.Names}}\t{{.Status}}' | head -15
  exit 1
fi

echo "=== PNCP homologado — $(date -Iseconds) ==="
echo "container=$CONTAINER db=$DB_PATH"
echo

echo "--- API (stats + coverage) ---"
docker exec "$CONTAINER" python - <<'PY'
import json
import urllib.request

def get(path):
    with urllib.request.urlopen(f"http://127.0.0.1:8012/api/pncp-research/{path}", timeout=60) as r:
        return json.loads(r.read().decode())

try:
    stats = get("local-index/stats")
    idx = stats.get("index") or stats
    print(f"total_itens: {idx.get('total_itens') or stats.get('total_itens')}")
    print(f"total_contratos: {idx.get('total_contratos') or stats.get('total_contratos')}")
    forn = stats.get("fornecedor") or (idx.get("fornecedor") if isinstance(idx, dict) else {}) or {}
    if forn:
        print(f"fornecedor_elegiveis: {forn.get('itens_elegiveis')}")
        print(f"fornecedor_cnpj_pct: {forn.get('cobertura_cnpj_pct')}%")
except Exception as e:
    print(f"stats: ERRO {e}")

try:
    cov = get("local-index/coverage")
    q = cov.get("queue") or {}
    rt = cov.get("runtime") or {}
    print(f"backfill_mode: {cov.get('backfill_mode')}")
    print(f"fila_pending: {q.get('pending')} processing: {q.get('processing')}")
    print(f"contratos_sem_itens: {(cov.get('gaps') or {}).get('contratos_sem_itens')}")
    if rt:
        print(f"item_rows_1h: {rt.get('item_rows_1h')} items_ok_1h: {rt.get('items_ok_1h')}")
        print(f"ingest_stalled: {rt.get('stalled')} items_stalled: {rt.get('items_stalled')}")
except Exception as e:
    print(f"coverage: ERRO {e}")
PY

echo
echo "--- SQLite (preço homologado) ---"
docker exec "$CONTAINER" python - "$DB_PATH" <<'PY'
import sqlite3
import sys

db = sys.argv[1]
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
c = conn.cursor()

def one(sql, params=()):
    return c.execute(sql, params).fetchone()

def pct(num, den):
    if not den:
        return 0.0
    return round(100.0 * num / den, 2)

total = int(one("SELECT COUNT(*) AS n FROM pncp_itens")["n"])
com_homolog_vu = int(
    one("SELECT COUNT(*) AS n FROM pncp_itens WHERE valor_unitario_homologado IS NOT NULL")["n"]
)
com_homolog_any = int(
    one(
        """
        SELECT COUNT(*) AS n FROM pncp_itens
        WHERE valor_unitario_homologado IS NOT NULL
           OR valor_total_homologado IS NOT NULL
           OR quantidade_homologada IS NOT NULL
        """
    )["n"]
)
elegiveis = int(
    one(
        """
        SELECT COUNT(*) AS n FROM pncp_itens
        WHERE fornecedor_elegivel = 1
           OR LOWER(COALESCE(situacao_item, '')) LIKE '%homolog%'
           OR LOWER(COALESCE(situacao_item, '')) LIKE '%adjudic%'
        """
    )["n"]
)
elegiveis_sem_homolog = int(
    one(
        """
        SELECT COUNT(*) AS n FROM pncp_itens
        WHERE valor_unitario_homologado IS NULL
          AND (
                fornecedor_elegivel = 1
             OR LOWER(COALESCE(situacao_item, '')) LIKE '%homolog%'
             OR LOWER(COALESCE(situacao_item, '')) LIKE '%adjudic%'
          )
        """
    )["n"]
)
contratos_backlog = int(
    one(
        """
        SELECT COUNT(DISTINCT numero_pncp) AS n FROM pncp_itens
        WHERE valor_unitario_homologado IS NULL
          AND (
                fornecedor_elegivel = 1
             OR LOWER(COALESCE(situacao_item, '')) LIKE '%homolog%'
             OR LOWER(COALESCE(situacao_item, '')) LIKE '%adjudic%'
          )
        """
    )["n"]
)
resolvido_at = int(
    one("SELECT COUNT(*) AS n FROM pncp_itens WHERE resultado_resolvido_at IS NOT NULL")["n"]
)

print(f"total_itens: {total:,}".replace(",", "."))
print(f"com valor_unitario_homologado: {com_homolog_vu:,} ({pct(com_homolog_vu, total)}%)".replace(",", "."))
print(f"com qualquer campo homologado: {com_homolog_any:,} ({pct(com_homolog_any, total)}%)".replace(",", "."))
print(f"itens elegíveis (homolog/adjudic/elegível): {elegiveis:,}".replace(",", "."))
print(
    f"elegíveis SEM preço homologado: {elegiveis_sem_homolog:,} "
    f"({pct(elegiveis_sem_homolog, elegiveis)}% do pool elegível)".replace(",", ".")
)
print(f"contratos distintos na fila lógica /resultados: {contratos_backlog:,}".replace(",", "."))
print(f"resultado_resolvido_at preenchido: {resolvido_at:,}".replace(",", "."))

row = one(
    """
    SELECT
      SUM(CASE WHEN valor_unitario_homologado IS NOT NULL THEN 1 ELSE 0 END) AS ok,
      COUNT(*) AS n
    FROM pncp_itens
    WHERE fornecedor_elegivel = 1
    """
)
if row and row["n"]:
    print(
        f"fornecedor_elegivel=1 com vu_homologado: {int(row['ok']):,} / {int(row['n']):,} "
        f"({pct(int(row['ok']), int(row['n']))}%)".replace(",", ".")
    )

print("\n--- amostra elegível sem homologado (5 mais recentes) ---")
for r in c.execute(
    """
    SELECT numero_pncp, numero_item, situacao_item, valor_unitario, valor_unitario_estimado, updated_at
    FROM pncp_itens
    WHERE valor_unitario_homologado IS NULL
      AND (
            fornecedor_elegivel = 1
         OR LOWER(COALESCE(situacao_item, '')) LIKE '%homolog%'
         OR LOWER(COALESCE(situacao_item, '')) LIKE '%adjudic%'
      )
    ORDER BY updated_at DESC
    LIMIT 5
    """
):
    print(
        f"  {r['numero_pncp']} item={r['numero_item']} sit={r['situacao_item'] or '-'} "
        f"vu_est={r['valor_unitario_estimado'] or r['valor_unitario']} upd={r['updated_at']}"
    )

conn.close()
PY

echo
echo "--- ingest heartbeat (últimas linhas) ---"
docker logs "$CONTAINER" --tail 8 2>&1 | grep -E 'heartbeat|resultados-only|topup resultados' || docker logs "$CONTAINER" --tail 5 2>&1
