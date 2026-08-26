# Módulo — Cotação em lote paralela (índice)

**Status:** planejado (não implementado)  
**Data da discussão / documentação:** 2026-08-21 → 2026-08-25  
**Objetivo:** reduzir o tempo total de cotação com muitos itens (ex. 700), mantendo **100% da qualidade** da pesquisa atual, processando **vários itens ao mesmo tempo** (ondas), em vez de 1 serial.

---

## Documentos deste módulo

| Doc | Conteúdo |
|-----|----------|
| [01 — Visão, diagnóstico e produto](./MODULO-COTACAO-LOTE-PARALELA-01-VISAO-DIAGNOSTICO-E-PRODUTO.md) | Problema, o que foi discutido, verditos (Python vs Qwen vs Enrich), produto vendável, o que **não** entra |
| [02 — Desenho técnico](./MODULO-COTACAO-LOTE-PARALELA-02-DESENHO-TECNICO.md) | Fluxo atual, onde serializa, como fazer N paralelos, SQLite, Cloudflare, timeouts, flags, código-alvo |
| [03 — Roadmap, aceite e runbook](./MODULO-COTACAO-LOTE-PARALELA-03-ROADMAP-ACEITE-RUNBOOK.md) | Fases 0–7, critérios de “100% feito”, stress test do “talo”, rollback |

---

## Promessa em uma frase

> A pesquisa continua **item a item** com o **mesmo funil** (federado + Camada B). O lote deixa de ser **1 por vez** e passa a manter **N itens em voo** (ex. 10–50, teto medido no hardware). Tempo do lote ≈ ondas × parede da onda — não a soma dos 700.

---

## Relacionados (já existentes)

| Documento | Relação |
|-----------|---------|
| [PNCP-PARIDADE-LOTE-STATUS-IMPLEMENTADO.md](./PNCP-PARIDADE-LOTE-STATUS-IMPLEMENTADO.md) | Paridade de **qualidade** lote↔item (já feito) — este módulo é **paralelismo de agenda** |
| [PNCP-BUSCA-INTELIGENTE-QUALIDADE.md](./PNCP-BUSCA-INTELIGENTE-QUALIDADE.md) | Regras de qualidade que **não** devem mudar |
| [ARQUITETURA-FEEDS-INDEPENDENTES.md](./ARQUITETURA-FEEDS-INDEPENDENTES.md) | Multi-fonte (PNCP / TCE / Compras / Notas) |
| [deploy/ESTABILIDADE-E-CLOUDFLARE.md](../deploy/ESTABILIDADE-E-CLOUDFLARE.md) | Tunnel, 502, timeouts CF |
| [PESQUISADOR_PNCP_FUNCIONAMENTO_ATUAL.md](./PESQUISADOR_PNCP_FUNCIONAMENTO_ATUAL.md) | Funcionamento atual busca/cotação |

---

## Decisão explícita de produto

| Decisão | Valor |
|---------|--------|
| Modo “rápido” vs “qualidade” | **Não existe.** Um único padrão de qualidade. |
| Qwen como vilão do lote | **Não** (rerank bulk off por default) |
| Enrich HTTP PNCP como vilão principal (multi-fonte) | **Não** — maioria TCE/Compras/Notas |
| Kafka/NATS obrigatório no v1 | **Não** — fase opcional |
| Só mudar `BULK_CONCURRENCY` | **Insuficiente** para módulo vendável; precisa FE+BE+SQLite+timeouts+paridade+runbook |
