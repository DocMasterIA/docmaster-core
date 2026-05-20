#!/usr/bin/env python3
"""
Valida o mapa fluxo → métricas Prometheus (código + opcional scrape ao vivo).

  python3 scripts/validate-metrics-flows.py
  METRICS_URL=https://api.docmasteria.com.br/metrics python3 scripts/validate-metrics-flows.py

Saída: OK/FALHOU por fluxo de negócio com evidência do /metrics quando URL definida.
"""
from __future__ import annotations

import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.metrics import (  # noqa: E402
    ALLOWED_LLM_TOKEN_FLUXOS,
    package_to_tipo_geracao,
    record_document_operation,
    record_llm_token_usage,
)
from backend.app.slot_package_keys import ROUTE_TO_SLOT_PACKAGE, resolve_slot_package_key

METRICS_URL = (os.environ.get("METRICS_URL") or "").strip()


@dataclass(frozen=True)
class FlowSpec:
    name: str
    package: str
    llm_fluxo: str | None  # None = sem tokens LLM neste passo
    doc_operation: str | None  # operação em docmaster_document_operations_total
    frontend_hint: str


# Mapa acordado com o produto (o que cada UI deve disparar).
FLOWS: list[FlowSpec] = [
    FlowSpec(
        "Dispensa normal — cláusulas (IA antes do documento)",
        "dispensa_75_ii_compras",
        "fill_tr_slots",
        "fill_tr_slots",
        "DispensaArt75IINormalForm → POST fill-tr-slots",
    ),
    FlowSpec(
        "Dispensa normal — documento ZIP",
        "dispensa_75_ii_compras",
        None,
        "gerar_tr_e_dfd",
        "DispensaArt75IINormalForm → POST gerar-tr-e-dfd",
    ),
    FlowSpec(
        "Dispensa rápida — cláusulas",
        "dispensa_rapida_75_ii_compras",
        "fill_tr_slots",
        "fill_tr_slots",
        "DispensaArt75IIRapidaForm → POST fill-tr-slots",
    ),
    FlowSpec(
        "Dispensa rápida — documento ZIP",
        "dispensa_rapida_75_ii_compras",
        None,
        "gerar_tr_e_dfd",
        "DispensaArt75IIRapidaForm → POST gerar-tr-e-dfd",
    ),
    FlowSpec(
        "Inexigibilidade — cláusulas (IA interna)",
        "inexigibilidade_74_i_fornecedor_exclusivo",
        "clausulas_llm",
        None,
        "Inexigibilidade*Preview → POST /api/llm/generate",
    ),
    FlowSpec(
        "Inexigibilidade — documento ZIP",
        "inexigibilidade_74_i_fornecedor_exclusivo",
        None,
        "gerar_tr_e_dfd",
        "Inexigibilidade*Preview → POST gerar-tr-e-dfd",
    ),
    FlowSpec(
        "ETP livre — geração completa via LLM",
        "etp_livre",
        "gerar_llm",
        "gerar_llm",
        "DocumentGenerator (EtpLivre) → POST gerar-via-llm",
    ),
]

EXPECTED_TIPOS = {
    "dispensa_75_ii_compras": "dispensa_normal",
    "dispensa_rapida_75_ii_compras": "dispensa_rapida",
    "inexigibilidade_74_i_fornecedor_exclusivo": "inexigibilidade",
    "etp_livre": "etp",
}


def _fetch_metrics_text() -> str:
    if not METRICS_URL:
        return ""
    req = urllib.request.Request(METRICS_URL, headers={"User-Agent": "docmaster-validate-metrics-flows/1"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _metric_has_labels(
    text: str,
    metric: str,
    required: dict[str, str],
) -> bool:
    """True se existir pelo menos uma série com labels exatos."""
    if not text:
        return False
    for line in text.splitlines():
        if not line.startswith(metric + "{"):
            continue
        ok = True
        for k, v in required.items():
            if f'{k}="{v}"' not in line:
                ok = False
                break
        if ok:
            return True
    return False


def _code_checks() -> list[str]:
    errors: list[str] = []
    for pkg, tipo in EXPECTED_TIPOS.items():
        got = package_to_tipo_geracao(pkg, fluxo="fill_tr_slots")
        if got != tipo:
            errors.append(f"package_to_tipo_geracao({pkg!r})={got!r}, esperado {tipo!r}")

    if "clausulas_llm" not in ALLOWED_LLM_TOKEN_FLUXOS:
        errors.append("ALLOWED_LLM_TOKEN_FLUXOS sem clausulas_llm")

    mock_req = type("R", (), {"META": {"HTTP_REFERER": "https://app/geracao/inexigibilidade-art-74-i/fornecedor-exclusivo"}})()
    key = resolve_slot_package_key({"slot_package_key": "inexigibilidade_74_i_fornecedor_exclusivo"}, mock_req)
    if key != "inexigibilidade_74_i_fornecedor_exclusivo":
        errors.append(f"resolve_slot_package_key inexig={key!r}")

    if len(ROUTE_TO_SLOT_PACKAGE) < 10:
        errors.append(f"ROUTE_TO_SLOT_PACKAGE incompleto ({len(ROUTE_TO_SLOT_PACKAGE)} rotas)")

  # llm_proxy deve referenciar clausulas_llm
    proxy = (ROOT / "backend/app/llm_proxy.py").read_text(encoding="utf-8")
    if 'fluxo="clausulas_llm"' not in proxy:
        errors.append("llm_proxy.py não grava fluxo clausulas_llm")

    for path in (
        "frontend-vue/src/components/dispensa-art-75-ii/DispensaArt75IINormalForm.vue",
        "frontend-vue/src/components/dispensa-art-75-ii/DispensaArt75IIRapidaForm.vue",
    ):
        src = (ROOT / path).read_text(encoding="utf-8")
        if "fill-tr-slots" not in src and "fetchFillTrSlots" not in src:
            errors.append(f"{path} sem fill-tr-slots")

    inex = (ROOT / "frontend-vue/src/views/InexigibilidadeManutencaoVeiculosPreview.vue").read_text(encoding="utf-8")
    if "/api/llm/generate" not in inex:
        errors.append("InexigibilidadeManutencaoVeiculosPreview sem /api/llm/generate")
    if "slot_package_key: slotPackageKey" not in inex:
        errors.append("Inexigibilidade sem slot_package_key no POST /api/llm/generate")

    dash = (ROOT / "config/grafana/provisioning/dashboards/json/docmaster-backend.json").read_text(encoding="utf-8")
    if "layout-v32" not in dash:
        errors.append("Dashboard sem tag layout-v32 (corra build-grafana-dashboard.py)")

    for label in ("Média — Dispensa normal", "Média — Dispensa rápida", "Média — Inexigibilidade", "Média — ETP"):
        if label not in dash:
            errors.append(f"Dashboard sem painel «{label}»")

    return errors


def main() -> int:
    print("=== Validação fluxos → métricas DocMaster ===\n")
    code_errors = _code_checks()
    if code_errors:
        print("CÓDIGO — problemas:")
        for e in code_errors:
            print(f"  ✗ {e}")
    else:
        print("CÓDIGO — OK (mapa package→tipo, clausulas_llm, rotas frontend, layout-v32)")

    metrics_text = _fetch_metrics_text()
    if not metrics_text:
        print("\nMÉTRICAS AO VIVO — ignorado (defina METRICS_URL=.../metrics)")
        return 1 if code_errors else 0

    print(f"\nMÉTRICAS AO VIVO — {METRICS_URL}")
    print("(contadores desde o último restart do backend; 0 = ainda não houve uso após deploy)\n")

    live_fail = 0
    for flow in FLOWS:
        tipo = package_to_tipo_geracao(flow.package, fluxo=flow.llm_fluxo or flow.doc_operation or "")
        parts = [f"tipo_geracao={tipo}"]

        llm_ok = True
        doc_ok = True

        if flow.llm_fluxo:
            llm_ok = _metric_has_labels(
                metrics_text,
                "docmaster_llm_invocations_total",
                {"fluxo": flow.llm_fluxo, "tipo_geracao": tipo},
            )
            parts.append(f"LLM fluxo={flow.llm_fluxo} {'✓' if llm_ok else '✗ (0 no scrape)'}")

        if flow.doc_operation:
            doc_ok = _metric_has_labels(
                metrics_text,
                "docmaster_document_operations_total",
                {
                    "operation": flow.doc_operation,
                    "result": "success",
                    "tipo_geracao": tipo,
                },
            )
            parts.append(f"op={flow.doc_operation} {'✓' if doc_ok else '✗ (0 no scrape)'}")

        status = "OK" if (llm_ok and doc_ok) else "SEM DADOS"
        if flow.llm_fluxo and not llm_ok:
            live_fail += 1
        if flow.doc_operation and not doc_ok:
            live_fail += 1
        print(f"  [{status}] {flow.name}")
        print(f"         {flow.frontend_hint}")
        print(f"         {' | '.join(parts)}")

    # Resumo por tipo no scrape
    print("\n--- Resumo invocações LLM por tipo_geracao (valor no scrape) ---")
    for tipo in ("dispensa_normal", "dispensa_rapida", "inexigibilidade", "etp"):
        pat = re.compile(
            rf'^docmaster_llm_invocations_total\{{[^}}]*tipo_geracao="{re.escape(tipo)}"[^}}]*\}}\s+(\S+)',
            re.M,
        )
        vals = [float(m.group(1)) for m in pat.finditer(metrics_text)]
        total = sum(vals)
        print(f"  {tipo}: {total:g} invocação(ões) no contador")

    for fl in ("clausulas_llm", "fill_tr_slots", "gerar_llm", "gerar_tr_e_dfd"):
        pat = re.compile(
            rf'^docmaster_llm_invocations_total\{{[^}}]*fluxo="{re.escape(fl)}"[^}}]*\}}\s+(\S+)',
            re.M,
        )
        vals = [float(m.group(1)) for m in pat.finditer(metrics_text)]
        if vals:
            print(f"  fluxo {fl}: {sum(vals):g} invocação(ões)")

    print()
    if code_errors:
        print("FALHOU — corrija o código acima.")
        return 1
    if live_fail:
        print(
            "AVISO — código OK, mas alguns fluxos têm contador 0 no scrape atual.\n"
            "  Isso é normal se ninguém usou esse fluxo desde o último deploy/restart.\n"
            "  Teste: gere cláusulas + documento em cada modalidade e rode de novo com METRICS_URL."
        )
        return 2
    print("OK — código e scrape com dados para todos os fluxos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
