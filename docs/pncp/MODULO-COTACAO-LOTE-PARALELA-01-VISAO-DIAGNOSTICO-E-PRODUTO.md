# Módulo Cotação em lote paralela — 01 Visão, diagnóstico e produto

**Status:** planejado (não implementado)  
**Índice:** [00-INDICE](./MODULO-COTACAO-LOTE-PARALELA-00-INDICE.md)

---

## 1. Problema reportado

Ferramentas de mercado devolvem muitos preços por item em cotações grandes (ex. 700 linhas) em segundos. No DocMaster:

- Por item: tipicamente **~1–5 s** (às vezes até ~10 s em casos pesados).
- Em cotação inteira (autostart / busca em lote): o tempo **soma** porque a agenda processa **1 item por vez**.
- Exemplo: 700 × 2 s ≈ **~23 min**; 700 × 5 s ≈ **~58 min**.

O cliente não pede “item unitário mais rápido a qualquer custo de qualidade”. Pede **rapidez de lote** — quase “o lote inteiro de uma vez” no sentido de **quantidade / parede do relógio**, mantendo a **mesma** qualidade de pesquisa.

---

## 2. O que foi discutido (síntese da análise)

### 2.1 Hipóteses e verditos

| Hipótese | Verdito | Notas |
|----------|---------|--------|
| Qwen (LLM) é o gargalo do lote | **Fraca** | `PNCP_IA_RERANK_BULK_ENABLED` default **false**; resumo de item não roda em `busca_lote` |
| Algoritmo Python / funil na consulta | **Forte (custo por item)** | Scoring, categoria, spec, faixa, merge multi-fonte — **por item** |
| Enrich HTTP PNCP é o principal | **Fraca no multi-fonte atual** | Maioria dos preços vem de **TCE-RS / Compras.gov / Notas** via `platform_item_search` (FTS local), sem enrich PNCP típico |
| Enrich / hybrid HTTP | **Cauda / pior caso** | Ainda pode doer em hits PNCP “buracos” ou híbrido ao vivo; não explica a demora média multi-fonte |
| DB “solto” sem pré-classificação | **Certo como arquitetura de longo prazo** | Pré-processar na ingestão reduz Big O **depois**; não é o primeiro ship deste módulo |
| Agenda serial (1 item por vez) | **Gargalo imediato do tempo de lote** | Confirmado no frontend: `BULK_CONCURRENCY = 1` |

### 2.2 Separação importante

| Conceito | Significado |
|----------|-------------|
| **Qualidade da pesquisa** | *O quê* entra, *como* pontua, *o que* vira top‑3 (fontes, filtros, Camada B) |
| **Agenda do lote** | *Quando* / *quantos* itens rodam juntos |

O módulo ataca a **agenda**. A qualidade permanece a da busca unitária / federada atual.

### 2.3 Requisito de produto (corrigido)

**Errado (descartado):** dois modos — “rápido” (frouxo) vs “qualidade”.

**Certo (obrigatório):**

- 100% da qualidade atual.
- Processamento **item a item** (cada linha tem seu termo e seu funil).
- **Vários** itens nessa situação **ao mesmo tempo** (ex. 10, 20, 50 — teto medido).
- Reduzir cotação que podia ser ~1 h para **bem menos** (minutos / dezenas de segundos na ordem de grandeza).

### 2.4 Modelo mental: ondas

```
Hoje (N=1):   [A....][B....][C....]...[item700]     → tempo ≈ SOMA
Alvo (N=50):  [A B C ... 50 em voo ≈ parede 5–10s]
              [próxima onda ...]
              → tempo ≈ (700/N) × parede_da_onda
```

Exemplo aspiracional: 700 ÷ 50 ≈ 14 ondas × ~10 s ≈ **~2–3 min** (depende do host e do p95 sob carga).

---

## 3. Por que “só mudar a variável” não é o módulo

Já existe pool de workers no frontend; o teto está em **1**:

```text
frontend-vue/src/views/BuscaInteligenteCotacoes.vue
  BULK_CONCURRENCY = 1
  BULK_ITEM_DELAY_MS = 50
```

Subir para 10 ou 50 **é o núcleo**, mas um módulo vendável / entregável “100% no talo” exige também:

- UI de progresso / cancelar / retomar
- Retry isolado por item
- Timeout por item alinhado ao Cloudflare
- Semáforo no backend (evitar 3 abas × 50)
- SQLite WAL / busy / comportamento sob N leitores
- Stress test → `N_SAFE` / `N_MAX` no hardware do cliente
- Teste de **paridade** N=1 vs N_max
- Flag + runbook + rollback

---

## 4. Empacotamento comercial (como vender)

**Nome:** Módulo de paralelização da pesquisa de preços em lote  

**Problema:** o lote pesquisa item a item **em série** → 700 × (1–5 s) ≈ dezenas de minutos a ~1 h.  

**Solução:** processar até **N** itens em paralelo (N calibrado no servidor), com limites no researcher, timeouts corretos, UI de progresso e garantia de paridade com a busca unitária.  

**Resultado esperado:** tempo total do lote na ordem de **÷ N**, **mesma qualidade**.  

**Escopo técnico:** frontend + backend/researcher + SQLite/timeouts + testes de paridade + runbook — **não** “uma linha de config”.

**Texto honesto para o cliente:**

> A cotação processa até N itens ao mesmo tempo (N calibrado no servidor), com a mesma qualidade da busca atual; o tempo do lote cai na ordem de N; falhas pontuais não destroem o lote; dá para cancelar e continuar.

Não prometer “sempre 50” antes do stress test. Prometer **paralelismo com teto configurável** e **N medido**.

---

## 5. Medos e riscos (discutidos)

Ordenados por relevância no stack atual (Docker no PC do cliente + Cloudflare Tunnel + SQLite multi-fonte):

| # | Medo | Mitigação no módulo |
|---|------|---------------------|
| 1 | SQLite `database is locked` / p95 sobe com N alto | WAL + busy_timeout (já parcialmente), retry, achar `N_MAX` por stress |
| 2 | Timeout / proxy (CF Free ~100 s/request) | Timeout **por item** &lt; ~90 s; retry 524; não um timeout do lote inteiro como 1 request |
| 3 | Falha parcial (mais timeouts com N=50) | Isolamento + retry + retomar só pendentes |
| 4 | “Mentira de velocidade” (UI diz 50, backend fila em 2 workers) | Semáforo + workers proxy/uvicorn adequados |
| 5 | Qualidade aparente cai porque item falhou vazio | Não é mudança de algoritmo; métrica de falha operacional separada da paridade |

### Cloudflare Free

- Tunnel **nomeado** (não Quick Tunnel): **não** há limite “1 processo por vez”; requests são multiplexadas.
- Limite de **200 in-flight** é de Quick Tunnels (`trycloudflare`), não do `api.docmasteria.com.br`.
- Riscos reais no Free: timeout de proxy ~100 s em item **muito** lento; WAF/Bot Fight/rate limit em burst de POSTs.
- Conclusão: CF Free **não** é o vilão principal de N=50; pode **somar** dor se mal configurado.

### Kafka / NATS JetStream

| Ajuda | Não resolve |
|-------|-------------|
| Job durable, retry, UI desacoplada, multi-worker depois | Custo FTS+Python por item |
| Orquestrar ondas no servidor | SQLite aguentar 50 FTS no mesmo disco |

**v1:** pool + semáforo basta. **Fase opcional:** NATS/Kafka se precisarem fechar o browser e continuar, ou vários workers.

---

## 6. O que **não** entra neste módulo (próximos)

Estes reduzem o **trabalho por item** (Big O estrutural), mas são módulos separados:

1. Pré-processamento na ingestão: categoria, núcleo, chave de produto (mesmas funções do funil).
2. Tabela `precos_por_produto` / pools pré-ranqueados **com paridade bit-a-bit** do scoring atual.
3. Migrar SQLite → Postgres só por velocidade.
4. Ligar Qwen no lote (não é alavanca; pode piorar tempo).
5. “Modo rápido” com match mais frouxo.

Ordem estratégica alinhada à discussão:

```
Paralelismo de agenda (ESTE MÓDULO)
  → medir
  → se ainda pesado no talo de hardware: materializar features/pools com paridade
```

---

## 7. Relação com paridade lote já implementada

Já existe trabalho de **paridade de qualidade** lote ↔ item isolado (pipeline inteligente no lote, caps, etc.). Ver:

- `PNCP-PARIDADE-LOTE-STATUS-IMPLEMENTADO.md`
- `PNCP-IMPLEMENTACAO-PARIDADE-LOTE.md`

Este módulo **não** reabre essas regras. Ele assume o funil atual (incluindo multi-fonte federado) e muda **só a concorrência da fila de itens da planilha**.

---

## 8. Números de referência (ordem de grandeza)

| Cenário | Ordem de tempo (700 itens, ~2 s/item médio) |
|---------|-----------------------------------------------|
| N=1 (hoje) | ~23 min |
| N=10 | ~2–3 min |
| N=20 | ~1–1,5 min |
| N=50 | ~30–60 s (se host aguentar parede ~5–10 s) |

Sob contenção SQLite, a “parede” da onda sobe (ex. 15–25 s) — ainda assim muito abaixo do serial.

---

## 9. Glossário rápido

| Termo | Significado |
|-------|-------------|
| **Inflight / em voo** | Quantos itens estão sendo pesquisados agora |
| **Onda** | Conjunto de até N itens cuja parede ≈ max(latências) |
| **N_SAFE** | Default de produção após stress |
| **N_MAX** | Teto configurável abaixo do ponto de ruptura |
| **Paridade** | Resultado do item com N&gt;1 ≡ resultado com N=1 (mesmos filtros) |
| **Camada B** | `orchestrate_merged_candidate_pool` — faixa, score, top3 |
| **Federado** | `market-search/federated` — PNCP + plataformas |
