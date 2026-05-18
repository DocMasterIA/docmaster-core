#!/usr/bin/env python3
"""Gera config/grafana/provisioning/dashboards/json/docmaster-backend.json"""
import json
from pathlib import Path

DS = {"type": "prometheus", "uid": "prometheus"}
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "config/grafana/provisioning/dashboards/json/docmaster-backend.json"

PACKAGE_LABELS = {
    "dispensa_75_i_manutencao_veiculos": "Dispensa 75-I — Veículos",
    "dispensa_75_i_obras_engenharia": "Dispensa 75-I — Obras",
    "dispensa_75_ii_compras": "Dispensa 75-II — Compras",
    "dispensa_75_ii_servicos": "Dispensa 75-II — Serviços",
    "dispensa_75_ii_compras_servicos_inclusos": "Dispensa 75-II — Compras+Serv.",
    "inexigibilidade_74_i_manutencao_veiculos": "Inexig. 74-I — Veículos",
    "inexigibilidade_74_i_fornecedor_exclusivo": "Inexig. 74-I — Exclusivo",
}


def row(id_, title, y, collapsed=False):
    return {"collapsed": collapsed, "gridPos": {"h": 1, "w": 24, "x": 0, "y": y}, "id": id_, "title": title, "type": "row"}


def instant(expr, ref="A"):
    return {
        "datasource": DS,
        "expr": expr,
        "refId": ref,
        "instant": True,
        "range": False,
        "format": "table",
        "editorMode": "code",
    }


def range_query(expr, ref="A", legend=None):
    t = {"datasource": DS, "expr": expr, "refId": ref, "range": True, "editorMode": "code", "legendFormat": legend or ""}
    return t


def period_delta(selector: str) -> str:
    """
    Contagem exacta no intervalo do Grafana: valor agora − valor no início do período.
    Monótono: 24h >= 16h (se o backend não reiniciou no meio).
    clamp_min trata restart (contador voltou a 0).
    """
    return f"""clamp_min(
sum({selector})
- sum({selector} offset $__range),
0)"""


def count_interval(selector: str) -> str:
    """Por bucket de tempo (gráfico de linha) — só para ver distribuição, não somar picos."""
    return f"sum(increase({selector}[$__interval]))"


def total(selector: str) -> str:
    """Total acumulado no contador (não depende do período do Grafana)."""
    return f"sum({selector})"


def total_by(selector: str, label: str) -> str:
    return f"sum({selector}) by ({label})"


def stat(id_, title, y, x, w, expr, desc="", *, period=False):
    return {
        "datasource": DS,
        "description": desc
        or ("Soma no período do Grafana." if period else "Query instantânea: total actual (ignora «últimas 24h»)."),
        "fieldConfig": {"defaults": {"decimals": 0, "noValue": "0", "unit": "none"}, "overrides": []},
        "gridPos": {"h": 4, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {
            "colorMode": "value",
            "graphMode": "none",
            "justifyMode": "center",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": "auto",
        },
        "targets": [range_query(expr) if period else instant(expr)],
        "title": title,
        "type": "stat",
    }


def ts_counts(id_, title, y, x, w, h, series, desc=""):
    return {
        "datasource": DS,
        "description": desc,
        "fieldConfig": {"defaults": {"decimals": 0, "noValue": "0", "unit": "none"}, "overrides": []},
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi"}},
        "targets": [range_query(e, chr(65 + i), l) for i, (e, l) in enumerate(series)],
        "title": title,
        "type": "timeseries",
    }


def ts_duration(id_, title, y, x, w, h, series, desc=""):
    return {
        "datasource": DS,
        "description": desc,
        "fieldConfig": {"defaults": {"unit": "s"}, "overrides": []},
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {"legend": {"displayMode": "list", "placement": "bottom"}},
        "targets": [range_query(e, chr(65 + i), l) for i, (e, l) in enumerate(series)],
        "title": title,
        "type": "timeseries",
    }


def _table_transforms(label_key: str, label_col: str, value_col: str):
    """Prometheus format=table + séries em linhas com coluna de label visível."""
    return [
        {"id": "seriesToRows", "options": {}},
        {
            "id": "organize",
            "options": {
                "excludeByName": {
                    "Time": True,
                    "time": True,
                    "__name__": True,
                    "Metric": True,
                    "job": True,
                    "instance": True,
                    "service": True,
                    "result": True,
                    "operation": True,
                    "output": True,
                    "tenant": True,
                },
                "indexByName": {label_key: 0, "Value": 1, "Value #A": 1},
                "renameByName": {
                    label_key: label_col,
                    "Value": value_col,
                    "Value #A": value_col,
                },
            },
        },
        {
            "id": "filterFieldsByName",
            "options": {"include": {"names": [label_col, value_col]}},
        },
    ]


def prom_table_prefeitura(id_, title, y, x, w, h, expr, desc=""):
    return {
        "datasource": DS,
        "description": desc or "Coluna Prefeitura = label prefeitura da métrica (nome do município + UF).",
        "fieldConfig": {
            "defaults": {"custom": {"align": "left", "filterable": True}, "decimals": 0},
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "Prefeitura"},
                    "properties": [{"id": "custom.width", "value": 360}],
                },
                {
                    "matcher": {"id": "byName", "options": "Logins"},
                    "properties": [{"id": "custom.width", "value": 90}, {"id": "custom.align", "value": "center"}],
                },
            ],
        },
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {
            "cellHeight": "sm",
            "footer": {"show": False},
            "showHeader": True,
            "sortBy": [{"desc": True, "displayName": "Logins"}],
        },
        "targets": [instant(expr)],
        "transformations": _table_transforms("prefeitura", "Prefeitura", "Logins"),
        "title": title,
        "type": "table",
    }


def prom_table_packages(id_, title, y, x, w, h, expr, desc=""):
    pkg_mappings = {"type": "value", "options": {k: {"text": v} for k, v in PACKAGE_LABELS.items()}}
    return {
        "datasource": DS,
        "description": desc or "Pacote = tipo de dispensa / fluxo de geração.",
        "fieldConfig": {
            "defaults": {"custom": {"align": "left", "filterable": True}, "decimals": 0},
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "Pacote"},
                    "properties": [
                        {"id": "custom.width", "value": 360},
                        {"id": "mappings", "value": [pkg_mappings]},
                    ],
                },
                {
                    "matcher": {"id": "byName", "options": "Gerações"},
                    "properties": [{"id": "custom.width", "value": 90}, {"id": "custom.align", "value": "center"}],
                },
            ],
        },
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {
            "cellHeight": "sm",
            "footer": {"show": False},
            "showHeader": True,
            "sortBy": [{"desc": True, "displayName": "Gerações"}],
        },
        "targets": [instant(expr)],
        "transformations": _table_transforms("package", "Pacote", "Gerações"),
        "title": title,
        "type": "table",
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


DOC = lambda op: total(f'docmaster_document_operations_total{{operation="{op}",result="success"}}')

panels = []
y = 0
panels.append(
    text_panel(
        299,
        y,
        "**Totais acumulados** = contador actual (não depende do período do Grafana). "
        "**No período** = contador agora − contador no início do intervalo (16h ⊆ 24h → nunca maior em 16h). "
        "Se o backend **reiniciou** no meio do intervalo, o período pode subestimar. "
        "Uma geração TR+DFD pode contar várias *operações* (slots + zip); «documentos salvos» é outra métrica.",
    )
)
y += 3

# --- Totais acumulados (instant) ---
panels.append(row(300, "Totais acumulados (desde o último restart do backend)", y))
y += 1
panels += [
    stat(301, "IA — preencher slots", y, 0, 4, DOC("fill_tr_slots")),
    stat(302, "Gerar via LLM", y, 4, 4, DOC("gerar_llm")),
    stat(303, "TR + DFD + Ofício", y, 8, 4, DOC("gerar_tr_e_dfd")),
    stat(304, "Docs salvos", y, 12, 4, total("docmaster_document_instances_created_total")),
    stat(305, "Logins OK", y, 16, 4, total('docmaster_auth_login_total{result="success"}')),
    stat(306, "Erros geração", y, 20, 4, total('docmaster_document_operations_total{result="error"}')),
]
y += 4

panels.append(
    prom_table_prefeitura(
        332,
        "Logins OK — por prefeitura (total acumulado)",
        y,
        0,
        12,
        8,
        total_by('docmaster_auth_login_total{result="success"}', "prefeitura"),
        "Query instantânea. Coluna Prefeitura = nome do município no cadastro.",
    )
)
panels.append(
    prom_table_packages(
        341,
        "Gerações por pacote (total acumulado)",
        y,
        12,
        12,
        8,
        total_by('docmaster_document_operations_total{result="success",package!~"unknown|other"}', "package"),
    )
)
y += 8

# --- No período Grafana (delta de contador — coerente com o intervalo) ---
panels.append(row(3010, "No período seleccionado no Grafana", y))
y += 1
panels += [
    stat(
        309,
        "Documentos salvos (período)",
        y,
        0,
        6,
        period_delta("docmaster_document_instances_created_total"),
        period=True,
    ),
    stat(
        307,
        "Operações geração OK (período)",
        y,
        6,
        6,
        period_delta('docmaster_document_operations_total{result="success"}'),
        period=True,
    ),
    stat(
        331,
        "Logins OK (período)",
        y,
        12,
        6,
        period_delta('docmaster_auth_login_total{result="success"}'),
        period=True,
    ),
    stat(
        3311,
        "TR+DFD no período",
        y,
        18,
        6,
        period_delta('docmaster_document_operations_total{operation="gerar_tr_e_dfd",result="success"}'),
        period=True,
    ),
]
y += 4

def bar_period_breakdown(id_, title, y, x, w, h, items, desc=""):
    return {
        "datasource": DS,
        "description": desc,
        "fieldConfig": {"defaults": {"decimals": 0, "unit": "none"}, "overrides": []},
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {"legend": {"displayMode": "table", "placement": "right", "calcs": ["lastNotNull"]}, "orientation": "horizontal"},
        "targets": [range_query(period_delta(sel), chr(65 + i), leg) for i, (sel, leg) in enumerate(items)],
        "title": title,
        "type": "barchart",
    }


panels.append(
    bar_period_breakdown(
        3071,
        "Operações no período (detalhe — não somar à mão)",
        y,
        0,
        24,
        7,
        [
            ('docmaster_document_operations_total{operation="fill_tr_slots",result="success"}', "Preencher slots"),
            ('docmaster_document_operations_total{operation="gerar_tr_e_dfd",result="success"}', "TR + DFD + Ofício"),
            ('docmaster_document_operations_total{operation="gerar_llm",result="success"}', "Gerar LLM"),
            ('docmaster_document_operations_total{operation="gerar_tr_modelo",result="success"}', "TR modelo"),
        ],
        "Cada barra é um tipo de operação; um fluxo TR+DFD pode incluir slots antes.",
    )
)
y += 7

panels.append(
    ts_counts(
        308,
        "Gerações ao longo do tempo (por intervalo)",
        y,
        0,
        24,
        8,
        [
            (count_interval('docmaster_document_operations_total{operation="fill_tr_slots",result="success"}'), "Slots IA"),
            (count_interval('docmaster_document_operations_total{operation="gerar_llm",result="success"}'), "LLM"),
            (count_interval('docmaster_document_operations_total{operation="gerar_tr_e_dfd",result="success"}'), "TR+DFD"),
        ],
        "Cada ponto = gerações naquele bucket de tempo. Zero = nenhuma naquele minuto/hora.",
    )
)
y += 8

# --- IA ---
panels.append(row(310, "Inteligência artificial", y))
y += 1
panels += [
    stat(311, "LLM OK (total)", y, 0, 6, total('docmaster_platform_events_total{module="llm",result="success"}')),
    stat(312, "Análise RAG (total)", y, 6, 6, total('docmaster_platform_events_total{module="analise",result="success"}')),
    stat(313, "Erros IA (total)", y, 12, 6, total('docmaster_platform_events_total{module=~"llm|analise",result="error"}')),
    stat(314, "PNCP OK (total)", y, 18, 6, total('docmaster_platform_events_total{module=~"pncp_.*",result="success"}')),
]
y += 4
panels.append(
    ts_counts(
        315,
        "LLM no período",
        y,
        0,
        12,
        7,
        [
            (count_interval('docmaster_platform_events_total{module="llm",action="planner"}'), "Planner"),
            (count_interval('docmaster_platform_events_total{module="llm",action="generate"}'), "Generate"),
        ],
    )
)
panels.append(
    ts_duration(
        316,
        "Duração IA p95",
        y,
        12,
        12,
        7,
        [
            ('histogram_quantile(0.95, sum(rate(docmaster_document_operation_duration_seconds_bucket{operation="fill_tr_slots"}[$__rate_interval])) by (le))', "Slots"),
            ('histogram_quantile(0.95, sum(rate(docmaster_document_operation_duration_seconds_bucket{operation="gerar_llm"}[$__rate_interval])) by (le))', "LLM"),
        ],
    )
)
y += 7

# --- PNCP ---
panels.append(row(320, "PNCP", y))
y += 1
panels += [
    stat(321, "Cotações OK", y, 0, 8, total('docmaster_platform_events_total{module="pncp_cotacao",result="success"}')),
    stat(322, "PDF relatório", y, 8, 8, total('docmaster_platform_events_total{module="pncp_cotacao",action="relatorio_pdf",result="success"}')),
    stat(323, "Research OK", y, 16, 8, total('docmaster_platform_events_total{module="pncp_research",result="success"}')),
]
y += 4
panels.append(
    ts_counts(
        325,
        "PNCP no período",
        y,
        0,
        24,
        7,
        [
            (count_interval('docmaster_platform_events_total{module="pncp_cotacao"}'), "Cotações"),
            (count_interval('docmaster_platform_events_total{module="pncp_research"}'), "Research"),
        ],
    )
)
y += 7

# --- Dev ---
panels.append(row(350, "Desenvolvimento — saúde", y, collapsed=True))
y += 1
panels += [
    stat(351, "Backend UP", y, 0, 4, 'up{job="backend"}'),
    stat(352, "HTTP (período)", y, 4, 5, period_delta('django_http_requests_total_by_method_total{job="backend"}'), period=True),
    stat(353, "5xx (período)", y, 9, 5, period_delta('django_http_responses_total_by_status_total{job="backend",status=~"5.."}'), period=True),
    stat(354, "4xx (período)", y, 14, 5, period_delta('django_http_responses_total_by_status_total{job="backend",status=~"4.."}'), period=True),
    stat(355, "Memória RSS", y, 19, 5, 'max(process_resident_memory_bytes{job="backend"})'),
]
y += 4
panels.append(
    ts_duration(
        356,
        "Latência p95 HTTP",
        y,
        0,
        12,
        7,
        [
            ('histogram_quantile(0.95, sum(rate(django_http_requests_latency_seconds_by_view_method_bucket{view="documentos_fill_tr_slots_api"}[$__rate_interval])) by (le))', "Slots"),
            ('histogram_quantile(0.95, sum(rate(django_http_requests_latency_seconds_by_view_method_bucket{view="documentos_gerar_tr_e_dfd_api"}[$__rate_interval])) by (le))', "TR+DFD"),
        ],
    )
)
panels.append(
    ts_duration(
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
    "description": "Layout v12 — tabelas prefeitura/pacote com format=table + seriesToRows.",
    "fiscalYearStartMonth": 0,
    "graphTooltip": 1,
    "id": None,
    "links": [],
    "panels": panels,
    "refresh": "1m",
    "schemaVersion": 39,
    "tags": ["docmaster", "backend", "django", "layout-v12"],
    "templating": {"list": []},
    "time": {"from": "now-24h", "to": "now"},
    "timezone": "browser",
    "title": "DocMaster — Backend Django",
    "uid": "docmaster-backend",
    "version": 12,
}

OUT.write_text(json.dumps(dash, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Wrote {OUT} ({len(panels)} panels)")
