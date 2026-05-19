# Prometheus — DocMaster

## Scrape

- **Produção:** `config/prometheus.yml` → job `backend` → `https://api.docmasteria.com.br/metrics` (30s).
- Não ative dois jobs `backend` ao mesmo tempo (métricas duplicadas).

## Métricas de negócio (`docmaster_*`)

| Métrica | Uso |
|---------|-----|
| `docmaster_auth_login_total` | Logins por `prefeitura` + `result` |
| `docmaster_document_operations_total` | Gerações por `operation`, `package`, `tipo_geracao`, `result` |
| `docmaster_document_operation_duration_seconds` | Histograma de duração (p95 no Grafana) |
| `docmaster_llm_tokens_total` | Tokens por `tipo_geracao`, `fluxo`, `direction` |
| `docmaster_metrics_active` | Workers Gunicorn com métricas ativas (~2) |

Labels `tipo_geracao`: `dispensa_normal`, `dispensa_rapida`, `inexigibilidade`, `etp`, `other`.

## Grafana

```bash
cd ~/docmaster-core
python3 scripts/build-grafana-dashboard.py
DOCMASTER_ROOT=~/docmaster-core ./scripts/grafana-reset-dashboard.sh
```

Dashboard: `DocMaster — Backend Django` (uid `docmaster-backend`, tag `layout-v24`).

## Explore (sanidade)

```promql
docmaster_metrics_active
sum by (tipo_geracao) (docmaster_document_operations_total)
sum by (tipo_geracao) (increase(docmaster_llm_tokens_total[1h]))
up{job="backend"}
```
