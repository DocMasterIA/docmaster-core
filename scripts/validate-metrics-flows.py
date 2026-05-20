#!/usr/bin/env python3
"""
Valida o mapa fluxo → métricas Prometheus (código + opcional scrape ao vivo).

Não exige Django nem prometheus_client — roda com o python3 do sistema.

Fatores (o que cada contador significa):
  fill_tr_slots     — POST fill-tr-slots (cláusulas dispensa normal/rápida)
  gerar_tr_e_dfd    — POST gerar-tr-e-dfd (ZIP TR+DFD+Ofício; todas as modalidades)
  clausulas_llm     — POST /api/llm/generate (cláusulas inexigibilidade)
  gerar_llm         — POST gerar-via-llm (ETP livre)
  tipo_geracao      — label derivado de slot_package_key (não confundir com operation)

  python3 scripts/validate-metrics-flows.py
  METRICS_URL=https://api.docmasteria.com.br/metrics python3 scripts/validate-metrics-flows.py
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
METRICS_URL = (os.environ.get("METRICS_URL") or "").strip()


def _load_module_from_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"não foi possível carregar {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_slot_mod = _load_module_from_path(
    "docmaster_slot_package_keys",
    ROOT / "backend/app/slot_package_keys.py",
)
resolve_slot_package_key = _slot_mod.resolve_slot_package_key
ROUTE_TO_SLOT_PACKAGE = _slot_mod.ROUTE_TO_SLOT_PACKAGE


# Espelha backend/app/metrics.py (sem importar prometheus_client).
_KNOWN_SLOT_PACKAGES = frozenset(
    {
        "dispensa_75_i_manutencao_veiculos",
        "dispensa_75_i_obras_engenharia",
        "dispensa_75_ii_compras",
        "dispensa_75_ii_servicos",
        "dispensa_75_ii_compras_servicos_inclusos",
        "dispensa_rapida_75_i_manutencao_veiculos",
        "dispensa_rapida_75_i_obras_engenharia",
        "dispensa_rapida_75_ii_compras",
        "dispensa_rapida_75_ii_servicos",
        "dispensa_rapida_75_ii_compras_servicos_inclusos",
        "inexigibilidade_74_i_manutencao_veiculos",
        "inexigibilidade_74_i_fornecedor_exclusivo",
    }
)


def normalize_package_key(key: str | None) -> str:
    k = (key or "").strip().lower()
    if not k:
        return "unknown"
    if k in _KNOWN_SLOT_PACKAGES:
        return k
    if k in ("etp", "etp_livre", "tr_dfd_generico"):
        return k
    if len(k) > 64:
        return "other"
    return "other"


def package_to_tipo_geracao(package: str | None, *, fluxo: str = "") -> str:
    p = normalize_package_key(package)
    if p.startswith("dispensa_rapida_"):
        return "dispensa_rapida"
    if p.startswith("dispensa_75_") or p.startswith("dispensa_"):
        return "dispensa_normal"
    if p.startswith("inexigibilidade_"):
        return "inexigibilidade"
    if p == "etp" or p.startswith("etp_"):
        return "etp"
    if (fluxo or "").strip().lower() == "gerar_llm":
        return "etp"
    return "other"


def _allowed_llm_fluxos_from_source() -> frozenset[str]:
    src = (ROOT / "backend/app/metrics.py").read_text(encoding="utf-8")
    m = re.search(r"ALLOWED_LLM_TOKEN_FLUXOS\s*=\s*frozenset\(\s*\{([^}]+)\}", src, re.S)
    if not m:
        return frozenset()
    return frozenset(
        x.strip().strip('"').strip("'")
        for x in m.group(1).split(",")
        if x.strip()
    )


@dataclass(frozen=True)
class FlowSpec:
    name: str
    package: str
    llm_fluxo: str | None
    doc_operation: str | None
    frontend_hint: str


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

    allowed = _allowed_llm_fluxos_from_source()
    if "clausulas_llm" not in allowed:
        errors.append(f"ALLOWED_LLM_TOKEN_FLUXOS sem clausulas_llm (encontrado: {sorted(allowed)})")

    mock_req = type(
        "R",
        (),
        {"META": {"HTTP_REFERER": "https://app/geracao/inexigibilidade-art-74-i/fornecedor-exclusivo"}},
    )()
    key = resolve_slot_package_key(
        {"slot_package_key": "inexigibilidade_74_i_fornecedor_exclusivo"},
        mock_req,
    )
    if key != "inexigibilidade_74_i_fornecedor_exclusivo":
        errors.append(f"resolve_slot_package_key inexig={key!r}")

    if len(ROUTE_TO_SLOT_PACKAGE) < 10:
        errors.append(f"ROUTE_TO_SLOT_PACKAGE incompleto ({len(ROUTE_TO_SLOT_PACKAGE)} rotas)")

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

    inex = (ROOT / "frontend-vue/src/views/InexigibilidadeManutencaoVeiculosPreview.vue").read_text(
        encoding="utf-8"
    )
    if "/api/llm/generate" not in inex:
        errors.append("InexigibilidadeManutencaoVeiculosPreview sem /api/llm/generate")
    if "slot_package_key: slotPackageKey" not in inex:
        errors.append("Inexigibilidade sem slot_package_key no POST /api/llm/generate")

    api_src = (ROOT / "backend/app/api.py").read_text(encoding="utf-8")
    if "if prompt_t or completion_t:" in api_src:
        errors.append(
            "api._record_llm_usage_from_response só grava LLM com tokens>0 "
            "(invocações ficam subcontadas)"
        )

    dash = (ROOT / "config/grafana/provisioning/dashboards/json/docmaster-backend.json").read_text(
        encoding="utf-8"
    )
    if "ZIP TR+DFD por família" not in dash:
        errors.append("Dashboard sem tabela ZIP por tipo_geracao (build-grafana-dashboard.py)")
    if "Chamadas IA por família" not in dash:
        errors.append("Dashboard sem tabela IA por tipo_geracao")
    if "Média — Dispensa" in dash:
        errors.append("Dashboard ainda tem painéis de média de tokens")

    metrics_src = (ROOT / "backend/app/metrics.py").read_text(encoding="utf-8")
    if "resolve_slot_package_key({}, request)" not in metrics_src:
        errors.append("set_request_metrics sem fallback Referer para package genérico")

    return errors


def main() -> int:
    print("=== Validação fluxos → métricas DocMaster ===\n")
    code_errors = _code_checks()
    if code_errors:
        print("CÓDIGO — problemas:")
        for e in code_errors:
            print(f"  ✗ {e}")
    else:
        print("CÓDIGO — OK (instrumentação, mapa fluxos, dashboard ZIP/IA separados)")

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
