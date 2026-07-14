#!/usr/bin/env bash
# Suíte de regressão — adaptação multi-plataforma (feeds + Camada B + TCE-RS + federado).
# Uso:
#   ./scripts/run-price-platform-regression.sh
#   ./scripts/run-price-platform-regression.sh -q
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SVC="$ROOT/pncp_researcher_service"
cd "$SVC"

if [[ -f "$ROOT/venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/venv/bin/activate"
fi

export PYTHONPATH="$SVC${PYTHONPATH:+:$PYTHONPATH}"

PYTEST_ARGS=("$@")
if [[ ${#PYTEST_ARGS[@]} -eq 0 ]]; then
  PYTEST_ARGS=(-v --tb=short)
fi

echo "==> Suíte multi-plataforma (cwd=$SVC)"
echo "    feeds isolados | Camada B | TCE-RS ingest | federado | crosslink | faixa"
python -m pytest \
  tests/test_feed_platform_isolation.py \
  tests/test_orchestrator_camada_b.py \
  tests/test_tce_rs_ingest.py \
  tests/test_federated_item_totals.py \
  tests/test_federated_adapters.py \
  tests/test_federated_regression.py \
  tests/test_platform_index_crosslink.py \
  tests/test_pricing_faixa.py::PricingFaixaTests \
  tests/test_pricing_faixa.py::ManualParityFaixaTests \
  -k "not raw_" \
  "${PYTEST_ARGS[@]}"

echo ""
echo "OK — regressão multi-plataforma passou."
