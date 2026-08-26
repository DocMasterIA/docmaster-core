# Módulo Cotação em lote paralela — 02 Desenho técnico

**Status:** planejado (não implementado)  
**Índice:** [00-INDICE](./MODULO-COTACAO-LOTE-PARALELA-00-INDICE.md)

Este documento descreve **como fazer** no código e na ops atuais, sem alterar a regra de qualidade da busca.

---

## 1. Fluxo atual (cadeia completa)

```
Planilha cotação (N itens)
  → CotacaoDetalhe / autostart
  → BuscaInteligenteCotacoes.runBulkItemSearches
       ├─ BULK_CONCURRENCY = 1          ← SERIALIZA O LOTE
       ├─ BULK_ITEM_DELAY_MS = 50
       └─ workers = min(CONCURRENCY, pendentes)
  → processOneBulkItem(ctx)
  → federatedMarketSearch(payload)     # frontend-vue/src/services/pncpResearch.js
       timeoutMs ~180–200s, retries
  → POST /api/pncp-research/market-search/federated
  → Django pncp_research_proxy          # backend/app/pncp_research_proxy.py
       timeout read até ~900s
  → pncp_researcher_service
       adapters/federated.py
         ├─ local_item_search (PNCP SQLite)      se "pncp" habilitado
         └─ platform_item_search (TCE/Compras/Notas)  FTS por fonte
       → merge / dedup / crosslink
       → orchestrate_merged_candidate_pool (Camada B)
  → top3 / itens → UI → gravação cotação
```

### Onde “obriga item por item”

- **Correto e necessário:** cada item da planilha tem `termo_busca` próprio → 1 pesquisa federada por item.
- **Serialização indesejada:** `BULK_CONCURRENCY = 1` faz com que só **um** `processOneBulkItem` rode por vez.

Trecho de referência (estado atual):

```javascript
// frontend-vue/src/views/BuscaInteligenteCotacoes.vue
const BULK_CONCURRENCY = 1;
const BULK_ITEM_DELAY_MS = 50;
// ...
const workers = Math.max(1, Math.min(BULK_CONCURRENCY, pendentes.length || 1));
await Promise.all(Array.from({ length: workers }, () => bulkWorker()));
```

O `bulkWorker` já é um pool com fila (`nextIdx`). Com concurrency 50, cinquenta workers puxam itens da fila em paralelo.

---

## 2. Alvo técnico (ondas)

### 2.1 Comportamento desejado

1. Fila de pendentes (como hoje).
2. Manter até **N** pesquisas federadas **em voo**.
3. Cada uma = **mesmo** payload/funil que a busca unitária (qualidade).
4. Ao terminar um, puxar o próximo até esgotar.
5. UI: `done / total / inFlight / ok / empty / fail / precos`.
6. Cancelar lote; retomar só falhos/pendentes.
7. Retry por item em erros transitórios.

### 2.2 Invariante de qualidade

```
resultado(item_i, N=k) ≡ resultado(item_i, N=1)
  para os mesmos filtros, fontes_habilitadas, faixa, etc.
  (exceto empates documentados / falha operacional)
```

**Proibido** neste módulo:

- Pular category/spec/faixa/homolog “porque é lote”
- Top‑K pré-pronto com regra diferente
- Desligar fontes para “acelerar”
- Trocar federado por atalho de uma base

---

## 3. Mudanças por camada

### 3.1 Frontend (`BuscaInteligenteCotacoes.vue` + serviço)

| Item | Detalhe |
|------|---------|
| Concurrency configurável | Ler de `import.meta.env.VITE_PNCP_BULK_CONCURRENCY` e/ou setting remoto; default `N_SAFE`; clamp `[1, N_MAX]` |
| Delay | `BULK_ITEM_DELAY_MS = 0` quando concurrency &gt; 1 (ou delay só no 1º de cada worker) |
| Progresso | Expor `inFlight` além de `done/total/ok/fail/empty/precos` |
| Cancelar | AbortController por item + flag `stopRequested` (já parcial) |
| Retomar | Reentrar `runBulkItemSearches` só com contextos sem preço / failed |
| Retry | Em `processOneBulkItem` ou no `federatedMarketSearch`: 429, 502, 524, network — 2–3 tentativas, backoff exponencial curto |
| Timeout por item | Ex.: 60–90 s (&lt; ~100 s CF Free); **não** usar um único timeout para o lote inteiro |
| Isolamento | `try/catch` por item já existe; garantir que `stop` só em cancelamento explícito, não em 1 falha |

**Payload por item (inalterado em espírito):**

- `busca_lote: true` (comportamento de lote no backend, se aplicável)
- `fontes_habilitadas` da UI
- termo / geo / faixa iguais ao fluxo atual

### 3.2 Proxy Django (`pncp_research_proxy.py`)

| Item | Detalhe |
|------|---------|
| Capacidade | Com N=50, o proxy precisa de workers/threads suficientes (Gunicorn/uvicorn atrás do tunnel). Se 1 worker sync, os “50” viram fila no Django. |
| Timeout | Manter read timeout folgado por request (já ~900s); o limite útil passa a ser o do **cliente** (60–90s) + CF (~100s) |
| Não agregar | v1 continua **1 POST federado por item** (simples, paridade fácil) |

### 3.3 `pncp_researcher_service` (obrigatório para “talo”)

| Item | Detalhe |
|------|---------|
| Semáforo global | `asyncio.Semaphore(N_MAX)` em torno de `federated_search` / market-search federated |
| Config | `PNCP_BULK_PARALLEL_MAX_INFLIGHT` (ex. 40) — **teto do servidor**, independente do frontend |
| 503 / Retry-After | Se semáforo saturado por muito tempo, responder de forma que o FE faça retry do **item** |
| Métricas | Contadores: `inflight`, `completed`, `errors`, histograms de duração; opcional campo em `stats` |
| SQLite | Já: WAL + `busy_timeout=30000` em `platform_index/connection.py` e local_index. Reforçar: retry em `OperationalError: database is locked` na search (1–3x) |
| Qualidade | **Zero** mudança em `orchestrate_merged_candidate_pool`, scoring, filtros de plataforma |

Pseudo-código do semáforo:

```python
# conceitual — não aplicar ainda
_FEDERATED_SEM = asyncio.Semaphore(int(os.getenv("PNCP_BULK_PARALLEL_MAX_INFLIGHT", "20")))

async def federated_search_guarded(query):
    async with _FEDERATED_SEM:
        return await federated_search(query)
```

### 3.4 SQLite / índices

Fontes sob carga paralela:

- `pncp_researcher_local.db` (~4 GB ordem)
- DBs de plataforma (TCE / Compras / Notas) — volumes grandes

Regras:

1. Somente leitura na busca; evitar writers (feed) competindo no mesmo momento do stress de cotação, ou aceitar N menor.
2. WAL obrigatório (já no `platform_conn`).
3. Medir `database is locked` sob N=10/20/50.
4. Se lock storm: baixar `N_MAX`; só então considerar read replica / endpoint bulk interno (fase 7).

### 3.5 Cloudflare Tunnel

| Tema | Ação |
|------|------|
| Tipo de tunnel | Named tunnel (ok para multiplex) |
| Timeout Free ~100s | Timeout cliente &lt; 90s |
| Bot Fight / rate limit | Allowlist ou exceção para `POST /api/pncp-research/*` se 429 em burst |
| Testes | Sempre pelo hostname público `https://api.docmasteria.com.br` (mesmo path do cliente) |

---

## 4. Flags / configuração propostas

| Flag / env | Onde | Default sugerido | Papel |
|------------|------|------------------|-------|
| `VITE_PNCP_BULK_CONCURRENCY` | Frontend build | `N_SAFE` (ex. 10–20) | Itens em voo no browser |
| `VITE_PNCP_BULK_ITEM_TIMEOUT_MS` | Frontend | `90000` | Timeout por item |
| `VITE_PNCP_BULK_ITEM_DELAY_MS` | Frontend | `0` se N&gt;1 | Delay entre picks |
| `PNCP_BULK_PARALLEL_ENABLED` | Researcher (+ opcional FE) | `true` após ship | Kill switch |
| `PNCP_BULK_PARALLEL_MAX_INFLIGHT` | Researcher | `N_MAX` (ex. 40) | Semáforo global |
| `PNCP_BULK_PARALLEL_LOCKED_RETRIES` | Researcher | `3` | Retry SQLite locked |

**Regra:** `min(frontend_concurrency, server_max_inflight)` define o talo real. Frontend nunca deve exceder o semáforo de forma útil (senão só enfileira).

---

## 5. Fase opcional — endpoint bulk nativo

Se HTTP×50 saturar proxy ou overhead:

```
POST /api/pncp-research/market-search/federated/bulk
Body: { items: [ { id, termo_busca, ...filtros }, ... ], max_inflight: 50 }
→ 202 + job_id
GET  /.../bulk/{job_id}  (progresso)
```

Internamente: mesmo `federated_search` por item + semáforo.  
**Paridade:** cada item idêntico ao POST unitário.  
**Não** é obrigatório para o v1 se o path atual aguentar N medido.

---

## 6. Fase opcional — fila (NATS JetStream / Kafka)

Usar **só se**:

- Precisarem fechar o browser e o lote continuar;
- Ou vários workers em hosts distintos.

Caso contrário, a fila em memória do `bulkWorker` + semáforo no researcher cobre o caso DocMaster single-host.

---

## 7. Teste de paridade (obrigatório)

### Harness

1. Fixar seed de 30–50 itens reais (descrições + filtros + `fontes_habilitadas`).
2. Rodar com `CONCURRENCY=1`; gravar top‑3 (preço, fonte, chave processo/pncp).
3. Rodar com `CONCURRENCY=N_MAX`; gravar de novo.
4. Diff: igualdade de conjunto de preços/fontes por item.

### Aceite

- Match ≥ 95% bit-a-bit nos itens **completed OK**.
- Divergências só por: empate de score, falha operacional, ou ordem irrelevante documentada.

### Casos especiais

- Multi-fonte (TCE+Compras+Notas+PNCP)
- Item sem preço
- Termo longo de edital
- Faixa direcional ativa

---

## 8. Stress test do “talo” (resumo técnico)

No **mesmo** ambiente de produção do cliente:

| Teste | Concurrency | Itens | Observar |
|-------|-------------|-------|----------|
| T1 | 5 | 100 | p95 item, locks, 5xx |
| T2 | 10 | 200 | idem |
| T3 | 20 | 300 | idem |
| T4 | 35 | 400 | idem |
| T5 | 50 | 500–700 | idem |
| T6 | 64+ | até romper | documentar ruptura |

Definir:

- `N_SAFE` = maior N com falha operacional &lt; 1–2% e p95 aceitável
- `N_MAX` = teto configurável com margem abaixo da ruptura

“No talo” = default em `N_SAFE` ou `N_MAX` com margem — **não** no ponto que quebra na demo.

---

## 9. Mapa de arquivos tocados (implementação futura)

| Área | Arquivos prováveis |
|------|-------------------|
| FE lote | `frontend-vue/src/views/BuscaInteligenteCotacoes.vue` |
| FE API | `frontend-vue/src/services/pncpResearch.js` |
| Proxy | `backend/app/pncp_research_proxy.py` (só se precisar headers/503) |
| Federado | `pncp_researcher_service/app/adapters/federated.py` |
| API | `pncp_researcher_service/app/api_researcher.py` |
| Config | `pncp_researcher_service/app/config.py` |
| SQLite | `pncp_researcher_service/app/platform_index/connection.py`, `local_index.py` |
| Testes | novos em `pncp_researcher_service/tests/` + e2e manual documentado |
| Compose/env | `.env.example`, override prod |

---

## 10. Sequência de implementação recomendada (técnica)

1. Instrumentar timers/contadores (sem mudar N).
2. Concurrency configurável + UI inFlight + delay 0 (começar N=8).
3. Semáforo researcher + retry locked.
4. Timeout/retry FE alinhados a CF.
5. Stress → gravar N_SAFE/N_MAX.
6. Paridade harness.
7. Flag prod + runbook.
8. (Opc) bulk endpoint / NATS.

Detalhamento de fases, aceite e runbook: [03](./MODULO-COTACAO-LOTE-PARALELA-03-ROADMAP-ACEITE-RUNBOOK.md).
