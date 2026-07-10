#!/usr/bin/env bash
# Suíte de regressão: multi-fonte Parte 0 + melhorias PNCP (faixa, bulk, formatação).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/venv/bin/python"

echo "== Researcher: adapters + regressão federada =="
cd "$ROOT/pncp_researcher_service"
"$PY" -m pytest \
  tests/test_federated_adapters.py \
  tests/test_federated_regression.py \
  tests/test_pricing_faixa.py \
  tests/test_pricing_display.py \
  -k "not MarketSearchFaixaIntegrationTests" \
  -q

echo "== Researcher: bulk/lote e performance (recall/velocidade) =="
"$PY" -m pytest \
  tests/test_bulk_search_lote.py \
  tests/test_bulk_search_performance.py \
  -k "not BulkIntelligentPipelineFlagTests" \
  -q

echo "== Backend Django: plataforma + Art. 5º + geo =="
cd "$ROOT"
DJANGO_SETTINGS_MODULE=backend.mdlicitatech.settings "$PY" -m pytest \
  backend/app/tests/test_pncp_multi_source_regression.py \
  backend/app/tests/test_pncp_relatorio_localidade.py \
  backend/app/tests/test_pncp_relatorio_descricao_fonte.py \
  -q

echo "OK — regressão multi-fonte concluída."
