# PNCP — Planejamento e referência técnica

**Atualizado:** junho/2026  
**Propósito:** documentação fina para análise, evolução e operação do módulo PNCP no DocMaster. Complementa (não substitui) os guias de deploy em `docs/deploy/`.

---

## Como usar esta pasta

| Documento | Conteúdo |
|-----------|----------|
| [01-OBJETIVOS-E-ESCOPO.md](./01-OBJETIVOS-E-ESCOPO.md) | Metas de produto, o que é realista, o que **não** é prometido |
| [02-ARQUITETURA-GERAL.md](./02-ARQUITETURA-GERAL.md) | Serviços, rede Docker, fluxo Django ↔ researcher |
| [03-INGESTAO-24-7.md](./03-INGESTAO-24-7.md) | Fila, worker, planner, watermark, backpressure |
| [04-INDICE-LOCAL-SQLITE.md](./04-INDICE-LOCAL-SQLITE.md) | Tabelas, FTS5, gaps, métricas de cobertura |
| [05-API-PNCP-EXTERNA.md](./05-API-PNCP-EXTERNA.md) | Endpoints PNCP, limites 365d, modalidades, throttle |
| [06-BUSCA-E-FORNECEDOR.md](./06-BUSCA-E-FORNECEDOR.md) | Busca inteligente, híbrida, CNPJ/razão social |
| [07-CONFIGURACAO-DEPLOY-OPS.md](./07-CONFIGURACAO-DEPLOY-OPS.md) | Variáveis de ambiente, compose, scripts, diagnóstico |
| [08-CASOS-FALHA-AUTOCURA.md](./08-CASOS-FALHA-AUTOCURA.md) | Falhas conhecidas, autocura, incidentes reais |
| [09-GAPS-E-ROADMAP.md](./09-GAPS-E-ROADMAP.md) | Lacunas vs PNCP nacional, próximos passos |
| [10-SLA-ALIMENTACAO.md](./10-SLA-ALIMENTACAO.md) | **SLA anti-trava** — throughput mínimo, métricas, garantias |

---

## Documentos relacionados (fora desta pasta)

| Ficheiro | Uso |
|----------|-----|
| [../PNCP-DECLARATIVO.md](../PNCP-DECLARATIVO.md) | Estado declarativo do repositório |
| [../PNCP-CONTEXTO-IA.md](../PNCP-CONTEXTO-IA.md) | Contexto compacto para IA |
| [../../deploy/PNCP-INGESTAO-INDEX-24-7.md](../../deploy/PNCP-INGESTAO-INDEX-24-7.md) | Guia operacional DESKTOP |
| [../../deploy/PNCP-COMANDOS-OPERACAO.txt](../../deploy/PNCP-COMANDOS-OPERACAO.txt) | Comandos copy-paste |
| [../PLANO-MODULO-COBERTURA-FORNECEDOR-PNCP.md](../PLANO-MODULO-COBERTURA-FORNECEDOR-PNCP.md) | Plano fornecedor |
| [../PLANO-FONTES-PRECOS-MULTIPLAS-PLATAFORMAS.md](../PLANO-FONTES-PRECOS-MULTIPLAS-PLATAFORMAS.md) | TCE, BNC, BLL e outras fontes de preço |
| [../PNCP-IMPLEMENTACAO-PARIDADE-LOTE.md](../PNCP-IMPLEMENTACAO-PARIDADE-LOTE.md) | Runbook implementação + checkpoints |
| [../PNCP-PARIDADE-LOTE-STATUS-IMPLEMENTADO.md](../PNCP-PARIDADE-LOTE-STATUS-IMPLEMENTADO.md) | **Status:** o que foi codado (ondas 1–2) vs notas/análise |
| [../PNCP-NOTAS-PENDENCIAS.md](../PNCP-NOTAS-PENDENCIAS.md) | Bugs/observações de campo |
| [../PNCP-ANALISE-CODIGO-IA-ITEM-VS-LOTE.md](../PNCP-ANALISE-CODIGO-IA-ITEM-VS-LOTE.md) | Análise código: `?itemId=` vs `busca_lote` |
| [../PNCP-PLANO-PARIDADE-BUSCA.md](../PNCP-PLANO-PARIDADE-BUSCA.md) | Paridade busca lote vs individual |

---

## Código principal

```
pncp_researcher_service/app/
├── api.py              # Rotas FastAPI
├── service.py          # Busca ao vivo + inteligente
├── local_index.py      # SQLite, FTS, backfill
├── pncp_client.py      # HTTP PNCP + throttle
├── supplier_resolver.py
├── ingest_worker.py
├── ingest_planner.py
├── ingest_queue.py
├── ingest_maintenance.py
├── ingest_runtime.py
├── ingest_backpressure.py
├── ingest_coverage.py
├── ingest_dates.py
└── config.py

backend/app/
├── pncp_research_proxy.py
└── services/pncp_relatorio_itens.py   # PDF/relatório

frontend-vue/src/
├── services/pncpResearch.js
└── views/BuscaInteligenteCotacoes.vue
```
