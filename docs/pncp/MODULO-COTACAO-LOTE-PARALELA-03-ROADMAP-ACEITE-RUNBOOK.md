# Módulo Cotação em lote paralela — 03 Roadmap, aceite e runbook

**Status:** planejado (não implementado)  
**Índice:** [00-INDICE](./MODULO-COTACAO-LOTE-PARALELA-00-INDICE.md)

---

## 0. Realismo do “100% sem falhas”

Rede + SQLite + 700 itens **não** garantem zero timeout eterno.  
**Definição operacional de pronto:**

- Máximo paralelismo **estável** (`N_SAFE` / `N_MAX` medidos).
- Falhas **isoladas** e **100% retentáveis** (não destroem o lote).
- Timeouts **por item**, tratados (retry / retomar).
- Qualidade **idêntica** à busca unitária (paridade).
- Kill switch + rollback em minutos.

---

## 1. Critérios de aceite (“100% feito”)

| ID | Critério | Como verificar |
|----|----------|----------------|
| A | Paridade N=1 vs N_max (≥30 itens) | Harness §7 do doc técnico |
| B | Lote 700 completa; UI não trava; cancelar/retomar | Teste manual + autostart |
| C | Falha operacional &lt; 2% no stress; falhos retentáveis | Contadores do lote |
| D | Sem 524/timeout CF por item sob N_max | Timeout item &lt; 90s; logs |
| E | Sem `database is locked` não tratado | Logs researcher; retry |
| F | Semáforo: 3 abas não fazem N×3 até matar host | Teste multi-aba |
| G | Flag + runbook + métricas p50/p95 | Docs + env prod |

---

## 2. Roadmap por fases

### Fase 0 — Instrumentação (1–2 dias)

**Objetivo:** baseline antes de paralelizar.

- [ ] Timers por item: proxy / federated_total / fts_por_fonte / funil / enrich (se houver)
- [ ] Contadores: `in_flight`, locks, timeouts, 4xx/5xx, vazios
- [ ] Log estruturado ou JSON ao fim do lote
- [ ] Baseline: 50 e 200 itens com `CONCURRENCY=1` (tempo total, p95)

**Exit:** números de baseline no ambiente do cliente.

---

### Fase 1 — Paralelismo no fluxo atual (2–4 dias)

**Objetivo:** primeiro salto real; ainda 1 HTTP por item.

- [ ] `BULK_CONCURRENCY` configurável (env/setting), default baixo (ex. 8), max alto (ex. 64)
- [ ] `BULK_ITEM_DELAY_MS = 0` (ou mínimo) quando N&gt;1
- [ ] UI: em voo / feitos / ok / vazios / falhas / preços
- [ ] Cancelar / pausar / retomar pendentes
- [ ] Isolamento: erro num item não para os workers
- [ ] Retry por item: 429, 502, 524, network (2–3×, backoff)
- [ ] Timeout **por item** 60–90 s

**Exit:** N=8 estável em 200 itens; paridade amostral ok.

---

### Fase 2 — Endurecer backend / origem (3–5 dias)

**Objetivo:** subir para 20–50 sem mentir.

- [ ] Semáforo `PNCP_BULK_PARALLEL_MAX_INFLIGHT` no researcher
- [ ] Django/proxy: workers suficientes para N simultâneos
- [ ] SQLite: confirmar WAL + busy_timeout; retry em locked na search
- [ ] 503 + Retry-After quando saturado (melhor que timeout opaco)
- [ ] `/ready` (DBs abrem + inflight &lt; teto) — opcional mas útil

**Exit:** stress 50 concurrent no hostname público sem cascata de 502.

---

### Fase 3 — Achar o “talo” (2–3 dias)

**Objetivo:** N máximo no hardware real (PC cliente + Docker + tunnel).

| Teste | N | Itens | Passa se |
|-------|---|-------|----------|
| T1 | 5 | 100 | falha &lt;1–2%, p95 ok |
| T2 | 10 | 200 | idem |
| T3 | 20 | 300 | idem + sem lock storm |
| T4 | 35 | 400 | idem |
| T5 | 50 | 500–700 | idem |
| T6 | 64+ | até quebrar | documentar ruptura |

- [ ] Gravar `N_SAFE_DEFAULT` e `N_MAX` no runbook
- [ ] Default de produção = `N_SAFE` (não o ponto de ruptura)

**Exit:** números escritos e usados nas flags.

---

### Fase 4 — Timeouts / Cloudflare / rede (1–2 dias)

- [ ] Path de teste = produção (`api.docmasteria.com.br`)
- [ ] Revisar Bot Fight / rate limit / WAF em POST research
- [ ] Timeout cliente &lt; 100 s; proxy alinhado
- [ ] UX: 524/429 → retry item, não “lote morto”
- [ ] 2 usuários no lote ao mesmo tempo (semáforo)

**Exit:** checklist CF verde.

---

### Fase 5 — Paridade de qualidade (1–2 dias)

- [ ] Harness N=1 vs N_max
- [ ] Casos: multi-fonte, sem preço, termo difícil, faixa
- [ ] Relatório de paridade anexado ao release
- [ ] Gate: sem paridade, não liga default alto em prod

**Exit:** relatório A aprovado.

---

### Fase 6 — Produção / venda (1–2 dias)

- [ ] `PNCP_BULK_PARALLEL_ENABLED` + concurrency FE/BE
- [ ] Default = `N_SAFE`; ops pode subir até `N_MAX`
- [ ] Runbook (secção 4 abaixo)
- [ ] Texto comercial alinhado ao N medido
- [ ] Monitoramento 1 semana pós-deploy (taxa falha, p95)

**Exit:** módulo on em prod; rollback = concurrency 1 ou flag off.

---

### Fase 7 — Opcional (só se Fase 3 saturar antes do desejado)

- [ ] `POST .../federated/bulk` (job + progresso)
- [ ] NATS/Kafka se lote durable fora do browser
- [ ] Pré-cálculo na ingestão (**outro módulo**) se quiserem ainda menos tempo com N já no teto de hardware

**Não bloqueia** o “feito” do paralelismo.

---

## 3. Ordem visual

```
0 Instrumentar
→ 1 Paralelo FE (N=8) + UI + retry
→ 2 Semáforo + SQLite + proxy
→ 3 Stress → N_SAFE / N_MAX
→ 4 Cloudflare / timeouts
→ 5 Paridade
→ 6 Flag + runbook + prod
→ 7 (opc) bulk nativo / fila / pré-processamento
```

Estimativa bruta ponta a ponta (sem Fase 7): **~10–18 dias úteis**, dependendo de acesso ao host do cliente para stress.

---

## 4. Runbook operacional (rascunho para o ship)

### 4.1 Ligar / desligar

```bash
# Conceitual — valores finais após Fase 3
# Researcher
PNCP_BULK_PARALLEL_ENABLED=1
PNCP_BULK_PARALLEL_MAX_INFLIGHT=40   # N_MAX exemplo

# Frontend (build) / runtime se houver
VITE_PNCP_BULK_CONCURRENCY=20        # N_SAFE exemplo
VITE_PNCP_BULK_ITEM_TIMEOUT_MS=90000
```

**Rollback imediato:**

```bash
VITE_PNCP_BULK_CONCURRENCY=1
# ou
PNCP_BULK_PARALLEL_ENABLED=0
```

Rebuild/redeploy FE se a concurrency for bake-time; preferir setting runtime se possível.

### 4.2 Sintomas → ação

| Sintoma | Ação |
|---------|------|
| Muitos `database is locked` | Baixar concurrency (FE e/ou MAX_INFLIGHT); pausar feeds writers se possível |
| 502/524 em massa | Baixar N; checar Docker CPU/RAM; timeout item; CF |
| 429 Cloudflare | Revisar Bot Fight/rate limit; backoff no FE |
| UI “50 em voo” mas lento como serial | Proxy/researcher com poucos workers — subir workers ou reduzir N mentiroso |
| Lote parou no meio | Retomar pendentes; não apagar preços já salvos |
| Paridade falhou em release | Não subir N_SAFE; investigar regressão no funil (não na agenda) |

### 4.3 Retomar lote

1. Abrir busca inteligente da cotação.
2. Disparar busca só nos itens sem preço / failed (fluxo a implementar na Fase 1).
3. Manter resultados já gravados.

### 4.4 Checklist pré-demo cliente

- [ ] N_SAFE conhecido e configurado
- [ ] Stress T2/T3 ok neste host
- [ ] Autostart 50–100 itens demo ok
- [ ] Cancelar/retomar ok
- [ ] Flag de rollback testada

---

## 5. Fora de escopo (não negociar neste módulo)

- Funil mais frouxo / modo rápido
- Kafka obrigatório no v1
- Prometer N=50 se o talo medido for 20
- “Zero timeout para sempre”
- Pré-materialização de preços (módulo seguinte)
- Alterar regras de qualidade da paridade lote↔item já entregue

---

## 6. Checklist de issues (para abrir no tracker)

1. `chore(pncp): métricas e timers busca lote` (Fase 0)  
2. `feat(fe): concurrency configurável + inFlight + delay` (Fase 1)  
3. `feat(fe): retry/timeout/cancel/retomar lote paralelo` (Fase 1)  
4. `feat(researcher): semáforo max inflight federated` (Fase 2)  
5. `fix(sqlite): retry locked na search platforms/pncp` (Fase 2)  
6. `test(ops): stress matrix N=5..64 no host prod` (Fase 3)  
7. `chore(cf): checklist timeout/WAF path research` (Fase 4)  
8. `test(pncp): harness paridade concurrency 1 vs N` (Fase 5)  
9. `docs+ops: flags, runbook, texto comercial N medido` (Fase 6)  
10. `(opc) feat: endpoint federated/bulk` (Fase 7)

---

## 7. Definição de pronto para o cliente (texto final)

> A cotação processa até **N** itens em paralelo (**N** calibrado neste servidor), com a **mesma qualidade** da busca atual; o tempo do lote cai na ordem de **N**; falhas pontuais **não** destroem o lote; é possível **cancelar e continuar**; medimos e podemos subir N até o teto seguro.

---

## 8. Histórico deste planejamento

| Data | Evento |
|------|--------|
| 2026-08 | Diagnóstico: demora lote; Python/funil vs Qwen; Enrich vs multi-fonte |
| 2026-08 | Confirmação: `BULK_CONCURRENCY = 1` serializa; pool já existe |
| 2026-08 | Requisito: sem modo rápido/qualidade — 100% qualidade + massa paralela |
| 2026-08 | Teoria das ondas (ex. 50 em voo, parede ~10 s) |
| 2026-08 | CF Free: não limita 1 request; cuidado 100s / WAF |
| 2026-08-25 | Documentação gravada nestes MDs |
