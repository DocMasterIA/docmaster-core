#!/usr/bin/env bash
# Suite de testes PNCP researcher (busca lote, fornecedor, enrich, pricing).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../pncp_researcher_service" && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"
if [[ -d "$ROOT/venv/bin" ]]; then
  PY="$ROOT/venv/bin/python"
elif [[ -d "$ROOT/../venv/bin" ]]; then
  PY="$ROOT/../venv/bin/python"
fi

if ! "$PY" -c "import pydantic" 2>/dev/null; then
  echo "Instalando dependências de teste em venv local..."
  "$PY" -m venv "$ROOT/.test-venv"
  PY="$ROOT/.test-venv/bin/python"
  "$PY" -m pip install -q -r "$ROOT/requirements.txt"
fi

echo "== PNCP researcher tests =="
"$PY" -m unittest discover -s tests -p 'test_catalog_metadata_sync.py' -v
"$PY" -m unittest discover -s tests -p 'test_bulk_search*.py' -v
"$PY" -m unittest discover -s tests -p 'test_local_search_display_filter.py' -v
"$PY" -m unittest discover -s tests -p 'test_search_enrich_async.py' -v
"$PY" -m unittest discover -s tests -p 'test_pricing_display.py' -v
"$PY" -m unittest discover -s tests -p 'test_supplier_resolver.py' -v

FRONT="$SCRIPT_DIR/../frontend-vue"
if command -v node >/dev/null 2>&1; then
  echo "== Frontend utils tests (pncpPricing) =="
  (cd "$FRONT" && node --test src/utils/pncpBulkFlow.node.test.mjs)
else
  echo "AVISO: node não encontrado — pulando testes frontend"
fi

echo "OK  todos os testes passaram"
