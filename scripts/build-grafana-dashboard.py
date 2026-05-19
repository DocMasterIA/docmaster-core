#!/usr/bin/env python3
"""Gera config/grafana/provisioning/dashboards/json/docmaster-backend.json"""
import json
from pathlib import Path

DS = {"type": "prometheus", "uid": "prometheus"}
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "config/grafana/provisioning/dashboards/json/docmaster-backend.json"

# Chave Prometheus (label package) → nome legível no Grafana (pt-BR).
PACKAGE_LABELS = {
    # Dispensa normal (formulário completo; chave legada dispensa_75_*)
    "dispensa_75_i_manutencao_veiculos": "Dispensa normal · Art. 75-I · Veículos",
    "dispensa_75_i_obras_engenharia": "Dispensa normal · Art. 75-I · Obras e engenharia",
    "dispensa_75_ii_compras": "Dispensa normal · Art. 75-II · Compras",
    "dispensa_75_ii_servicos": "Dispensa normal · Art. 75-II · Serviços",
    "dispensa_75_ii_compras_servicos_inclusos": "Dispensa normal · Art. 75-II · Compras com serviços",
    # Dispensa rápida (chaves novas)
    "dispensa_rapida_75_i_manutencao_veiculos": "Dispensa rápida · Art. 75-I · Veículos",
    "dispensa_rapida_75_i_obras_engenharia": "Dispensa rápida · Art. 75-I · Obras e engenharia",
    "dispensa_rapida_75_ii_compras": "Dispensa rápida · Art. 75-II · Compras",
    "dispensa_rapida_75_ii_servicos": "Dispensa rápida · Art. 75-II · Serviços",
    "dispensa_rapida_75_ii_compras_servicos_inclusos": "Dispensa rápida · Art. 75-II · Compras com serviços",
    # Inexigibilidade
    "inexigibilidade_74_i_manutencao_veiculos": "Inexigibilidade · Art. 74-I · Show artístico / veículos",
    "inexigibilidade_74_i_fornecedor_exclusivo": "Inexigibilidade · Art. 74-I · Fornecedor exclusivo",
}


def _promql_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def generations_by_package_display(
    selector: str = 'docmaster_document_operations_total{result="success",package!~"unknown|other"}',
) -> str:
    """Agrupa por nome legível (label tipo) a partir do package Prometheus."""
    expr = f'label_replace({selector}, "tipo", "$1", "package", "(.+)")'
    for key, label in PACKAGE_LABELS.items():
        expr = f'label_replace({expr}, "tipo", "{_promql_escape(label)}", "package", "{key}")'
    return f"sum({expr}) by (tipo)"


def row(id_, title, y, collapsed=False):
    return {"collapsed": collapsed, "gridPos": {"h": 1, "w": 24, "x": 0, "y": y}, "id": id_, "title": title, "type": "row"}


def instant(expr, ref="A"):
    """Query instantânea para painéis Stat (valor único)."""
    return {
        "datasource": DS,
        "expr": expr,
        "refId": ref,
        "instant": True,
        "range": False,
        "editorMode": "code",
    }


def instant_vector(expr, ref="A", legend_format="__auto"):
    """Várias séries com labels (prefeitura, package) — legendFormat define o nome visível."""
    return {
        "datasource": DS,
        "expr": expr,
        "refId": ref,
        "instant": True,
        "range": False,
        "legendFormat": legend_format,
        "editorMode": "code",
    }


def range_query(expr, ref="A", legend=None):
    t = {"datasource": DS, "expr": expr, "refId": ref, "range": True, "editorMode": "code", "legendFormat": legend or ""}
    return t


def period_delta(selector: str) -> str:
    """
    Soma no intervalo do Grafana. Usa increase() para funcionar com contadores novos
    (offset $__range falha quando não há amostra no início do período).
    """
    return f"sum(increase({selector}[$__range]))"


def count_interval(selector: str) -> str:
    """Por bucket de tempo (gráfico de linha) — só para ver distribuição, não somar picos."""
    return f"sum(increase({selector}[$__interval]))"


def total(selector: str) -> str:
    """Total acumulado no contador (não depende do período do Grafana)."""
    return f"sum({selector})"


def total_by(selector: str, label: str) -> str:
    return f"sum({selector}) by ({label})"


# Métrica antiga: label `tenant` (só UF, ex. SC). Nova: `prefeitura` = "Joinville (SC)".
# Ordem: tenant → prefeitura (prefeitura ganha). UF de 2 letras = dado antigo sem município.
def _selector_with_offset(selector: str, offset: str = "") -> str:
    """Aplica offset ao seletor de métrica (antes de agregações)."""
    if not offset:
        return selector
    return f"{selector} offset {offset}"


def metric_prefeitura_nome(selector: str) -> str:
    """Unifica label prefeitura (novo) e tenant (legado) em nome."""
    return f"""label_replace(
  label_replace(
    {selector},
    "nome", "$1", "tenant", "(.+)"
  ),
  "nome", "$1", "prefeitura", "(.+)"
)"""


def period_delta_by_nome(selector: str) -> str:
    """Tokens e gerações por prefeitura no intervalo (label prefeitura)."""
    return f"sum(increase({selector}[$__range])) by (prefeitura)"


def login_prefeitura_nome_chain(selector: str) -> str:
    return f"""label_replace(
  label_replace(
    label_replace(
      {selector},
      "nome", "$1", "tenant", "(.+)"
    ),
    "nome", "$1", "prefeitura", "(.+)"
  ),
  "nome", "Só UF ($1) — refaça login após deploy", "nome", "^([A-Z]{{2}})$"
)"""


def period_delta_login_by_nome(selector: str) -> str:
    return f"sum(increase({selector}[$__range])) by (prefeitura)"


def period_delta_by_result(selector: str) -> str:
    return f"sum(increase({selector}[$__range])) by (result)"


def period_delta_by_fluxo(selector: str = "docmaster_llm_tokens_total") -> str:
    return f"sum(increase({selector}[$__range])) by (fluxo)"


def llm_tokens_by_fluxo_display(selector: str = "docmaster_llm_tokens_total") -> str:
    """Agrupa tokens no período por fluxo com nomes legíveis."""
    expr = f"sum(increase({selector}[$__range])) by (fluxo)"
    for key, label in FLUXO_LABELS.items():
        expr = f'label_replace({expr}, "tipo", "{_promql_escape(label)}", "fluxo", "{key}")'
    return f'label_replace({expr}, "tipo", "$1", "fluxo", "(.+)")'


def p95_duration(operation: str) -> str:
    return (
        f'histogram_quantile(0.95, sum(rate('
        f'docmaster_document_operation_duration_seconds_bucket{{operation="{operation}",result="success"}}'
        f"[$__rate_interval])) by (le))"
    )


def p95_duration_by_prefeitura(operation: str) -> str:
    return (
        f"histogram_quantile(0.95, sum(rate("
        f'docmaster_document_operation_duration_seconds_bucket{{operation="{operation}",result="success"}}'
        f"[$__rate_interval])) by (le, prefeitura))"
    )


def login_by_prefeitura_display(selector: str = 'docmaster_auth_login_total{result="success"}') -> str:
    return f"sum({login_prefeitura_nome_chain(selector)}) by (nome)"


LOGIN_NOME_MAPPINGS = {
    "staff": "Equipe DocMaster (staff)",
    "sem_prefeitura": "Sem prefeitura",
    "anonymous": "Não identificado",
}

RESULT_LABELS = {
    "success": "Sucesso",
    "error": "Erro",
}

OPERATION_LABELS = {
    "fill_tr_slots": "Preencher slots (IA)",
    "gerar_llm": "Gerar via LLM",
    "gerar_tr_e_dfd": "TR + DFD + Ofício",
    "gerar_tr_modelo": "TR modelo",
}

FLUXO_LABELS = {
    "fill_tr_slots": "Preencher slots (IA)",
    "gerar_tr_e_dfd": "TR + DFD + Ofício",
    "gerar_llm": "Gerar documento (LLM)",
    "gerar_tr_modelo": "TR modelo",
    "unknown": "Outro fluxo",
}

DESC_STAT_TOTAL = (
    "Consulta instantânea: total atual do contador (independente do intervalo do Grafana)."
)
DESC_STAT_PERIODO = "Soma no intervalo selecionado no Grafana."


def stat(id_, title, y, x, w, expr, desc="", *, period=False, unit="none", decimals=0):
    return {
        "datasource": DS,
        "description": desc or (DESC_STAT_PERIODO if period else DESC_STAT_TOTAL),
        "fieldConfig": {
            "defaults": {"decimals": decimals, "noValue": "0", "unit": unit},
            "overrides": [],
        },
        "gridPos": {"h": 4, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {
            "colorMode": "value",
            "graphMode": "none",
            "justifyMode": "center",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": "auto",
        },
        "targets": [instant(expr)],
        "title": title,
        "type": "stat",
    }


def stat_duration(id_, title, y, x, w, expr, desc=""):
    """p95 exige query de intervalo (rate/histogram), não instant."""
    return {
        "datasource": DS,
        "description": desc
        or "Percentil 95 da duração no intervalo do Grafana (requer tráfego recente).",
        "fieldConfig": {
            "defaults": {"decimals": 1, "noValue": "—", "unit": "s"},
            "overrides": [],
        },
        "gridPos": {"h": 4, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {
            "colorMode": "value",
            "graphMode": "none",
            "justifyMode": "center",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": "auto",
        },
        "targets": [range_query(expr)],
        "title": title,
        "type": "stat",
    }


def prom_table_p95_prefeitura(id_, title, y, x, w, h, operation, desc=""):
    value_mappings = [
        {"type": "value", "options": {k: {"text": v} for k, v in LOGIN_NOME_MAPPINGS.items()}}
    ]
    return {
        "datasource": DS,
        "description": desc
        or "Tempo até concluir a operação (p95). Quanto menor, mais rápido para o usuário.",
        "fieldConfig": {
            "defaults": {"decimals": 1, "unit": "s"},
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "Prefeitura"},
                    "properties": [{"id": "mappings", "value": value_mappings}],
                },
                {
                    "matcher": {"id": "byName", "options": "p95"},
                    "properties": [{"id": "custom.width", "value": 80}],
                },
            ],
        },
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {
            "cellHeight": "sm",
            "footer": {"countRows": False, "show": False},
            "showHeader": True,
            "sortBy": [{"desc": True, "displayName": "p95"}],
        },
        "targets": [
            {
                "datasource": DS,
                "expr": p95_duration_by_prefeitura(operation),
                "refId": "A",
                "instant": False,
                "range": True,
                "format": "table",
                "editorMode": "code",
            }
        ],
        "transformations": [
            {
                "id": "organize",
                "options": {
                    "excludeByName": {"Time": True, "__name__": True, "le": True},
                    "renameByName": {"prefeitura": "Prefeitura", "Value": "p95"},
                },
            }
        ],
        "title": title,
        "type": "table",
    }


def pie_period(id_, title, y, x, w, h, expr, desc="", value_mappings=None):
    overrides = []
    if value_mappings:
        overrides.append(
            {
                "matcher": {"id": "byRegexp", "options": ".*"},
                "properties": [{"id": "mappings", "value": [value_mappings]}],
            }
        )
    return {
        "datasource": DS,
        "description": desc,
        "fieldConfig": {
            "defaults": {"decimals": 0, "unit": "none"},
            "overrides": overrides,
        },
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {
            "legend": {"displayMode": "table", "placement": "right", "values": ["value", "percent"]},
            "pieType": "donut",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "tooltip": {"mode": "single"},
        },
        "targets": [
            {
                "datasource": DS,
                "expr": expr,
                "refId": "A",
                "instant": True,
                "range": False,
                "legendFormat": "{{result}}",
                "editorMode": "code",
            }
        ],
        "title": title,
        "type": "piechart",
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


def prom_table_by_nome(id_, title, y, x, w, h, expr, value_col="Logins", desc=""):
    """Tabela instantânea: coluna Prefeitura + contagem (compatível com tenant/prefeitura)."""
    value_mappings = [
        {"type": "value", "options": {k: {"text": v} for k, v in LOGIN_NOME_MAPPINGS.items()}}
    ]
    return {
        "datasource": DS,
        "description": desc
        or (
            "Compatível com métrica antiga (label tenant) e nova (prefeitura com nome do município)."
        ),
        "fieldConfig": {
            "defaults": {"decimals": 0, "min": 0, "unit": "none"},
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "Prefeitura"},
                    "properties": [{"id": "mappings", "value": value_mappings}],
                }
            ],
        },
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {
            "cellHeight": "sm",
            "footer": {"countRows": False, "show": False},
            "showHeader": True,
            "sortBy": [{"desc": True, "displayName": value_col}],
        },
        "targets": [
            {
                "datasource": DS,
                "expr": expr,
                "refId": "A",
                "instant": True,
                "range": False,
                "format": "table",
                "editorMode": "code",
            }
        ],
        "transformations": [
            {
                "id": "organize",
                "options": {
                    "excludeByName": {"Time": True, "__name__": True},
                    "renameByName": {
                        "prefeitura": "Prefeitura",
                        "nome": "Prefeitura",
                        "Value": value_col,
                    },
                },
            }
        ],
        "title": title,
        "type": "table",
    }


def prom_table_generations(id_, title, y, x, w, h, expr, desc=""):
    """Tabela compacta: tipo de geração legível + contagem."""
    return {
        "datasource": DS,
        "description": desc
        or "Nomes legíveis por tipo (dispensa normal, dispensa rápida, inexigibilidade).",
        "fieldConfig": {
            "defaults": {
                "decimals": 0,
                "min": 0,
                "unit": "none",
                "custom": {"align": "auto", "cellOptions": {"type": "auto"}, "inspect": False},
            },
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "Gerações"},
                    "properties": [
                        {"id": "custom.width", "value": 90},
                        {"id": "custom.cellOptions", "value": {"type": "color-text"}},
                    ],
                },
                {
                    "matcher": {"id": "byName", "options": "Tipo de geração"},
                    "properties": [{"id": "custom.width", "value": 420}],
                },
            ],
        },
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {
            "cellHeight": "sm",
            "footer": {"countRows": False, "show": False},
            "showHeader": True,
            "sortBy": [{"desc": True, "displayName": "Gerações"}],
        },
        "targets": [
            {
                "datasource": DS,
                "expr": expr,
                "refId": "A",
                "instant": True,
                "range": False,
                "format": "table",
                "editorMode": "code",
            }
        ],
        "transformations": [
            {
                "id": "organize",
                "options": {
                    "excludeByName": {"Time": True, "__name__": True},
                    "renameByName": {"tipo": "Tipo de geração", "Value": "Gerações"},
                },
            }
        ],
        "title": title,
        "type": "table",
    }


def bargauge_by_label(id_, title, y, x, w, h, expr, legend_format, value_mappings=None, desc=""):
    """
    Barras horizontais: nome da série = legendFormat (ex. {{prefeitura}}).
    Mais confiável que tabela com transformações Prometheus no Grafana.
    """
    overrides = []
    if value_mappings:
        overrides.append(
            {
                "matcher": {"id": "byRegexp", "options": ".*"},
                "properties": [{"id": "mappings", "value": [value_mappings]}],
            }
        )
    return {
        "datasource": DS,
        "description": desc
        or (
            "Cada barra é uma prefeitura ou pacote. "
            "O nome vem dos labels da métrica no Prometheus (prefeitura ou package)."
        ),
        "fieldConfig": {
            "defaults": {
                "decimals": 0,
                "min": 0,
                "unit": "none",
                "color": {"mode": "palette-classic"},
            },
            "overrides": overrides,
        },
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {
            "displayMode": "basic",
            "minVizHeight": 18,
            "minVizWidth": 0,
            "namePlacement": "left",
            "orientation": "horizontal",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "showUnfilled": True,
            "sizing": "manual",
            "valueMode": "color",
            "legend": {"displayMode": "hidden"},
        },
        "targets": [instant_vector(expr, legend_format=legend_format)],
        "title": title,
        "type": "bargauge",
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


panels = []
y = 0
panels.append(
    text_panel(
        299,
        y,
        "**Operação (topo)** = foco no período do Grafana: erros, velocidade (p95) e prefeitura. "
        "**Totais acumulados** = desde o último restart do backend. "
        "Se o backend reiniciou no meio do intervalo, o período pode subestimar.",
    )
)
y += 3

# --- Operação: erros, rapidez, prefeituras (prioridade gestão) ---
panels.append(row(280, "Operação — período selecionado (erros, velocidade, prefeituras)", y))
y += 1
panels += [
    stat(
        281,
        "Erros de geração",
        y,
        0,
        4,
        period_delta('docmaster_document_operations_total{result="error"}'),
        period=True,
    ),
    stat(
        282,
        "Falhas de login",
        y,
        4,
        4,
        period_delta('docmaster_auth_login_total{result!="success"}'),
        period=True,
    ),
    stat(
        283,
        "Erros IA / PNCP",
        y,
        8,
        4,
        period_delta('docmaster_platform_events_total{result="error"}'),
        period=True,
    ),
    stat(
        284,
        "Gerações OK",
        y,
        12,
        4,
        period_delta('docmaster_document_operations_total{result="success"}'),
        period=True,
    ),
    stat_duration(285, "p95 Slots IA", y, 16, 4, p95_duration("fill_tr_slots")),
    stat_duration(286, "p95 TR + DFD", y, 20, 4, p95_duration("gerar_tr_e_dfd")),
]
y += 4

panels.append(row(275, "Tokens LLM — período selecionado", y))
y += 1
panels += [
    stat(
        276,
        "Tokens entrada",
        y,
        0,
        6,
        period_delta('docmaster_llm_tokens_total{direction="entrada"}'),
        period=True,
        unit="short",
    ),
    stat(
        277,
        "Tokens saída",
        y,
        6,
        6,
        period_delta('docmaster_llm_tokens_total{direction="saida"}'),
        period=True,
        unit="short",
    ),
    stat(
        278,
        "Tokens total",
        y,
        12,
        6,
        period_delta("docmaster_llm_tokens_total"),
        period=True,
        unit="short",
        desc="Soma de entrada + saída no intervalo (métrica docmaster_llm_tokens_total no backend).",
    ),
    stat(
        279,
        "Chamadas LLM (proxy)",
        y,
        18,
        6,
        period_delta('docmaster_platform_events_total{module="llm",result="success"}'),
        period=True,
        desc="Eventos do proxy Django → llm_api (não inclui chamadas internas rag→llm).",
    ),
]
y += 4
panels.append(
    prom_table_by_nome(
        271,
        "Tokens por prefeitura (período)",
        y,
        0,
        12,
        7,
        period_delta_by_nome("docmaster_llm_tokens_total"),
        value_col="Tokens",
        desc="Entrada + saída agregados por município no intervalo.",
    )
)
panels.append(
    prom_table_generations(
        272,
        "Tokens por fluxo (período)",
        y,
        12,
        12,
        7,
        llm_tokens_by_fluxo_display(),
        desc="Distribuição por operação (slots, TR+DFD, etc.). Requer backend com record_llm_token_usage.",
    )
)
y += 7

panels.append(
    prom_table_by_nome(
        287,
        "Gerações OK por prefeitura (período)",
        y,
        0,
        8,
        7,
        period_delta_by_nome('docmaster_document_operations_total{result="success"}'),
        value_col="Gerações",
        desc="Operações concluídas com sucesso no intervalo, por município.",
    )
)
panels.append(
    prom_table_by_nome(
        288,
        "Erros de geração por prefeitura (período)",
        y,
        8,
        8,
        7,
        period_delta_by_nome('docmaster_document_operations_total{result="error"}'),
        value_col="Erros",
        desc="Falhas ao gerar documentos (resposta ok=false ou exceção).",
    )
)
panels.append(
    prom_table_by_nome(
        289,
        "Falhas de login por prefeitura (período)",
        y,
        16,
        8,
        7,
        period_delta_login_by_nome('docmaster_auth_login_total{result!="success"}'),
        value_col="Falhas",
        desc="Senha inválida, bloqueio, prefeitura incorreta, etc.",
    )
)
y += 7

result_pie_mappings = {"type": "value", "options": {k: {"text": v} for k, v in RESULT_LABELS.items()}}

panels.append(
    pie_period(
        290,
        "TR + DFD — sucesso vs erro (período)",
        y,
        0,
        8,
        7,
        period_delta('docmaster_document_operations_total{operation="gerar_tr_e_dfd"}'),
        desc="Proporção de gerações TR+DFD+Ofício que concluíram com sucesso no intervalo.",
        value_mappings=result_pie_mappings,
    )
)
panels.append(
    bar_period_breakdown(
        291,
        "Erros por tipo de operação (período)",
        y,
        8,
        16,
        7,
        [
            ('docmaster_document_operations_total{operation="fill_tr_slots",result="error"}', "Slots IA"),
            ('docmaster_document_operations_total{operation="gerar_tr_e_dfd",result="error"}', "TR + DFD"),
            ('docmaster_document_operations_total{operation="gerar_llm",result="error"}', "Gerar LLM"),
            ('docmaster_platform_events_total{module="llm",result="error"}', "Proxy LLM"),
            ('docmaster_platform_events_total{module=~"pncp_.*",result="error"}', "PNCP"),
        ],
        desc="Onde mais falhou no intervalo — priorize correção nos maiores valores.",
    )
)
y += 7

panels.append(
    prom_table_p95_prefeitura(
        292,
        "Rapidez TR + DFD por prefeitura (p95 no período)",
        y,
        0,
        14,
        6,
        "gerar_tr_e_dfd",
    )
)
panels.append(
    prom_table_by_nome(
        293,
        "Erros IA / PNCP por prefeitura (período)",
        y,
        14,
        10,
        6,
        period_delta_by_nome('docmaster_platform_events_total{result="error"}'),
        value_col="Erros",
        desc="Falhas em chamadas ao LLM, análise ou serviços PNCP.",
    )
)
y += 6

panels.append(
    ts_duration(
        294,
        "Rapidez ao longo do tempo (p95)",
        y,
        0,
        24,
        7,
        [
            (p95_duration("fill_tr_slots"), "Slots IA"),
            (p95_duration("gerar_tr_e_dfd"), "TR + DFD"),
            (p95_duration("gerar_llm"), "Gerar LLM"),
        ],
        desc="Quanto menor a linha, mais rápido o fluxo naquele momento.",
    )
)
y += 7

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
    prom_table_by_nome(
        332,
        "Logins OK — por prefeitura (total acumulado)",
        y,
        0,
        12,
        8,
        login_by_prefeitura_display(),
        desc=(
            "Exige backend com label prefeitura (nome + UF). Métrica antiga gravava só a UF (ex.: SC). "
            "Após deploy do backend, faça login de novo para aparecer \"Joinville (SC)\"."
        ),
    )
)
panels.append(
    prom_table_generations(
        341,
        "Gerações por tipo de documento (total acumulado)",
        y,
        12,
        12,
        7,
        generations_by_package_display(),
        desc=(
            "Dispensa normal, dispensa rápida e inexigibilidade com nomes legíveis. "
            "Séries antigas sem distinção rápida/normal aparecem como «Dispensa · Art. …». "
            "Após deploy do backend + frontend, novas gerações rápidas usam chave dispensa_rapida_*."
        ),
    )
)
y += 7

# --- No período Grafana (delta de contador — coerente com o intervalo) ---
panels.append(row(3010, "No período selecionado no Grafana", y))
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

panels.append(
    bar_period_breakdown(
        3071,
        "Operações no período (detalhe — não some manualmente)",
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
        "Cada barra é um tipo de operação; um fluxo TR+DFD pode incluir preenchimento de slots antes.",
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
        "Cada ponto são gerações naquele intervalo de tempo. Zero = nenhuma naquele minuto ou hora.",
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
    "description": "Layout v21 — increase() no período (contadores novos); tokens LLM por prefeitura/fluxo.",
    "fiscalYearStartMonth": 0,
    "graphTooltip": 1,
    "id": None,
    "links": [],
    "panels": panels,
    "refresh": "1m",
    "schemaVersion": 39,
    "tags": ["docmaster", "backend", "django", "layout-v21"],
    "templating": {"list": []},
    "time": {"from": "now-24h", "to": "now"},
    "timezone": "browser",
    "title": "DocMaster — Backend Django",
    "uid": "docmaster-backend",
    "version": 21,
}

OUT.write_text(json.dumps(dash, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Wrote {OUT} ({len(panels)} panels)")
