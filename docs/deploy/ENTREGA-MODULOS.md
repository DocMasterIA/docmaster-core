# Verificação de entrega — Módulos 1 e 2 (R$ 2.900 + persistência)

Documento para conferência do que está **implementado no repositório** versus o texto do escopo. Use como checklist de aceite e anexo técnico da entrega.

**Data de referência:** maio/2026 · repositório `docmaster-core`

**Próximo módulo (planejado):** [Cobertura de fornecedor PNCP](../PLANO-MODULO-COBERTURA-FORNECEDOR-PNCP.md) — persistir vencedor no índice SQLite; meta 70–90% nos itens elegíveis.

---

## Módulo 1 — Otimização de I.A. + Prometheus + Grafana (R$ 2.900)

| Promessa do escopo | Status | Evidência no projeto |
|--------------------|--------|----------------------|
| Otimização do pipeline de geração com I.A. | **Atendido** | Timeouts configuráveis Django→`rag_service` (`RAG_HTTP_TIMEOUT`, `RAG_HTTP_TIMEOUT_TR_DFD_MAX` em `docker-compose.yml` / `backend/app/api.py`). Remoção de retry duplicado em `_rag_post_json` (comentário explícito: evita dobrar tempo LLM/TR). |
| Desacoplamento de processos que degradam o fluxo principal | **Atendido (parcial)** | PNCP Researcher em compose **isolado** (`docker-compose.pncp.yml`) — backfill 24h não morre com `up -d` do backend. Frontend: remoção de header que quebrava CORS em `fill-tr-slots`. |
| Retry ineficiente corrigido | **Atendido** | `backend/app/api.py` — POST ao RAG sem retry em cascata; métricas LLM só após sucesso real (`_record_llm_usage_from_response`). |
| Timeouts mal gerenciados | **Atendido** | Histograma de duração até 1200s; timeouts por operação TR+DFD; exemplo nginx 900s em `deploy/nginx-gerar-tr-e-dfd-timeout.conf.example`. `GUNICORN_TIMEOUT` configurável. |
| Prometheus — coleta de métricas (app, containers, host) | **Atendido** | `config/prometheus.yml`: jobs `backend` (API remota), `node` (`node_exporter`), `prometheus`. `docker-compose.yml`: serviços `prometheus`, `node_exporter`. |
| Grafana — visualização para dev/admin | **Atendido** | Dashboard provisionado `DocMaster — Backend Django` (`scripts/build-grafana-dashboard.py` → `config/grafana/provisioning/.../docmaster-backend.json`). Acesso: `http://127.0.0.1:3000` (+ túnel SSH). Tag `layout-v42-tokens`. |
| Métricas de negócio Django + microsserviços | **Atendido** | `backend/app/metrics.py`: `docmaster_document_operations_total`, `docmaster_llm_tokens_total`, `docmaster_llm_invocations_total`, logins, duração, `docmaster_platform_events_total`. Export em `GET /metrics` (django-prometheus + multiproc Gunicorn). |
| Identificação proativa de gargalos | **Atendido (painéis)** | Host: CPU, RAM, disco, load (`node_*`). API: erros, ZIP, fill-tr-slots, tokens IA por família/fluxo, scrape health. **Alertas automáticos (e-mail)** não estão provisionados — recomendado como melhoria pós-entrega. |
| Escalabilidade sem falhas silenciosas | **Atendido (observabilidade)** | Falhas de geração contam em `result="error"`; scrape `up{job="backend"}` e `up{job="node"}` no dashboard. |

### Artefatos Módulo 1

- `config/prometheus.yml`, `config/grafana/provisioning/`
- `scripts/build-grafana-dashboard.py`, `scripts/grafana-reset-dashboard.sh`, `scripts/ensure-observability.sh`
- `scripts/validate-observability.py`, `scripts/validate-metrics-flows.py`
- `backend/app/metrics.py`, `backend/app/api.py`, `backend/app/metrics_export.py`
- `config/prometheus/README.md`, `docs/deploy/OBSERVABILIDADE-VPS.md`

### Ressalva de redação (contrato vs técnico)

- Microsserviços no projeto são em sua maioria **FastAPI** (`rag_service`, `llm_api`, `pncp_researcher_service`), não Flask — o escopo pode dizer “microsserviços Python” na entrega.
- Limite **~100s** do Cloudflare no plano gratuito continua existindo para requisições HTTP longas; timeouts internos podem ser 900s — documentado no exemplo nginx.

---

## Módulo 2 — Persistência do servidor (Cloudflare, Nginx, Docker YAML)

| Promessa do escopo | Status | Evidência no projeto |
|--------------------|--------|----------------------|
| Eliminação de quedas enquanto o servidor está ativo | **Atendido (com ressalvas)** | `restart: always` em `cloudflared-tunnel`, `prometheus`, `grafana`, `node_exporter`, PNCP. **WSL** pode “dormir” com PC ligado — mitigação: `vmIdleTimeout=-1` em `.wslconfig` (`docs/deploy/ESTABILIDADE-E-CLOUDFLARE.md`). |
| Erro 1033 Cloudflare — túnel íntegro | **Atendido (operacional)** | Causa documentada (túnel/origem/WSL). `cloudflared-tunnel` com `restart: always`. Token via `CLOUDFLARE_TUNNEL_TOKEN`. Runbook em `ESTABILIDADE-E-CLOUDFLARE.md`. **Não** exige nginx público para Grafana/API. |
| Reestruturação proxy (Nginx) e borda Cloudflare | **Parcial** | **Exemplos** prontos: `deploy/nginx-gerar-tr-e-dfd-timeout.conf.example`, `deploy/nginx-observability-api.conf.example` (opcional). Produção atual usa **Cloudflare Tunnel** → `backend` / `frontend-vue`, não nginx obrigatório no mesmo host. |
| Revisão YAML Docker | **Atendido** | `docker-compose.yml` (stack principal), `docker-compose.pncp.yml` (PNCP isolado), redes `docmaster_net`, portas em `127.0.0.1` para métricas. |
| Resiliência do túnel de saída | **Atendido** | Serviço `cloudflared-tunnel`, `depends_on` backend + frontend, `restart: always`. |
| Feeder PNCP contínuo sob demanda | **Atendido** | Compose dedicado `docmaster-pncp`; volume persistente (`pncp_researcher_data`); scripts `ensure-pncp-researcher.sh`, `find-pncp-db-volumes.sh`, `attach-pncp-volume.sh`; entrypoint corrige permissões SQLite; recuperação índice ~2,6 GB documentada. |

### Artefatos Módulo 2

- `docker-compose.yml`, `docker-compose.pncp.yml`
- `deploy/nginx-gerar-tr-e-dfd-timeout.conf.example`, `deploy/nginx-observability-api.conf.example`
- `deploy/docmaster-observability.service.example` (systemd Linux, opcional)
- `docs/deploy/ESTABILIDADE-E-CLOUDFLARE.md`, `docs/deploy/PNCP-RESEARCHER-24-7.md`
- `scripts/ensure-pncp-researcher.sh`, `scripts/ensure-observability.sh`

### Ressalvas honestas para o cliente

1. **“Eliminação total”** de interrupções: na prática é **alta resiliência** com Docker + runbooks; reboot do host ou `docker compose down` ainda exigem subida manual ou systemd.
2. **Nginx**: se o cliente espera nginx **já aplicado** no servidor de produção, confirme se os blocos dos ficheiros `.example` foram colados no `server` real — o repositório entrega o **modelo**, não altera o servidor remoto sozinho.
3. **1033**: resolvido no cenário WSL idle + tunnel parado; produção 24/7 ideal em **VPS Linux** sem WSL.

---

## Provas rápidas de aceite (5–10 min)

```bash
# API e métricas
curl -sI https://api.docmasteria.com.br/metrics | head -3

# Prometheus (no host do compose)
curl -s 'http://127.0.0.1:9090/api/v1/query' --data-urlencode 'query=up{job="backend"}'
curl -s 'http://127.0.0.1:9090/api/v1/query' --data-urlencode 'query=up{job="node"}'

# Grafana
curl -s http://127.0.0.1:3000/api/health

# PNCP (volume grande montado)
curl -s http://127.0.0.1:8012/api/pncp-research/local-index/stats

# Tunnel / stack
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'cloudflared|pncp|prometheus|grafana|backend'
```

---

## Conclusão para entrega

| Módulo | Veredito |
|--------|----------|
| **1 — Otimização I.A. + Prometheus/Grafana** | **Entregável** com evidência em código, dashboard e documentação. Complementar com 2–3 capturas de tela do Grafana (host + tokens + erros) e menção a alertas como evolução opcional. |
| **2 — Persistência servidor** | **Entregável** com ressalvas de linguagem: túnel + Docker YAML + PNCP 24h **sim**; nginx **como templates + aplicar no host se existir nginx**; 1033 **mitigado** (WSL + restart), não “impossível” se WSL dormir sem `vmIdleTimeout`. |

### Sugestão de texto para o termo de entrega (1 parágrafo)

*Implementados monitoramento Prometheus/Grafana com métricas de infraestrutura (CPU, RAM, disco) e de negócio (gerações, tokens LLM, erros e logins); otimização de timeouts e de retries no pipeline Django/RAG; isolamento do serviço PNCP Researcher em orquestração Docker dedicada com persistência de índice local; resiliência do Cloudflare Tunnel e documentação operacional para erro 1033 e recuperação pós-reboot. Fornecidos ficheiros de exemplo para Nginx (timeouts de geração longa) e runbooks de operação.*

---

## Melhorias opcionais (não exigidas pelo escopo, valorizam a entrega)

- Regras de alerta no Grafana (API down, disco baixo).
- `docs/ENTREGA.md` único com diagrama de arquitetura.
- Backup agendado do volume `docmaster_pncp_researcher_data`.
- Pin de versões de imagens Docker na release.
