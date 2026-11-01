# PNCP — índice da documentação

Documentação do módulo **Pesquisador PNCP** (`pncp_researcher_service`), ingestão 24/7, índice local SQLite e busca inteligente.

---

## Visão geral

| Documento | Conteúdo |
|-----------|----------|
| [PNCP-DECLARATIVO.md](./PNCP-DECLARATIVO.md) | Estado declarativo do sistema |
| [PNCP-CONTEXTO-IA.md](./PNCP-CONTEXTO-IA.md) | Contexto IA (ingest + fornecedor + ops) |
| [ANALISE-COBERTURA-TEMPORAL-INDICE-PNCP-SET2026.md](./ANALISE-COBERTURA-TEMPORAL-INDICE-PNCP-SET2026.md) | **Análise set/2026** — índice ~1,2M enviesado (pico abr–mai/2025); alimentação vs API vs UI |
| [PLANOS-TECNICOS-CONTRATOS-E-ITENS-SET2026.md](./PLANOS-TECNICOS-CONTRATOS-E-ITENS-SET2026.md) | **Planos técnicos** — (A) catálogo/justiça temporal; (B) paginação /itens (teto 10) |
| [PESQUISADOR_PNCP_FUNCIONAMENTO_ATUAL.md](./PESQUISADOR_PNCP_FUNCIONAMENTO_ATUAL.md) | Funcionamento atual da busca/cotação |
| [PNCP-NOTAS-PENDENCIAS.md](./PNCP-NOTAS-PENDENCIAS.md) | Pendências conhecidas |
| [PNCP-BUSCA-INTELIGENTE-REGRESSAO-UI-VS-BACKEND.md](./PNCP-BUSCA-INTELIGENTE-REGRESSAO-UI-VS-BACKEND.md) | Regressão UI vs backend (bisect jun/2026) |
| [PNCP-PERFIL-OPERACIONAL-JUL2026.md](./PNCP-PERFIL-OPERACIONAL-JUL2026.md) | **Handoff completo** — qualidade, lote, deploy VPS, flags |
| [PNCP-FAIXA-DIRECIONAL-JUL2026.md](./PNCP-FAIXA-DIRECIONAL-JUL2026.md) | **Faixa `cima`/`baixo`** — causa, fix, testes (validado jul/2026) |
| [ARQUITETURA-FEEDS-INDEPENDENTES.md](./ARQUITETURA-FEEDS-INDEPENDENTES.md) | Feeds PNCP + TCE-RS + Compras.gov independentes → researcher |
| [ANALISE-COLUNAS-PREMIUM.md](../pncp_researcher_service/data/tce_rs/ANALISE-COLUNAS-PREMIUM.md) | TCE-RS: scan CSV × item premium (sem API externa) |
| [MODULO-FONTES-PRECOS-04-COMPRAS-GOV.md](./MODULO-FONTES-PRECOS-04-COMPRAS-GOV.md) | **Compras.gov** — o que foi feito (scaffold + produto + testes); CSV pendente |
| [MODULO-FONTES-PRECOS-05-NOTAS-FISCAIS.md](./MODULO-FONTES-PRECOS-05-NOTAS-FISCAIS.md) | **Notas Fiscais** — scaffold Fase 1 (feed `:8017`; ingest 501) |
| [ESTUDO-NOTAS-FISCAIS-PORTAL-TRANSPARENCIA.md](./ESTUDO-NOTAS-FISCAIS-PORTAL-TRANSPARENCIA.md) | **Estudo** — NF-e Portal da Transparência → Inciso V |

---

## Planejamento

Pasta [planejamento/](./planejamento/) — documentos numerados `00` a `10`:

| Doc | Tema |
|-----|------|
| [00-INDICE.md](./planejamento/00-INDICE.md) | Índice do planejamento |
| [01-OBJETIVOS-E-ESCOPO.md](./planejamento/01-OBJETIVOS-E-ESCOPO.md) | Objetivos |
| [02-ARQUITETURA-GERAL.md](./planejamento/02-ARQUITETURA-GERAL.md) | Arquitetura |
| [03-INGESTAO-24-7.md](./planejamento/03-INGESTAO-24-7.md) | Ingestão contínua |
| … | Ver índice completo na pasta |

---

## Busca e fornecedor

| Documento | Conteúdo |
|-----------|----------|
| [PNCP-BUSCA-INTELIGENTE-QUALIDADE.md](./PNCP-BUSCA-INTELIGENTE-QUALIDADE.md) | Qualidade da busca + Qwen |
| [PNCP_BUSCA_INTELIGENTE_IA.md](./PNCP_BUSCA_INTELIGENTE_IA.md) | Busca inteligente IA |
| [PNCP-FORNECEDOR-RELATORIO-REGRAS.md](./PNCP-FORNECEDOR-RELATORIO-REGRAS.md) | Regras relatório fornecedor |
| [PNCP-TESTES-FORNECEDOR.md](./PNCP-TESTES-FORNECEDOR.md) | Testes fornecedor |
| [PLANO-MODULO-COBERTURA-FORNECEDOR-PNCP.md](./PLANO-MODULO-COBERTURA-FORNECEDOR-PNCP.md) | Cobertura fornecedor vencedor |

---

## Paridade lote / item

| Documento | Conteúdo |
|-----------|----------|
| [PNCP-ANALISE-CODIGO-IA-ITEM-VS-LOTE.md](./PNCP-ANALISE-CODIGO-IA-ITEM-VS-LOTE.md) | Análise item vs lote |
| [PNCP-PLANO-PARIDADE-BUSCA.md](./PNCP-PLANO-PARIDADE-BUSCA.md) | Plano paridade busca |
| [PNCP-IMPLEMENTACAO-PARIDADE-LOTE.md](./PNCP-IMPLEMENTACAO-PARIDADE-LOTE.md) | Implementação |
| [PNCP-PARIDADE-LOTE-STATUS-IMPLEMENTADO.md](./PNCP-PARIDADE-LOTE-STATUS-IMPLEMENTADO.md) | Status implementado |

---

## Cotação em lote paralela (agenda N itens em voo)

**Status: planejado (não implementado).** Paralelizar a fila do lote mantendo 100% da qualidade da busca atual.

| Documento | Conteúdo |
|-----------|----------|
| [MODULO-COTACAO-LOTE-PARALELA-00-INDICE.md](./MODULO-COTACAO-LOTE-PARALELA-00-INDICE.md) | Índice do módulo |
| [MODULO-COTACAO-LOTE-PARALELA-01-VISAO-DIAGNOSTICO-E-PRODUTO.md](./MODULO-COTACAO-LOTE-PARALELA-01-VISAO-DIAGNOSTICO-E-PRODUTO.md) | Visão, diagnóstico, produto, riscos |
| [MODULO-COTACAO-LOTE-PARALELA-02-DESENHO-TECNICO.md](./MODULO-COTACAO-LOTE-PARALELA-02-DESENHO-TECNICO.md) | Fluxo atual, ondas, FE/BE/SQLite/CF, flags |
| [MODULO-COTACAO-LOTE-PARALELA-03-ROADMAP-ACEITE-RUNBOOK.md](./MODULO-COTACAO-LOTE-PARALELA-03-ROADMAP-ACEITE-RUNBOOK.md) | Fases 0–7, aceite, runbook, issues |

---

## Outros planos

| Documento | Conteúdo |
|-----------|----------|
| [PLANO-FONTES-PRECOS-MULTIPLAS-PLATAFORMAS.md](./PLANO-FONTES-PRECOS-MULTIPLAS-PLATAFORMAS.md) | Plano original multi-plataforma (jun/2026) |
| [MODULO-FONTES-PRECOS-00-PREPARACAO.md](./MODULO-FONTES-PRECOS-00-PREPARACAO.md) | **Preparação** — síntese + decisões |
| [MODULO-FONTES-PRECOS-01-CATALOGO-COMERCIAL.md](./MODULO-FONTES-PRECOS-01-CATALOGO-COMERCIAL.md) | Catálogo comercial (complexidade + faixas — opcional) |
| [MODULO-FONTES-PRECOS-02-PARTICIONAMENTO.md](./MODULO-FONTES-PRECOS-02-PARTICIONAMENTO.md) | **Particionamento** — camadas, épicos, o que conectar |
| [MODULO-FONTES-PRECOS-03-PORTAL-COMPRAS-PUBLICAS.md](./MODULO-FONTES-PRECOS-03-PORTAL-COMPRAS-PUBLICAS.md) | **PCP (Ecustomize)** — API, fluxo, mapeamento, legal, dedup PNCP |
| [MODULO-FONTES-PRECOS-04-COMPRAS-GOV.md](./MODULO-FONTES-PRECOS-04-COMPRAS-GOV.md) | **Compras.gov (Dados Abertos / CSV)** — status implementação jul/2026 |

---

## Deploy e operação

Ver [deploy/README.md](../deploy/README.md) e subpasta `deploy/` (PNCP 24/7, ingestão, API índice local).

Comandos rápidos: [deploy/PNCP-COMANDOS-OPERACAO.txt](../deploy/PNCP-COMANDOS-OPERACAO.txt)
