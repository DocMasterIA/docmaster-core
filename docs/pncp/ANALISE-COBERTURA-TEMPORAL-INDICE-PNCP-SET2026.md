# Análise — cobertura temporal do índice PNCP (set/2026)

**Status:** diagnóstico estrutural (análise; sem plano de código neste ficheiro)  
**Ambiente medido:** produção WSL (`docmaster@DESKTOP-2M57RHE`)  
**Base de dados:** `/data/pncp/pncp_researcher_local.db` (volume Docker do `pncp_researcher_service`)  
**Data do dump de datas:** ~set/2026 (conversa de diagnóstico)

---

## 1. Veredicto em uma frase

O índice local **não representa o PNCP nacional histórico**. Representa um **bloco denso de publicações concentrado nos primeiros 3–5 meses da janela** (sobretudo **abr–mai/2025**), seguido de **alimentação fraca / quase parada** no resto — **problema de ingestão dentro do próprio ano**, não de FTS nem de “filtro UI” como causa raiz do volume.

---

## 2. Sintoma que motivou o estudo

| O que o utilizador via | Interpretação errada (rejeitada) | Interpretação correta |
|------------------------|----------------------------------|------------------------|
| Busca manual PNCP com “poucos” itens vs expectativa do portal | “API/FTS quebrados” ou “só o filtro Período” | Índice **temporalmente torto**; filtro amplifica |
| ~1,2M itens no DB → sensação de “pouco” face ao PNCP | Volume absoluto insuficiente | Volume alto **dentro de janela estreita**; cobertura temporal pobre |
| Outras fontes (TCE, Compras, Notas) “melhores” em recall | PNCP search bug | Pipelines/volumes diferentes; PNCP legado = faixa + homolog + data |

Exemplo clássico (busca `pneu`, homologados):

| Camada | Contagem (ordem de grandeza) |
|--------|------------------------------|
| Hits na API federada | ~619–632 |
| Com data em **2025-04** | ~612 (fora de “Último Ano” em set/2026) |
| Dentro de 365 dias (filtro default UI) | ~18 |
| UI com «Último Ano» | ~18 |

**Conclusão parcial:** o filtro «Período = Último Ano» explica **632 → 18** na UI. **Não** explica **36% do índice num único mês** nem a cauda morta em 2026.

---

## 3. Evidência: distribuição de `data_publicacao` no índice

### 3.1 Totais

| Métrica | Valor |
|---------|------:|
| `total_itens` | **1.198.808** |
| Com `data_publicacao` | **1.198.808** (100%) |
| Sem `data_publicacao` | **0** |
| Faixa (10 chars) | **2025-04-13 … 2026-06-03** |
| Meses distintos | **15** |
| Ano 2025 | **1.165.107** (~97%) |
| Ano 2026 | **33.701** (~3%) |

### 3.2 Por mês (dump completo)

```
2025-04   227.599  ###############################
2025-05   430.749  ############################################################
2025-06   249.944  ##################################
2025-07   127.146  #################
2025-08    70.158  #########
2025-09    32.841  ####
2025-10    10.644  #
2025-11     8.802  #
2025-12     7.224  #
2026-01     8.507  #
2026-02     6.392  #
2026-03     7.666  #
2026-04     6.527  #
2026-05     4.582  #
2026-06        27  #
```

### 3.3 Concentração

| Agregado | Itens | % do total (~1,20M) |
|----------|------:|--------------------:|
| **Abr–Ago/2025** | **~1.105.596** | **~92%** |
| Só **abr–mai/2025** | **~658.348** | **~55%** |
| Só **mai/2025** | **430.749** | **~35,9%** |
| Set/2025–Mai/2026 | **~93k** | **~8%** |
| **Jun/2026** | **27** | **~0%** |

Assinatura típica: **rajada de backfill / drenagem agressiva no arranque**, depois **cruzeiro fraco**, depois **fluxo efetivamente parado**.

---

## 4. Leitura estrutural (alimentação × API × UI)

### 4.1 O que **não** é o problema principal

| Hipótese | Porquê cai |
|----------|------------|
| FTS / índice SQLite corrompido | `integrity_check` ok; volume ~1,2M; busca devolve centenas de hits |
| Federated / faixa regional cortando na API (causa do volume) | Já corrigido em caso pontual; dump de datas é propriedade do DB |
| “Só temos 365 dias por desenho da API” como *única* explicação | A API limita **request** a 365d; **dentro** desses 365d a distribuição **não é uniforme** |
| Filtro UI «Último Ano» como causa do índice torto | Afeta **exibição**; não gera o pico de mai/2025 |

### 4.2 O que **é** o problema principal

1. **Janela de ingestão** desenhada em torno de `PNCP_LOCAL_BACKFILL_DAYS=365` (`ingest_dates.resolve_backfill_window`, cap `PNCP_API_MAX_LOOKBACK_DAYS=365`).
2. **Dentro** dessa janela, a alimentação **não particionou de forma equilibrada no tempo**: ~¾ do volume cai em abr–jun/2025.
3. **Incremental pós-arranque** insuficiente (set/2025 em diante em dezenas de milhares/mês).
4. **Paragem recente** (jun/2026 ≈ 27 itens) — sinal forte de worker/fila/stall/ops, não só “histórico curto”.

### 4.3 Modelo mental

```
PNCP nacional (anos)     [████████████████████████████████████]  universo amplo
Janela API (≤365d)       [········████████████████████████····]
Índice local (real)      [········█████▓▓▒▒░░░|]               pico abr–mai/25
UI «Último Ano» (hoje)   [                    |▏]               fatia fina do subconjunto
```

Vocês indexaram **muito** dentro de uma **janela estreita e enviesada**, não “pouco” no absoluto.

---

## 5. Como a API PNCP entra neste diagnóstico

Referência: [`planejamento/05-API-PNCP-EXTERNA.md`](./planejamento/05-API-PNCP-EXTERNA.md).

| Endpoint / regra | Relevância para o estudo |
|------------------|--------------------------|
| `GET /v1/contratacoes/publicacao` | Catálogo; `dataInicial`/`dataFinal` **AAAAMMDD**; **máx. 365 dias** por request (422 se exceder) |
| `GET …/itens` | Alimenta `pncp_itens`; **só isto** sobe `total_itens` |
| `/resultados` | Fornecedor — **pipeline B** (on-demand); **não** explica o enviesamento de datas |
| UF × modalidade | Planner varre scopes (27×5); desbalanceamento temporal ≠ só “faltou UF” |

**Ponto crítico:** o limite de 365 dias da API **autoriza** um índice “de um ano”, mas **não obriga** 36% num mês. O pico e o decaimento são **artefacto do fluxo de alimentação** (backfill/worker/watermark/partição), não do contrato HTTP sozinho.

Campo analisado: `pncp_itens.data_publicacao` (herdado da contratação; **não** é `updated_at` de ingestão). O histograma descreve **quando a compra foi publicada no PNCP**, não quando a linha entrou no SQLite — mas o padrão ainda é compatível com **varredura inicial concentrada** numa faixa de publicação.

---

## 6. Arquitetura de ingestão (contexto)

Resumo alinhado a [`planejamento/03-INGESTAO-24-7.md`](./planejamento/03-INGESTAO-24-7.md) e [`PNCP-CONTEXTO-IA.md`](./PNCP-CONTEXTO-IA.md):

```
Planner → pncp_ingest_queue → Worker
  catalog_page     → pncp_contratos
  contract_items   → pncp_itens (+ FTS)
```

| Peça | Papel |
|------|--------|
| `ingest_dates.py` | Janela backfill (cap 365d) |
| `ingest_planner.py` | Páginas por UF×modalidade + gap-fill contratos sem itens |
| `ingest_worker.py` | Batch (~2s), itens antes de catálogo, backpressure |
| `ingest_backpressure.py` | Pausa catálogo se fila de itens/starve |
| `PNCP_LOCAL_BACKFILL_DAYS` | Default **365** no compose |

Dois regimes de throughput já observados em ops (contexto histórico):

| Regime | Throughput típico | Quando |
|--------|-------------------|--------|
| **Rajada** | ~25k–35k itens/h | Backfill bash / fila inchada |
| **Cruzeiro** | ~10k–15k itens/h | Worker com fila baixa |

O histograma de **mai/2025** é coerente com **regime de rajada** sobre publicações daquela época; a cauda 2026 é coerente com **cruzeiro fraco + stall**.

---

## 7. Distinção de camadas (anti-confusão)

| Camada | O que mede | Exemplo |
|--------|------------|---------|
| **Cobertura do índice** | Linhas em `pncp_itens` e suas datas | 1,2M; 36% em mai/2025 |
| **Recall da busca** | Termo + homolog + filtros API | `pneu` → ~632 |
| **Exibição UI** | Filtros cliente (período, etc.) | «Último Ano» → ~18 |
| **Ops / volumes** | Mounts, compose, Cloudflare | Índices de plataforma vazios = outro incidente |

Correções de UI/API (período default, mensagem de filtros, faixa na federated) **melhoram honestidade e uso do subconjunto existente**. **Não substituem** reequilíbrio da alimentação.

---

## 8. Hipóteses de causa (ordenadas por força)

| # | Hipótese | Evidência a favor | Como falsificar |
|---|----------|-------------------|-----------------|
| H1 | Backfill inicial com janela 365d a partir do arranque do feed | Faixa começa **2025-04-13**; env `PNCP_LOCAL_BACKFILL_DAYS=365` | Comparar watermark/`pncp_ingest_state` com data de go-live |
| H2 | Rajada de ingestão (loop bash ou fila enorme) no bloco abr–mai | Pico **mai/2025 = 36%**; throughput histórico de rajada | Logs de backfill / `items_ok` da época |
| H3 | Incremental sem partição temporal equilibrada após o bloco | Decaimento monótono set→jun | Coverage por mês vs API PNCP “ao vivo” |
| H4 | Worker stalled / autopaused / fila morta em 2026 | **Jun/2026 = 27** | `ingest-status`, heartbeats, `paused_blocked` |
| H5 | Confundir `data_publicacao` com data de ingestão | Histograma é de publicação | Cruzar com `updated_at` do item (análise futura) |

---

## 9. Perguntas em aberto (próxima investigação)

1. **O que disparou o pico de mai/2025?** (data de deploy do researcher, loop `run-pncp-index-ingest-loop.sh`, restore de volume?)
2. **Watermarks por UF×modalidade** — ficaram presos numa sub-janela de datas?
3. **Por que set/2025–mai/2026 não compensaram** o bloco inicial (rate limit PNCP, catalog_heavy, starve invertido)?
4. **Jun/2026 ≈ zero** — stall confirmado nos logs (`ingest PARADA`, `paused_blocked`, queue vazia)?
5. Distribuição de **`updated_at`** vs **`data_publicacao`** — quando as linhas foram realmente escritas?

Comandos úteis (ops; não executados neste doc):

```bash
# Status ingest
curl -s http://127.0.0.1:8012/api/pncp-research/local-index/ingest-status | python3 -m json.tool

# Heartbeats recentes
docker logs pncp_researcher_service 2>&1 | grep -E 'ingest batch|ingest heartbeat|PARADA|catalog_heavy' | tail -40

# Re-medir datas (no contentor / volume)
# SELECT substr(data_publicacao,1,7), COUNT(*) FROM pncp_itens GROUP BY 1 ORDER BY 1;
```

---

## 10. O que já foi descartado / corrigido em paralelo (contexto)

Incidentes **ortogonais** ao enviesamento temporal, mas misturados na mesma época de diagnóstico:

| Tema | Nota |
|------|------|
| Volume `price_platform_data` não montado | TCE/Compras/Notas «indisponíveis» — ops de volume, não PNCP dates |
| Filtro «Último Ano» na UI | Explica recall UI; default «Todo o período» discutido |
| Mensagem «API devolveu X… filtros reduziram Y» | Podia ser enganosa com valor base 0 |
| IndentationError backend | Crash loop — hotfix separado |
| Orphans PNCP no compose principal | Esperados; **não** `--remove-orphans` no stack app |

---

## 11. Conclusões

1. **Problema estrutural de alimentação**, não de busca.
2. O índice é **denso em abr–ago/2025 (~92%)** e **esparso/parado depois** — enviesamento **dentro** do único ano disponível.
3. **1,2M itens** = “muito para 3 meses de publicação; pouco para o resto do ano e para o PNCP completo”.
4. **Jun/2026 com 27 itens** é o sinal mais forte de **fluxo quebrado agora**.
5. Próximo passo natural (quando sair de análise): **watermark, continuidade do worker, estratégia de partição por data/órgão/modalidade** — eixos em [`planejamento/10-SLA-ALIMENTACAO.md`](./planejamento/10-SLA-ALIMENTACAO.md) e [`planejamento/09-GAPS-E-ROADMAP.md`](./planejamento/09-GAPS-E-ROADMAP.md).

---

## 12. Referências internas

| Documento | Relação |
|-----------|---------|
| [`planejamento/05-API-PNCP-EXTERNA.md`](./planejamento/05-API-PNCP-EXTERNA.md) | Contrato API + limite 365d |
| [`planejamento/03-INGESTAO-24-7.md`](./planejamento/03-INGESTAO-24-7.md) | Fila / worker / planner |
| [`planejamento/10-SLA-ALIMENTACAO.md`](./planejamento/10-SLA-ALIMENTACAO.md) | Anti-trava / backpressure |
| [`PNCP-CONTEXTO-IA.md`](./PNCP-CONTEXTO-IA.md) | Ingest + armadilhas de produção |
| [`PNCP-DECLARATIVO.md`](./PNCP-DECLARATIVO.md) | Estado declarativo do módulo |
| `pncp_researcher_service/app/ingest_dates.py` | Cap 365 dias |

---

*Documento de análise gerado a partir do diagnóstico conjunto (dump SQL de datas + rastreio de busca/UI + arquitetura de ingestão). Atualizar §3 se re-medir o DB.*
