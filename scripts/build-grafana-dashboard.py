#!/usr/bin/env python3
"""Gera config/grafana/provisioning/dashboards/json/docmaster-backend.json"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DS = {"type": "prometheus", "uid": "prometheus"}


def _resolve_repo_root() -> Path:
    """
    Raiz do docmaster-core (pasta com config/grafana/...).

    Use DOCMASTER_ROOT=~/docmaster-core se o script estiver copiado em ~/scripts/.
    """
    env = (os.environ.get("DOCMASTER_ROOT") or "").strip()
    if env:
        root = Path(env).expanduser().resolve()
        if (root / "config/grafana").is_dir():
            return root
        print(f"ERRO: DOCMASTER_ROOT={root} não contém config/grafana/", file=sys.stderr)
        sys.exit(1)

    here = Path(__file__).resolve().parent
    candidates = [here.parent, here.parent.parent, Path.cwd(), Path.cwd() / "docmaster-core"]
    for root in candidates:
        root = root.resolve()
        if (root / "config/grafana").is_dir():
            return root

    print(
        "ERRO: não encontrei a raiz do repo (config/grafana/).\n"
        "  cd ~/docmaster-core && python3 scripts/build-grafana-dashboard.py\n"
        "  ou: DOCMASTER_ROOT=~/docmaster-core python3 /caminho/build-grafana-dashboard.py",
        file=sys.stderr,
    )
    sys.exit(1)


ROOT = _resolve_repo_root()
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


# Operações de documento com IA (contagem geral).
_LLM_TOKEN_OPERATIONS = "fill_tr_slots|gerar_tr_e_dfd|gerar_llm"
_LLM_OPS_SELECTOR = (
    f'docmaster_document_operations_total{{result="success",operation=~"{_LLM_TOKEN_OPERATIONS}"}}'
)
# Média de tokens/op.: gerar_tr_e_dfd costuma não gravar tokens (render só com override).
_LLM_TOKEN_DENOM_OPERATIONS = "fill_tr_slots|gerar_llm"
_LLM_TOKEN_DENOM_SELECTOR = (
    f'docmaster_document_operations_total{{result="success",operation=~"{_LLM_TOKEN_DENOM_OPERATIONS}"}}'
)
# Tokens: só fluxos do pipeline documento (exclui legado llm_proxy_* no TSDB).
_LLM_TOKENS_METRIC = (
    f'docmaster_llm_tokens_total{{fluxo=~"{_LLM_TOKEN_OPERATIONS}"}}'
)
# Tipos de geração com pacote conhecido (evita «other»/unknown de rotas antigas).
_TIPO_GERACAO_FILTER = "dispensa_normal|dispensa_rapida|inexigibilidade|etp"
_OPS_BY_TIPO_SELECTOR = (
    f'docmaster_document_operations_total{{tipo_geracao=~"{_TIPO_GERACAO_FILTER}"}}'
)

TIPO_GERACAO_LABELS = {
    "dispensa_normal": "Dispensa normal",
    "dispensa_rapida": "Dispensa rápida",
    "inexigibilidade": "Inexigibilidade",
    "etp": "ETP",
    "other": "Outros",
}


def _llm_ops_selector(*, tipo_geracao: str | None = None, for_token_avg: bool = False) -> str:
    base = _LLM_TOKEN_DENOM_SELECTOR if for_token_avg else _LLM_OPS_SELECTOR
    if tipo_geracao:
        return f'{base[:-1]},tipo_geracao="{tipo_geracao}"}}'
    return base


def avg_tokens_for_tipo(tipo_geracao: str, *, direction: str | None = None) -> str:
    """Média de tokens por operação no período, para um tipo de geração."""
    tok = f'{_LLM_TOKENS_METRIC[:-1]},tipo_geracao="{tipo_geracao}"}}'
    if direction:
        tok = f'{_LLM_TOKENS_METRIC[:-1]},tipo_geracao="{tipo_geracao}",direction="{direction}"}}'
    ops = _llm_ops_selector(tipo_geracao=tipo_geracao, for_token_avg=True)
    return f"(sum(increase({tok}[$__range])) / clamp_min(sum(increase({ops}[$__range])), 1))"


def avg_tokens_by_tipo_geracao(*, direction: str | None = None) -> str:
    tok = _LLM_TOKENS_METRIC
    if direction:
        tok = f'{_LLM_TOKENS_METRIC[:-1]},direction="{direction}"}}'
    ops = _llm_ops_selector(for_token_avg=True)
    return f"""(
sum(increase({tok}[$__range])) by (tipo_geracao)
/ on(tipo_geracao) group_left()
clamp_min(sum(increase({ops}[$__range])) by (tipo_geracao), 1)
)"""


def avg_tokens_by_tipo_geracao_display(*, direction: str | None = None) -> str:
    expr = avg_tokens_by_tipo_geracao(direction=direction)
    for key, label in TIPO_GERACAO_LABELS.items():
        expr = f'label_replace({expr}, "tipo", "{_promql_escape(label)}", "tipo_geracao", "{key}")'
    return f'label_replace({expr}, "tipo", "$1", "tipo_geracao", "(.+)")'


def operations_by_tipo_geracao_period(*, result: str = "success") -> str:
    """Contagem de operações no período, agrupadas por tipo_geracao com nome legível."""
    sel = f'{_OPS_BY_TIPO_SELECTOR[:-1]},result="{result}"}}'
    expr = f"sum(increase({sel}[$__range])) by (tipo_geracao)"
    for key, label in TIPO_GERACAO_LABELS.items():
        expr = f'label_replace({expr}, "tipo", "{_promql_escape(label)}", "tipo_geracao", "{key}")'
    return f'label_replace({expr}, "tipo", "$1", "tipo_geracao", "(.+)")'


def operations_by_tipo_geracao_total(*, result: str = "success") -> str:
    sel = f'{_OPS_BY_TIPO_SELECTOR[:-1]},result="{result}"}}'
    expr = f"sum({sel}) by (tipo_geracao)"
    for key, label in TIPO_GERACAO_LABELS.items():
        expr = f'label_replace({expr}, "tipo", "{_promql_escape(label)}", "tipo_geracao", "{key}")'
    return f'label_replace({expr}, "tipo", "$1", "tipo_geracao", "(.+)")'


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

AUTH_LOGIN_RESULT_LABELS = {
    "success": "Sucesso",
    "failure": "Credenciais inválidas",
    "locked": "Conta bloqueada",
    "forbidden_prefeitura": "Prefeitura não permitida",
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


def prom_table_generations(id_, title, y, x, w, h, expr, desc="", *, value_col="Gerações"):
    """Tabela compacta: tipo de geração legível + valor (contagem ou média)."""
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
                    "matcher": {"id": "byName", "options": value_col},
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
                    "renameByName": {"tipo": "Tipo de geração", "Value": value_col},
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
        "**Totais acumulados** = desde o último restart do backend (contadores zeram no deploy). "
        "Tokens: só fill-tr-slots, gerar-tr-e-dfd e gerar_llm (não inclui /api/llm do formulário). "
        "Tipos: dispensa normal/rápida, inexigibilidade, ETP — séries «other»/unknown ficam fora dos painéis por tipo.",
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
        period_delta(
            'docmaster_auth_login_total{result=~"failure|locked|forbidden_prefeitura"}'
        ),
        period=True,
        desc="Tentativas de login sem sucesso (credenciais, bloqueio ou prefeitura).",
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

panels.append(row(275, "Tokens LLM — média por tipo de geração (período)", y))
y += 1
panels += [
    stat(
        276,
        "Dispensa normal",
        y,
        0,
        6,
        avg_tokens_for_tipo("dispensa_normal"),
        period=True,
        unit="short",
        decimals=0,
        desc="Média de tokens (entrada+saída) por operação com LLM (fill-tr-slots / gerar_llm). TR+DFD sem 2ª passagem IA não entra no denominador.",
    ),
    stat(
        277,
        "Dispensa rápida",
        y,
        6,
        6,
        avg_tokens_for_tipo("dispensa_rapida"),
        period=True,
        unit="short",
        decimals=0,
        desc="Média de tokens por operação — fluxo simplificado Art. 75.",
    ),
    stat(
        278,
        "Inexigibilidade",
        y,
        12,
        6,
        avg_tokens_for_tipo("inexigibilidade"),
        period=True,
        unit="short",
        decimals=0,
        desc="Média de tokens por operação — Art. 74.",
    ),
    stat(
        279,
        "ETP",
        y,
        18,
        6,
        avg_tokens_for_tipo("etp"),
        period=True,
        unit="short",
        decimals=0,
        desc="Média de tokens por operação — geração ETP (gerar_llm / documento LLM).",
    ),
]
y += 4
panels.append(
    prom_table_generations(
        271,
        "Média total por tipo",
        y,
        0,
        8,
        5,
        avg_tokens_by_tipo_geracao_display(),
        value_col="Tokens/op.",
        desc="Comparativo entre tipos de geração no intervalo.",
    )
)
panels.append(
    prom_table_generations(
        272,
        "Média entrada por tipo",
        y,
        8,
        8,
        5,
        avg_tokens_by_tipo_geracao_display(direction="entrada"),
        value_col="Entrada/op.",
        desc="Tokens de prompt (entrada) por operação.",
    )
)
panels.append(
    prom_table_generations(
        273,
        "Média saída por tipo",
        y,
        16,
        8,
        5,
        avg_tokens_by_tipo_geracao_display(direction="saida"),
        value_col="Saída/op.",
        desc="Tokens gerados pelo modelo (saída) por operação.",
    )
)
y += 5
panels.append(
    prom_table_generations(
        274,
        "Gerações OK por tipo (período)",
        y,
        0,
        12,
        5,
        operations_by_tipo_geracao_period(result="success"),
        value_col="Gerações",
        desc="Contagem de operações de documento no intervalo, por família (dispensa normal/rápida, inexigibilidade, ETP).",
    )
)
panels.append(
    prom_table_generations(
        2741,
        "Erros por tipo (período)",
        y,
        12,
        12,
        5,
        operations_by_tipo_geracao_period(result="error"),
        value_col="Erros",
        desc="Falhas de geração agrupadas por tipo_geracao.",
    )
)
y += 5

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
        period_delta_login_by_nome(
            'docmaster_auth_login_total{result=~"failure|locked|forbidden_prefeitura"}'
        ),
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
        "Gerações por pacote (total acumulado)",
        y,
        12,
        8,
        7,
        generations_by_package_display(),
        desc=(
            "Detalhe por chave package (cada formulário). "
            "Séries antigas sem distinção rápida/normal podem aparecer só como chave técnica."
        ),
    )
)
panels.append(
    prom_table_generations(
        342,
        "Gerações por tipo (total acumulado)",
        y,
        20,
        4,
        7,
        operations_by_tipo_geracao_total(result="success"),
        value_col="Total",
        desc="Totais desde o último restart, agrupados por tipo_geracao.",
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

# --- Infra / saúde (mesmo scrape Prometheus job=backend que alimenta docmaster_*) ---
_JOB = "backend"
_DJANGO_VIEWS_APP = 'view!~"prometheus-django-metrics|admin.*"'


panels.append(
    row(
        350,
        "Infraestrutura — scrape Prometheus e API",
        y,
        collapsed=False,
    )
)
y += 1
panels.append(
    text_panel(
        349,
        y,
        "Esta secção usa o **mesmo job Prometheus `backend`** que o resto do dashboard "
        f"(`config/prometheus.yml` → /metrics). "
        "**Backend UP** vem do Prometheus (`up`), não do Django. "
        "Pedidos HTTP excluem o scrape de `/metrics`. "
        "Duração p95 usa `docmaster_document_operation_duration_seconds` (igual à secção Operação). "
        "O endpoint Django **não** exporta CPU/RSS do processo.",
    )
)
y += 3
panels += [
    stat(
        351,
        "Scrape UP",
        y,
        0,
        4,
        f'up{{job="{_JOB}"}}',
        desc="1 = Prometheus alcança https://api.docmasteria.com.br/metrics. 0 = target down.",
    ),
    stat(
        355,
        "Workers métricas",
        y,
        4,
        4,
        f'max(docmaster_metrics_active{{job="{_JOB}"}})',
        desc="Workers Gunicorn com docmaster_* (esperado ≈2).",
    ),
    stat(
        352,
        "HTTP app (período)",
        y,
        8,
        4,
        period_delta(
            f"sum(django_http_requests_total_by_view_transport_method_total{{job=\"{_JOB}\",{_DJANGO_VIEWS_APP}}})"
        ),
        period=True,
        desc="Pedidos à API no intervalo, sem contar o scrape GET /metrics.",
    ),
    stat(
        353,
        "5xx (período)",
        y,
        12,
        4,
        period_delta(
            f'sum(django_http_responses_total_by_status_total{{job="{_JOB}",status=~"5.."}})'
        ),
        period=True,
        desc="Respostas HTTP 5xx (proxy timeout, crash, 502 do upstream).",
    ),
    stat(
        354,
        "4xx (período)",
        y,
        16,
        4,
        period_delta(
            f'sum(django_http_responses_total_by_status_total{{job="{_JOB}",status=~"4.."}})'
        ),
        period=True,
        desc="Respostas 401/403/404/405 etc.",
    ),
    stat(
        358,
        "Erros docmaster (período)",
        y,
        20,
        4,
        period_delta(
            f'sum(docmaster_document_operations_total{{job="{_JOB}",result="error"}})'
        ),
        period=True,
        desc="Falhas de geração contabilizadas pelo decorator (mesma fonte que «Erros de geração» no topo).",
    ),
]
y += 4
panels.append(
    ts_duration(
        356,
        "Duração p95 geração (docmaster)",
        y,
        0,
        14,
        7,
        [
            (p95_duration("fill_tr_slots"), "Slots IA"),
            (p95_duration("gerar_tr_e_dfd"), "TR + DFD"),
            (p95_duration("gerar_llm"), "Gerar LLM"),
        ],
        desc="Histograma de negócio — visível assim que houver tráfego real (não depende de django_http_latency).",
    )
)
panels.append(
    ts_counts(
        357,
        "HTTP e erros no tempo",
        y,
        14,
        10,
        7,
        [
            (
                count_interval(
                    f'django_http_responses_total_by_status_total{{job="{_JOB}",status=~"5.."}}'
                ),
                "5xx",
            ),
            (
                count_interval(
                    f'django_http_responses_total_by_status_total{{job="{_JOB}",status=~"4.."}}'
                ),
                "4xx",
            ),
            (
                count_interval(
                    f'docmaster_document_operations_total{{job="{_JOB}",result="error"}}'
                ),
                "Erros geração",
            ),
        ],
        desc="Tendência no intervalo do Grafana (cada ponto = bucket $__interval).",
    )
)

dash = {
    "annotations": {"list": []},
    "editable": False,
    "description": "Layout v26 — secção infra alinhada ao scrape Prometheus; tokens e tipos limpos.",
    "fiscalYearStartMonth": 0,
    "graphTooltip": 1,
    "id": None,
    "links": [],
    "panels": panels,
    "refresh": "1m",
    "schemaVersion": 39,
    "tags": ["docmaster", "backend", "django", "layout-v26"],
    "templating": {"list": []},
    "time": {"from": "now-24h", "to": "now"},
    "timezone": "browser",
    "title": "DocMaster — Backend Django",
    "uid": "docmaster-backend",
    "version": 26,
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(dash, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

panel_ids = [p.get("id") for p in panels if p.get("id") is not None]
dupes = sorted({i for i in panel_ids if panel_ids.count(i) > 1})
if dupes:
    print(f"AVISO: IDs de painel duplicados: {dupes}", file=sys.stderr)
    sys.exit(1)

print(f"Repo:  {ROOT}")
print(f"Wrote: {OUT} ({len(panels)} panels, layout-v26)")
