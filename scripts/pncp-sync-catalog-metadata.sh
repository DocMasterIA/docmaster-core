#!/usr/bin/env bash
# Materializa situacao_item/fornecedor_elegivel do raw_json e mostra fila de /resultados pendente.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../pncp_researcher_service" && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"
if [[ -d "$ROOT/venv/bin" ]]; then
  PY="$ROOT/venv/bin/python"
fi

DB="${PNCP_LOCAL_DB_PATH:-/home/adryan/pncp_researcher_local.db}"
BATCH="${1:-25000}"
BATCHES="${2:-1}"

export PNCP_LOCAL_DB_PATH="$DB"

echo "== sync catalog metadata =="
echo "DB: $PNCP_LOCAL_DB_PATH"
"$PY" - <<PY
import os
from app import local_index
from app.config import PNCP_LOCAL_DB_PATH

print("db:", PNCP_LOCAL_DB_PATH)
print("needs metadata sync:", local_index.count_items_needing_catalog_metadata_sync())
print("contracts needing /resultados:", local_index.count_contracts_needing_resultados())
out = local_index.sync_catalog_metadata_from_raw_json(
    batch_size=int("${BATCH}"),
    max_batches=int("${BATCHES}"),
)
print("sync:", out)
cov = local_index.supplier_coverage_stats()
print(
    "cobertura fornecedor:",
    f"cnpj={cov['itens_com_cnpj_fornecedor']}/{cov['total_itens']}",
    f"nome={cov['itens_com_nome_fornecedor']}/{cov['total_itens']}",
)
print("contracts needing /resultados (apos sync):", local_index.count_contracts_needing_resultados())
PY

echo
echo "Próximo passo: worker ingest enfileira GET /resultados automaticamente."
echo "Para acelerar: reinicie pncp-ingest-worker ou POST /local-index/sync-catalog-metadata"
