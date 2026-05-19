#!/usr/bin/env python3
"""
Sanidade: métricas no repo alinhadas ao dashboard Grafana (layout-v25).

Uso: python3 scripts/validate-observability.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASH = ROOT / "config/grafana/provisioning/dashboards/json/docmaster-backend.json"
METRICS_PY = ROOT / "backend/app/metrics.py"
BUILD_PY = ROOT / "scripts/build-grafana-dashboard.py"

REQUIRED_DOCMASTER = [
    "docmaster_auth_login_total",
    "docmaster_document_operations_total",
    "docmaster_document_operation_duration_seconds",
    "docmaster_llm_tokens_total",
    "docmaster_metrics_active",
]

ALLOWED_FLUXOS = {"fill_tr_slots", "gerar_tr_e_dfd", "gerar_llm"}


def main() -> int:
    errors: list[str] = []

    if not DASH.is_file():
        errors.append(f"Dashboard ausente: {DASH}")
    else:
        dash = json.loads(DASH.read_text(encoding="utf-8"))
        tags = dash.get("tags") or []
        if "layout-v25" not in tags:
            errors.append(f"Dashboard sem tag layout-v25 (tags={tags})")
        exprs = json.dumps(dash.get("panels") or [])
        if "llm_proxy" in exprs:
            errors.append("Dashboard referencia llm_proxy em PromQL (não deve)")
        if "fill_tr_slots|gerar_tr_e_dfd|gerar_llm" not in exprs:
            errors.append("Dashboard sem filtro de fluxo nos tokens LLM")

    metrics_src = METRICS_PY.read_text(encoding="utf-8")
    for name in REQUIRED_DOCMASTER:
        if name not in metrics_src:
            errors.append(f"metrics.py sem {name}")

    m = re.search(r"ALLOWED_LLM_TOKEN_FLUXOS\s*=\s*frozenset\(\{([^}]+)\}", metrics_src)
    if m:
        found = {x.strip().strip('"') for x in m.group(1).split(",") if x.strip()}
        if found != ALLOWED_FLUXOS:
            errors.append(f"ALLOWED_LLM_TOKEN_FLUXOS={found} (esperado {ALLOWED_FLUXOS})")

    llm_proxy = (ROOT / "backend/app/llm_proxy.py").read_text(encoding="utf-8")
    if "record_llm_token_usage" in llm_proxy:
        errors.append("llm_proxy ainda chama record_llm_token_usage (polui tokens)")

    if errors:
        print("FALHOU validação observabilidade:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("OK — observabilidade consistente (layout-v25, métricas, llm_proxy limpo).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
