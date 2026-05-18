#!/usr/bin/env python3
"""Gera config/grafana/provisioning/dashboards/json/docmaster-backend.json"""
import json
from pathlib import Path

DS = {"type": "prometheus", "uid": "prometheus"}
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "config/grafana/provisioning/dashboards/json/docmaster-backend.json"


def row(id_, title, y, collapsed=False):
    return {"collapsed": collapsed, "gridPos": {"h": 1, "w": 24, "x": 0, "y": y}, "id": id_, "title": title, "type": "row"}


def stat(id_, title, y, x, w, expr, desc=""):
    return {
        "datasource": DS,
        "description": desc,
        "fieldConfig": {"defaults": {"decimals": 0, "noValue": "0", "unit": "short"}, "overrides": []},
        "gridPos": {"h": 4, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {"colorMode": "value", "graphMode": "area", "justifyMode": "center", "reduceOptions": {"calcs": ["lastNotNull"]}},
        "targets": [{"datasource": DS, "expr": expr, "refId": "A"}],
        "title": title,
        "type": "stat",
    }


def ts(id_, title, y, x, w, h, targets, unit="short", desc=""):
    return {
        "datasource": DS,
        "description": desc,
        "fieldConfig": {"defaults": {"noValue": "0", "unit": unit}, "overrides": []},
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi"}},
        "targets": [
            {"datasource": DS, "expr": e, "legendFormat": l, "refId": chr(65 + i)} for i, (e, l) in enumerate(targets)
        ],
        "title": title,
        "type": "timeseries",
    }


def bar_multi(id_, title, y, x, w, h, targets, desc=""):
    return {
        "datasource": DS,
        "description": desc,
        "fieldConfig": {"defaults": {"unit": "short"}, "overrides": []},
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {"legend": {"displayMode": "table", "placement": "right", "calcs": ["sum"]}, "orientation": "horizontal"},
        "targets": [
            {"datasource": DS, "expr": e, "legendFormat": l, "refId": chr(65 + i)} for i, (e, l) in enumerate(targets)
        ],
        "title": title,
        "type": "barchart",
    }


def bar_tenant(id_, title, y, x, w, h, expr):
    return {
        "datasource": DS,
        "description": "tenant = UF (2 letras), staff, ou slug da prefeitura se UF ausente.",
        "fieldConfig": {
            "defaults": {
                "unit": "short",
                "mappings": [
                    {
                        "type": "value",
                        "options": {
                            "staff": {"text": "Equipe DocMaster (staff)"},
                            "anonymous": {"text": "Anônimo"},
                            "sem_prefeitura": {"text": "Sem prefeitura"},
                            "test": {"text": "Slug prefeitura «test»"},
                        },
                    }
                ],
            },
            "overrides": [],
        },
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {"legend": {"displayMode": "table", "placement": "right", "calcs": ["lastNotNull"]}},
        "targets": [{"datasource": DS, "expr": expr, "legendFormat": "{{tenant}}", "refId": "A"}],
        "title": title,
        "type": "barchart",
    }


def text_panel(id_, y, content):
    return {
        "gridPos": {"h": 3, "w": 24, "x": 0, "y": y},
        "id": id_,
        "options": {"mode": "markdown", "content": content},
        "title": "",
        "type": "text",
        "transparent": True,
    }


DOC_OP = lambda op: f'sum(docmaster_document_operations_total{{operation="{op}",result="success"}})'

panels = []
y = 0
panels.append(
    text_panel(
        299,
        y,
        "**Como ler:** cartões = total desde o último restart do backend. Gráficos = actividade no período do Grafana. "
        "Dados vêm do Prometheus (scrape `api.docmasteria.com.br`). Faça login/geração **nesse** ambiente.",
    )
)
y += 3

panels.append(row(300, "Gestão — resumo (totais acumulados)", y))
y += 1
panels += [
    stat(301, "IA — preencher slots", y, 0, 4, DOC_OP("fill_tr_slots")),
    stat(302, "Gerar via LLM", y, 4, 4, DOC_OP("gerar_llm")),
    stat(303, "TR + DFD + Ofício", y, 8, 4, DOC_OP("gerar_tr_e_dfd")),
    stat(304, "Docs salvos", y, 12, 4, "sum(docmaster_document_instances_created_total)"),
    stat(305, "Logins OK", y, 16, 4, 'sum(docmaster_auth_login_total{result="success"})'),
    stat(306, "Erros geração", y, 20, 4, 'sum(docmaster_document_operations_total{result="error"})'),
]
y += 4

panels.append(
    bar_multi(
        307,
        "Gerações no período (incremento)",
        y,
        0,
        12,
        8,
        [
            ('sum(increase(docmaster_document_operations_total{operation="fill_tr_slots",result="success"}[$__range]))', "Preencher slots (IA)"),
            ('sum(increase(docmaster_document_operations_total{operation="gerar_llm",result="success"}[$__range]))', "Gerar via LLM"),
            ('sum(increase(docmaster_document_operations_total{operation="gerar_tr_e_dfd",result="success"}[$__range]))', "TR + DFD"),
            ('sum(increase(docmaster_document_operations_total{operation="gerar_tr_modelo",result="success"}[$__range]))', "TR modelo"),
        ],
    )
)
panels.append(
    ts(
        308,
        "Gerações ao longo do tempo",
        y,
        12,
        12,
        8,
        [
            ('sum(increase(docmaster_document_operations_total{operation="fill_tr_slots",result="success"}[$__interval]))', "Slots IA"),
            ('sum(increase(docmaster_document_operations_total{operation="gerar_llm",result="success"}[$__interval]))', "LLM"),
            ('sum(increase(docmaster_document_operations_total{operation="gerar_tr_e_dfd",result="success"}[$__interval]))', "TR+DFD"),
        ],
    )
)
y += 8

panels.append(row(310, "Inteligência artificial", y))
y += 1
panels += [
    stat(311, "Chamadas proxy LLM", y, 0, 6, 'sum(docmaster_platform_events_total{module="llm",result="success"})'),
    stat(312, "Planner+section+generate", y, 6, 6,
         'sum(docmaster_platform_events_total{module="llm",action=~"planner|section|generate",result="success"})'),
    stat(313, "Análise edital (RAG)", y, 12, 6, 'sum(docmaster_platform_events_total{module="analise",result="success"})'),
    stat(314, "Erros IA/PNCP", y, 18, 6, 'sum(docmaster_platform_events_total{module=~"llm|analise",result="error"})'),
]
y += 4
panels.append(
    ts(
        315,
        "Proxy LLM por endpoint",
        y,
        0,
        12,
        7,
        [
            ('sum(increase(docmaster_platform_events_total{module="llm",action="planner"}[$__interval]))', "Planner"),
            ('sum(increase(docmaster_platform_events_total{module="llm",action="section"}[$__interval]))', "Section"),
            ('sum(increase(docmaster_platform_events_total{module="llm",action="generate"}[$__interval]))', "Generate"),
            ('sum(increase(docmaster_platform_events_total{module="llm",action="analysis"}[$__interval]))', "Analysis"),
        ],
    )
)
panels.append(
    ts(
        316,
        "Duração operações IA (p95)",
        y,
        12,
        12,
        7,
        [
            ('histogram_quantile(0.95, sum(rate(docmaster_document_operation_duration_seconds_bucket{operation="fill_tr_slots"}[$__rate_interval])) by (le))', "Slots p95"),
            ('histogram_quantile(0.95, sum(rate(docmaster_document_operation_duration_seconds_bucket{operation="gerar_llm"}[$__rate_interval])) by (le))', "LLM p95"),
        ],
        unit="s",
    )
)
y += 7

panels.append(row(320, "PNCP — pesquisa de preços", y))
y += 1
panels += [
    stat(321, "Eventos cotação", y, 0, 8, 'sum(docmaster_platform_events_total{module="pncp_cotacao",result="success"})'),
    stat(322, "Relatórios PDF", y, 8, 8, 'sum(docmaster_platform_events_total{module="pncp_cotacao",action="relatorio_pdf",result="success"})'),
    stat(323, "Research proxy", y, 16, 8, 'sum(docmaster_platform_events_total{module="pncp_research",result="success"})'),
]
y += 4
panels.append(
    ts(
        325,
        "PNCP ao longo do tempo",
        y,
        0,
        24,
        7,
        [
            ('sum(increase(docmaster_platform_events_total{module="pncp_cotacao"}[$__interval]))', "Cotações"),
            ('sum(increase(docmaster_platform_events_total{module="pncp_research"}[$__interval]))', "Research"),
            ('sum(increase(django_http_requests_total_by_view_transport_method_total{view=~"api_pncp.*"}[$__interval]))', "HTTP PNCP"),
        ],
    )
)
y += 7

panels.append(row(330, "Utilizadores", y))
y += 1
panels.append(
    ts(
        331,
        "Logins por resultado (período)",
        y,
        0,
        12,
        7,
        [
            ('sum(increase(docmaster_auth_login_total{result="success"}[$__interval]))', "Sucesso"),
            ('sum(increase(docmaster_auth_login_total{result="failure"}[$__interval]))', "Falha"),
            ('sum(increase(docmaster_auth_login_total{result="locked"}[$__interval]))', "Bloqueado"),
            ('sum(increase(django_http_requests_total_by_view_transport_method_total{view="api_auth_login"}[$__interval]))', "HTTP login (fallback)"),
        ],
    )
)
panels.append(
    bar_tenant(
        332,
        "Logins OK — por tenant (total acumulado)",
        y,
        12,
        12,
        7,
        'sum(docmaster_auth_login_total{result="success"}) by (tenant)',
    )
)
y += 7

panels.append(row(340, "Pacotes / dispensas", y))
y += 1
panels.append(
    bar_multi(
        341,
        "Gerações por pacote (período)",
        y,
        0,
        14,
        8,
        [('sum(increase(docmaster_document_operations_total{result="success",package!~"unknown|other"}[$__range])) by (package)', "{{package}}")],
    )
)
panels.append(
    ts(
        342,
        "Docs persistidos",
        y,
        14,
        10,
        8,
        [('sum(increase(docmaster_document_instances_created_total[$__interval])) by (doc_type)', "{{doc_type}}")],
    )
)
y += 8

panels.append(row(350, "Desenvolvimento — saúde", y, collapsed=True))
y += 1
panels += [
    stat(351, "Backend UP", y, 0, 4, 'up{job="backend"}'),
    stat(352, "HTTP total (período)", y, 4, 5, 'sum(increase(django_http_requests_total_by_method_total{job="backend"}[$__range]))'),
    stat(353, "5xx (período)", y, 9, 5, 'sum(increase(django_http_responses_total_by_status_total{job="backend",status=~"5.."}[$__range]))'),
    stat(354, "4xx (período)", y, 14, 5, 'sum(increase(django_http_responses_total_by_status_total{job="backend",status=~"4.."}[$__range]))'),
    stat(355, "RSS", y, 19, 5, 'max(process_resident_memory_bytes{job="backend"})'),
]
y += 4
panels.append(
    ts(
        356,
        "Latência p95",
        y,
        0,
        12,
        7,
        [
            ('histogram_quantile(0.95, sum(rate(django_http_requests_latency_seconds_by_view_method_bucket{view="documentos_fill_tr_slots_api"}[$__rate_interval])) by (le))', "Slots"),
            ('histogram_quantile(0.95, sum(rate(django_http_requests_latency_seconds_by_view_method_bucket{view="documentos_gerar_tr_e_dfd_api"}[$__rate_interval])) by (le))', "TR+DFD"),
            ('histogram_quantile(0.95, sum(rate(django_http_requests_latency_seconds_by_view_method_bucket{view="api_auth_login"}[$__rate_interval])) by (le))', "Login"),
        ],
        unit="s",
    )
)
panels.append(
    ts(
        357,
        "CPU / DB",
        y,
        12,
        12,
        7,
        [
            ('rate(process_cpu_seconds_total{job="backend"}[$__rate_interval])', "CPU"),
            ('sum(rate(django_db_execute_total{job="backend"}[$__rate_interval])) by (vendor)', "DB"),
        ],
    )
)

dash = {
    "annotations": {"list": []},
    "editable": False,
    "description": "Layout v9 — stats acumulados + gráficos por período. Requer backend com docmaster_* e scrape Prometheus.",
    "fiscalYearStartMonth": 0,
    "graphTooltip": 1,
    "id": None,
    "links": [],
    "panels": panels,
    "refresh": "30s",
    "schemaVersion": 39,
    "tags": ["docmaster", "backend", "django", "layout-v9"],
    "templating": {"list": []},
    "time": {"from": "now-24h", "to": "now"},
    "timezone": "browser",
    "title": "DocMaster — Backend Django",
    "uid": "docmaster-backend",
    "version": 9,
}

OUT.write_text(json.dumps(dash, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Wrote {OUT} ({len(panels)} panels)")