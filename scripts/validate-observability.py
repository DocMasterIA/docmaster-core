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

ALLOWED_FLUXOS = {"fill_tr_slots", "gerar_tr_e_dfd", "gerar_llm", "clausulas_llm"}


def main() -> int:
    errors: list[str] = []

    if not DASH.is_file():
        errors.append(f"Dashboard ausente: {DASH}")
    else:
        dash = json.loads(DASH.read_text(encoding="utf-8"))
        tags = dash.get("tags") or []
        panels_blob = json.dumps(dash.get("panels") or [])
        exprs = panels_blob
        if "layout-v41-host" not in tags:
            errors.append(f"Dashboard sem tag layout-v41-host (tags={tags})")
        if "node_memory_MemAvailable_bytes" not in exprs:
            errors.append("Dashboard sem métricas node_exporter (node_memory_*)")
        if 'up{job=\\"node\\"}' not in exprs and 'job="node"' not in exprs:
            errors.append("Dashboard sem painel Node scrape (up{job=node})")
        if "Média — Dispensa" in exprs or "Tokens LLM" in exprs:
            errors.append("Dashboard ainda contém painéis de tokens/média (remover)")
        if "gerar_tr_e_dfd" not in exprs or "by (tipo_geracao)" not in exprs:
            errors.append("Dashboard sem query ZIP por tipo_geracao (gerar_tr_e_dfd only)")
        if "docmaster_llm_invocations_total" not in exprs:
            errors.append("Dashboard sem painel de invocações LLM por família")
        if len(dash.get("panels") or []) > 24:
            errors.append(f"Dashboard com muitos painéis ({len(dash.get('panels') or [])}); esperado ≤24")
        if "process_cpu_seconds_total" in exprs:
            errors.append("Dashboard ainda referencia process_cpu (métrica inexistente no Django)")

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
    if "clausulas_llm" not in llm_proxy:
        errors.append("llm_proxy não grava fluxo clausulas_llm")
    if "docmaster_llm_invocations_total" not in metrics_src:
        errors.append("metrics.py sem docmaster_llm_invocations_total")

    if errors:
        print("FALHOU validação observabilidade:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("OK — observabilidade consistente (layout-v41-host).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
