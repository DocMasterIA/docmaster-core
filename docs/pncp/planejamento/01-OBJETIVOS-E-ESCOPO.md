# Objetivos e escopo realista

## 1. Objetivos do produto (DocMaster)

### Primários

1. **Pesquisa de preços para cotações** — usuário busca termo (ex.: "parafuso sextavado"), recebe até 3 itens homologados/adjudicados com preço, órgão, UF, fornecedor (CNPJ + razão social quando possível).
2. **Índice local profundo** — reduzir dependência de chamadas PNCP ao vivo; busca em SQLite com FTS5.
3. **Operação autônoma 24/7** — ingestão contínua no DESKTOP/servidor sem monitoramento manual constante.
4. **Relatório/PDF de cotação** — itens selecionados com fornecedor legível (sem placeholders `pncp_*`).

### Secundários

- Busca manual / stream ao vivo quando índice é raso (fallback híbrido).
- Sessões de cotação (Django ORM + frontend Vue).
- Diagnóstico de funil de busca (`/market-search/intelligent/diagnose`).

---

## 2. Objetivos explícitos do operador (sessão jun/2026)

| Objetivo | Status |
|----------|--------|
| Ingestão 24/7 sem intervenção manual | **Implementado** (worker + self-heal + stall recovery) |
| Não depender de olhar `pending` na fila | **Implementado** (heartbeat, autocura) |
| Recuperação após crash/restart | **Implementado** (supervisor, requeue, purge dead) |
| Crescimento contínuo do índice | **Parcial** — anti-trava jun/2026; ver [10-SLA-ALIMENTACAO.md](./10-SLA-ALIMENTACAO.md) |
| Espelhar **todo** o PNCP nacional (dezenas de milhões de itens) | **Fora do escopo atual** — ver [09-GAPS-E-ROADMAP.md](./09-GAPS-E-ROADMAP.md) |
| Zero paradas ever | **Impossível** — API externa, Docker, disco, 429 |

---

## 3. O que o sistema **é** hoje

Um **índice operacional** focado em:

- **Janela:** últimos **365 dias** (limite da API PNCP por request).
- **Geografia:** **27 UFs** brasileiras.
- **Modalidades default:** códigos **6, 7, 8, 9, 10** (pregão, dispensa, inexigibilidade, etc.).
- **Volume típico:** ~1,5M+ linhas em `pncp_itens` no DESKTOP (jun/2026), crescendo conforme fila processa.

Isso cobre bem **cotações recentes** em modalidades comuns. **Não** equivale ao universo completo do portal PNCP.

---

## 4. O que **não** prometer na entrega

| Expectativa incorreta | Realidade |
|---------------------|-----------|
| "Temos todos os itens do PNCP" | Só o que entrou na janela 365d × modalidades configuradas × contratos efetivamente buscados |
| "O índice sobe X mil itens/hora garantido" | Limitado por rate limit PNCP, tamanho da fila, mix catálogo/itens |
| "Nunca trava" | Pode ficar **lento** por PNCP — mas **não** aceitável `items_ok=0` por dias com gap no SQLite |
| "`pending` sempre desce" | Planner pode **aumentar** catálogo enquanto descobre páginas; normal oscilar |
| "Histórico > 1 ano automático" | Não implementado — contratos antigos nunca indexados não aparecem na busca atual |

---

## 5. Métricas de sucesso realistas

### Operacionais (24/7)

- Contentor `pncp_researcher_service` **healthy**
- Logs `ingest batch` ou `ingest heartbeat` a cada **≤20 min** (em condições normais)
- `dead` na fila **≈ 0**
- `items_ok_1h > 0` quando há contratos sem itens ou fila `contract_items` (ver [10-SLA-ALIMENTACAO.md](./10-SLA-ALIMENTACAO.md))
- `items_stalled=false` ou recovery `items_sem_progresso` em ≤ 15 min
- `stalled=false` na maioria do tempo, ou stall recovery dispara e destrava

### Produto (busca)

- Busca inteligente retorna 3 itens em termos comuns (parafuso, papel A4, etc.)
- Fornecedor com CNPJ válido **não** exibe `pncp_resultado_item_item`
- PDF/relatório com razão social ou "Não informado" — nunca string `pncp_*`

### Cobertura (índice)

- `total_itens` **sobe ao longo de dias/semanas** (não necessariamente a cada 15 min)
- `contratos_sem_itens` (coverage) **desce** enquanto fila de itens é alimentada
- `next_page` avança em `ingest-status` por UF/modalidade

---

## 6. Dois pipelines independentes (conceito-chave)

```
PIPELINE A — Ingestão 24/7
  Objetivo: encher pncp_contratos + pncp_itens
  Não traz fornecedor em massa no GET /itens

PIPELINE B — Enriquecimento on-demand
  Objetivo: CNPJ + razão social na busca/PDF
  Dispara na pesquisa (top N homologados) via /resultados + BrasilAPI
```

**Erro comum:** esperar que ingestão massiva já traga fornecedor perfeito. O GET `/itens` do PNCP traz descrição/preço; vencedor vem de `/resultados` (Pipeline B).

---

## 7. Prioridade de trabalho (ordem sugerida)

1. **Estabilidade da alimentação** — SLA anti-trava, backpressure, stall de itens *(jun/2026)*
2. **Throughput dentro da janela 365d** — tunar env, validar fila drena
3. **Fornecedor na cotação** — fixes deploy researcher + backend
4. **Cobertura histórica / modalidades extras** — roadmap fase 2
5. **Alertas automáticos** (Grafana/cron) — opcional pós-estabilização
