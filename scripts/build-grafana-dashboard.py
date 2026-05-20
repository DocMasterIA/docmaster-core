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


def instant(expr, ref="A", legend: str | None = None):
    """Query instantânea para painéis Stat / bargauge (valor único por série)."""
    t = {
        "datasource": DS,
        "expr": expr,
        "refId": ref,
        "instant": True,
        "range": False,
        "editorMode": "code",
    }
    if legend is not None:
        t["legendFormat"] = legend
    return t


def period_range(expr, ref="A"):
    """
    Soma/média no intervalo do dashboard — query em modo range (não instant).

    instant + increase[$__range] em painéis Stat costuma devolver vazio no Grafana 10+;
    range + reduceOptions lastNotNull usa o último ponto (= increase no $__range).
    """
    return {
        "datasource": DS,
        "expr": expr,
        "refId": ref,
        "range": True,
        "instant": False,
        "editorMode": "code",
        "legendFormat": "",
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
# Tokens e invocações LLM (mesmos fluxos; média = tokens / invocações).
_LLM_TOKEN_FLUXOS = "fill_tr_slots|gerar_tr_e_dfd|gerar_llm|clausulas_llm"
_LLM_TOKENS_METRIC = f'docmaster_llm_tokens_total{{fluxo=~"{_LLM_TOKEN_FLUXOS}"}}'
_LLM_INVOCATIONS_METRIC = f'docmaster_llm_invocations_total{{fluxo=~"{_LLM_TOKEN_FLUXOS}"}}'
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


def _tokens_selector(*, tipo_geracao: str | None = None, direction: str | None = None) -> str:
    parts = [f'fluxo=~"{_LLM_TOKEN_FLUXOS}"']
    if tipo_geracao:
        parts.append(f'tipo_geracao="{tipo_geracao}"')
    if direction:
        parts.append(f'direction="{direction}"')
    return f'docmaster_llm_tokens_total{{{",".join(parts)}}}'


def _invocations_selector(*, tipo_geracao: str | None = None) -> str:
    parts = [f'fluxo=~"{_LLM_TOKEN_FLUXOS}"']
    if tipo_geracao:
        parts.append(f'tipo_geracao="{tipo_geracao}"')
    return f'docmaster_llm_invocations_total{{{",".join(parts)}}}'


def total_tokens_for_tipo(tipo_geracao: str) -> str:
    """Soma entrada+saída no período (sempre visível após gerar cláusulas ou fill-tr-slots)."""
    return f"sum(increase({_tokens_selector(tipo_geracao=tipo_geracao)}[$__range]))"


def generations_ok_for_tipo(tipo_geracao: str) -> str:
    """Gerações de documento OK no período (inclui TR+DFD sem tokens LLM)."""
    return (
        f'sum(increase(docmaster_document_operations_total{{result="success",'
        f'tipo_geracao="{tipo_geracao}"}}[$__range]))'
    )


def avg_tokens_for_tipo(tipo_geracao: str, *, direction: str | None = None) -> str:
    """Média tokens por chamada LLM (invocações = 1 por geração de cláusulas / fill-tr-slots / etc.)."""
    tok = f"sum(increase({_tokens_selector(tipo_geracao=tipo_geracao, direction=direction)}[$__range]))"
    inv = f"sum(increase({_invocations_selector(tipo_geracao=tipo_geracao)}[$__range]))"
    return f"({tok} / clamp_min({inv}, 1))"


def avg_tokens_by_tipo_geracao(*, direction: str | None = None) -> str:
    tok = f"sum(increase({_tokens_selector(direction=direction)}[$__range])) by (tipo_geracao)"
    inv = f"sum(increase({_LLM_INVOCATIONS_METRIC}[$__range])) by (tipo_geracao)"
    return f"""(
{tok}
/ on(tipo_geracao) group_left()
clamp_min({inv}, 1)
)"""


def avg_tokens_by_tipo_geracao_display(*, direction: str | None = None) -> str:
    expr = avg_tokens_by_tipo_geracao(direction=direction)
    for key, label in TIPO_GERACAO_LABELS.items():
        expr = f'label_replace({expr}, "tipo", "{_promql_escape(label)}", "tipo_geracao", "{key}")'
    return f'label_replace({expr}, "tipo", "$1", "tipo_geracao", "(.+)")'


def operations_by_operation_period(*, result: str = "success") -> str:
    """Contagem no período por operation com rótulo legível (uma query → bargauge estável)."""
    sel = f'docmaster_document_operations_total{{result="{result}"}}'
    expr = f"sum(increase({sel}[$__range])) by (operation)"
    for key, label in OPERATION_LABELS.items():
        expr = f'label_replace({expr}, "op_label", "{_promql_escape(label)}", "operation", "{key}")'
    return f'label_replace({expr}, "op_label", "$1", "operation", "(.+)")'



def operations_by_tipo_geracao_period(*, result: str = "success", operation: str | None = None) -> str:
    """Contagem de operações no período, agrupadas por tipo_geracao com nome legível."""
    if operation:
        sel = f'docmaster_document_operations_total{{result="{result}",operation="{operation}"}}'
    else:
        sel = f'docmaster_document_operations_total{{result="{result}"}}'
    expr = f"sum(increase({sel}[$__range])) by (tipo_geracao)"
    for key, label in TIPO_GERACAO_LABELS.items():
        expr = f'label_replace({expr}, "tipo", "{_promql_escape(label)}", "tipo_geracao", "{key}")'
    return f'label_replace({expr}, "tipo", "$1", "tipo_geracao", "(.+)")'


def llm_invocations_by_tipo_geracao_period() -> str:
    """Chamadas LLM no período (fill_tr_slots, clausulas_llm, gerar_llm) por família."""
    expr = f"sum(increase({_LLM_INVOCATIONS_METRIC}[$__range])) by (tipo_geracao)"
    for key, label in TIPO_GERACAO_LABELS.items():
        expr = f'label_replace({expr}, "tipo", "{_promql_escape(label)}", "tipo_geracao", "{key}")'
    return f'label_replace({expr}, "tipo", "$1", "tipo_geracao", "(.+)")'


def total_tokens_by_tipo_geracao_period() -> str:
    """Soma entrada+saída no período por família (docmaster_llm_tokens_total)."""
    expr = f"sum(increase({_LLM_TOKENS_METRIC}[$__range])) by (tipo_geracao)"
    for key, label in TIPO_GERACAO_LABELS.items():
        expr = f'label_replace({expr}, "tipo", "{_promql_escape(label)}", "tipo_geracao", "{key}")'
    return f'label_replace({expr}, "tipo", "$1", "tipo_geracao", "(.+)")'


def operations_by_tipo_geracao_total(*, result: str = "success") -> str:
    sel = f'docmaster_document_operations_total{{result="{result}"}}'
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
    "clausulas_llm": "Cláusulas (formulário /api/llm)",
    "gerar_tr_e_dfd": "TR + DFD + Ofício",
    "gerar_llm": "Gerar documento (LLM)",
    "gerar_tr_modelo": "TR modelo",
    "unknown": "Outro fluxo",
}


def tokens_by_fluxo_period() -> str:
    expr = f"sum(increase({_LLM_TOKENS_METRIC}[$__range])) by (fluxo)"
    for key, label in FLUXO_LABELS.items():
        expr = f'label_replace({expr}, "fluxo_label", "{_promql_escape(label)}", "fluxo", "{key}")'
    return f'label_replace({expr}, "fluxo_label", "$1", "fluxo", "(.+)")'

DESC_STAT_TOTAL = (
    "Consulta instantânea: total atual do contador (independente do intervalo do Grafana)."
)
DESC_STAT_PERIODO = "Soma no intervalo selecionado no Grafana."


def _thresholds(mode: str):
    """Evita «alerta» vermelho quando 0 é o valor bom (erros) ou quando sem dados."""
    if mode == "good_low":
        return {
            "mode": "absolute",
            "steps": [
                {"color": "green", "value": None},
                {"color": "yellow", "value": 1},
                {"color": "red", "value": 10},
            ],
        }
    if mode == "good_high":
        return {
            "mode": "absolute",
            "steps": [
                {"color": "red", "value": None},
                {"color": "yellow", "value": 1},
                {"color": "green", "value": 1},
            ],
        }
    return None


def stat(
    id_,
    title,
    y,
    x,
    w,
    expr,
    desc="",
    *,
    period=False,
    unit="none",
    decimals=0,
    thresholds=None,
    color_mode="value",
    no_value="0",
):
    defaults = {"decimals": decimals, "noValue": no_value, "unit": unit}
    if thresholds:
        defaults["thresholds"] = _thresholds(thresholds)
    return {
        "datasource": DS,
        "description": desc or (DESC_STAT_PERIODO if period else DESC_STAT_TOTAL),
        "fieldConfig": {"defaults": defaults, "overrides": []},
        "gridPos": {"h": 4, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {
            "colorMode": color_mode,
            "graphMode": "none",
            "justifyMode": "center",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": "auto",
        },
        "targets": [period_range(expr) if period else instant(expr)],
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
        "fieldConfig": {
            "defaults": {"decimals": 1, "noValue": "0", "unit": "percent", "min": 0, "max": 100},
            "overrides": [],
        },
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
                    "excludeByName": {
                        "Time": True,
                        "__name__": True,
                        "tipo_geracao": True,
                        "fluxo": True,
                        "fluxo_label": True,
                        "package": True,
                        "prefeitura": True,
                        "direction": True,
                        "operation": True,
                        "result": True,
                        "output": True,
                        "le": True,
                    },
                    "renameByName": {"tipo": "Tipo de geração", "fluxo_label": "Fluxo", "Value": value_col},
                },
            }
        ],
        "title": title,
        "type": "table",
    }


def prom_table_period(id_, title, y, x, w, h, expr, *, value_col="Valor", desc=""):
    """Tabela com increase no intervalo — instant no fim do range (não range+reduce)."""
    tbl = prom_table_generations(id_, title, y, x, w, h, expr, desc=desc, value_col=value_col)
    tbl["targets"] = [instant(expr)]
    return tbl


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


def bargauge_period_breakdown(id_, title, y, x, w, h, items, desc=""):
    """Barras horizontais no período — instant + increase (evita barchart com série temporal quebrada)."""
    return {
        "datasource": DS,
        "description": desc,
        "fieldConfig": {
            "defaults": {
                "decimals": 0,
                "min": 0,
                "unit": "none",
                "color": {"mode": "palette-classic"},
            },
            "overrides": [],
        },
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": id_,
        "options": {
            "displayMode": "gradient",
            "minVizHeight": 16,
            "namePlacement": "left",
            "orientation": "horizontal",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "showUnfilled": True,
            "valueMode": "color",
            "legend": {"displayMode": "hidden"},
        },
        "targets": [
            instant(period_delta(sel), chr(65 + i), leg) for i, (sel, leg) in enumerate(items)
        ],
        "title": title,
        "type": "bargauge",
    }


_NODE_JOB = 'job="node"'
_NODE_ROOT_FS = 'mountpoint="/",fstype!~"tmpfs|overlay|aufs|squashfs"'
_NODE_CPU_BUSY = (
    f'100 * (1 - avg(irate(node_cpu_seconds_total{{{_NODE_JOB},mode="idle"}}[5m])))'
)
_NODE_RAM_PCT = (
    f"100 * (1 - (node_memory_MemAvailable_bytes{{{_NODE_JOB}}} "
    f"/ node_memory_MemTotal_bytes{{{_NODE_JOB}}}))"
)
_NODE_DISK_FREE_PCT = (
    f"100 * (node_filesystem_avail_bytes{{{_NODE_JOB},{_NODE_ROOT_FS}}} "
    f"/ node_filesystem_size_bytes{{{_NODE_JOB},{_NODE_ROOT_FS}}})"
)
_NODE_RAM_USED = "node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes"

panels = []
y = 0
panels.append(
    text_panel(
        299,
        y,
        "**API** (`/metrics` remoto) = DocMaster (ZIP, logins, LLM). "
        "**Tokens IA** = `docmaster_llm_tokens_total` + `docmaster_llm_invocations_total` (média = tokens ÷ chamadas). "
        "**Host** = node_exporter :9100. Grafana lê o Prometheus, não a API no browser.",
    )
)
y += 3

panels.append(row(200, "Host (node_exporter)", y))
y += 1
panels += [
    stat(
        2001,
        "Node scrape",
        y,
        0,
        4,
        'max(up{job="node"})',
        thresholds="good_high",
        no_value="DOWN",
        desc="0 ou vazio = Prometheus não alcança node_exporter:9100.",
    ),
    stat(
        201,
        "CPU em uso",
        y,
        4,
        5,
        _NODE_CPU_BUSY,
        unit="percent",
        decimals=1,
        color_mode="none",
        no_value="—",
        period=True,
        desc="Query em range (instant+irate ficava vazio no Grafana).",
    ),
    stat(
        202,
        "RAM em uso",
        y,
        9,
        5,
        _NODE_RAM_PCT,
        unit="percent",
        decimals=1,
        color_mode="none",
        no_value="—",
        period=True,
    ),
    stat(
        203,
        "Disco livre (/)",
        y,
        14,
        5,
        _NODE_DISK_FREE_PCT,
        unit="percent",
        decimals=1,
        color_mode="none",
        no_value="—",
        period=True,
    ),
    stat(
        204,
        "Load 1m",
        y,
        19,
        5,
        f"node_load1{{{_NODE_JOB}}}",
        unit="none",
        decimals=2,
        color_mode="none",
        no_value="—",
        period=True,
    ),
]
y += 4
panels.append(
    ts_counts(
        205,
        "CPU e RAM no tempo",
        y,
        0,
        24,
        8,
        [
            (_NODE_CPU_BUSY, "CPU %"),
            (_NODE_RAM_PCT, "RAM %"),
        ],
        desc="Requer scrape do job node ativo.",
    )
)
y += 8

panels.append(row(280, "API DocMaster — período", y))
y += 1
panels += [
    stat(
        281,
        "Erros geração",
        y,
        0,
        6,
        period_delta('docmaster_document_operations_total{result="error"}'),
        period=True,
        thresholds="good_low",
    ),
    stat(
        282,
        "ZIP TR+DFD OK",
        y,
        6,
        6,
        period_delta(
            'docmaster_document_operations_total{operation="gerar_tr_e_dfd",result="success"}'
        ),
        period=True,
        color_mode="none",
        desc="Dispensa normal/rápida/inexig. — 1 por geração de documento (ZIP).",
    ),
    stat(
        283,
        "Fill-tr-slots OK",
        y,
        12,
        6,
        period_delta(
            'docmaster_document_operations_total{operation="fill_tr_slots",result="success"}'
        ),
        period=True,
        color_mode="none",
        desc="Só dispensa (normal/rápida) — botão Gerar cláusulas via fill-tr-slots.",
    ),
    stat(
        284,
        "Logins OK",
        y,
        18,
        6,
        period_delta('docmaster_auth_login_total{result="success"}'),
        period=True,
        color_mode="none",
    ),
]
y += 4

panels.append(row(265, "Tokens IA (período)", y))
y += 1
panels.append(
    text_panel(
        266,
        y,
        "**Média** = (entrada + saída) ÷ chamadas LLM (`docmaster_llm_invocations_total`). "
        "Dispensa: `fill_tr_slots`. Inexigibilidade: `clausulas_llm`. ETP: `gerar_llm`. "
        "0 = nenhuma chamada desse tipo no intervalo.",
    )
)
y += 3
panels += [
    stat(
        361,
        "Média — Dispensa normal",
        y,
        0,
        6,
        avg_tokens_for_tipo("dispensa_normal"),
        period=True,
        unit="short",
        decimals=0,
        color_mode="none",
        no_value="0",
        desc="docmaster_llm_tokens_total ÷ invocações (dispensa_normal).",
    ),
    stat(
        362,
        "Média — Dispensa rápida",
        y,
        6,
        6,
        avg_tokens_for_tipo("dispensa_rapida"),
        period=True,
        unit="short",
        decimals=0,
        color_mode="none",
        no_value="0",
    ),
    stat(
        363,
        "Média — Inexigibilidade",
        y,
        12,
        6,
        avg_tokens_for_tipo("inexigibilidade"),
        period=True,
        unit="short",
        decimals=0,
        color_mode="none",
        no_value="0",
        desc="Cláusulas via /api/llm (fluxo clausulas_llm).",
    ),
    stat(
        364,
        "Média — ETP",
        y,
        18,
        6,
        avg_tokens_for_tipo("etp"),
        period=True,
        unit="short",
        decimals=0,
        color_mode="none",
        no_value="0",
    ),
]
y += 4
panels.append(
    prom_table_generations(
        365,
        "Tokens totais por família",
        y,
        0,
        12,
        5,
        total_tokens_by_tipo_geracao_period(),
        value_col="Tokens",
        desc="Soma entrada+saída no período (docmaster_llm_tokens_total).",
    )
)
panels.append(
    bargauge_by_label(
        366,
        "Tokens por fluxo",
        y,
        12,
        12,
        5,
        tokens_by_fluxo_period(),
        "{{fluxo_label}}",
        desc="fill_tr_slots, clausulas_llm, gerar_llm, gerar_tr_e_dfd.",
    )
)
y += 5

panels.append(row(275, "Detalhe no período", y))
y += 1
panels.append(
    bargauge_by_label(
        3071,
        "Sucesso por operação API",
        y,
        0,
        12,
        5,
        operations_by_operation_period(result="success"),
        "{{op_label}}",
        desc="fill_tr_slots = cláusulas (dispensa). gerar_tr_e_dfd = ZIP. gerar_llm = ETP.",
    )
)
panels.append(
    prom_table_generations(
        274,
        "ZIP TR+DFD por família",
        y,
        12,
        6,
        5,
        operations_by_tipo_geracao_period(result="success", operation="gerar_tr_e_dfd"),
        value_col="ZIP",
        desc="Uma linha por modalidade — só geração de documento (gerar_tr_e_dfd), não fill-tr-slots.",
    )
)
panels.append(
    prom_table_generations(
        276,
        "Chamadas IA por família",
        y,
        18,
        6,
        5,
        llm_invocations_by_tipo_geracao_period(),
        value_col="IA",
        desc="fill_tr_slots (dispensa), clausulas_llm (inexig.), gerar_llm (ETP).",
    )
)
y += 5

panels.append(row(350, "Saúde", y))
y += 1
panels += [
    stat(
        351,
        "Node scrape",
        y,
        0,
        6,
        'max(up{job="node"})',
        thresholds="good_high",
        desc="1 = node_exporter alcançável.",
    ),
    stat(
        352,
        "API scrape",
        y,
        6,
        6,
        'max(up{job="backend"})',
        thresholds="good_high",
    ),
    stat(
        355,
        "Workers métricas",
        y,
        12,
        6,
        "max(docmaster_metrics_active)",
        thresholds="good_high",
    ),
    stat(
        353,
        "HTTP 5xx",
        y,
        18,
        6,
        period_delta('django_http_responses_total_by_status_total{status=~"5.."}'),
        period=True,
        thresholds="good_low",
    ),
]


dash = {
    "annotations": {"list": []},
    "editable": False,
    "description": "Métricas host (node) + API docmaster_* (ZIP/IA separados).",
    "fiscalYearStartMonth": 0,
    "graphTooltip": 1,
    "id": None,
    "links": [],
    "panels": panels,
    "refresh": "1m",
    "schemaVersion": 39,
    "tags": ["docmaster", "backend", "django", "layout-v41-host", "layout-v42-tokens"],
    "templating": {"list": []},
    "time": {"from": "now-24h", "to": "now"},
    "timezone": "browser",
    "title": "DocMaster — Backend Django",
    "uid": "docmaster-backend",
    "version": 42,
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(dash, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

panel_ids = [p.get("id") for p in panels if p.get("id") is not None]
dupes = sorted({i for i in panel_ids if panel_ids.count(i) > 1})
if dupes:
    print(f"AVISO: IDs de painel duplicados: {dupes}", file=sys.stderr)
    sys.exit(1)

print(f"Repo:  {ROOT}")
print(f"Wrote: {OUT} ({len(panels)} panels, layout-v42-tokens)")
