# PNCP — valor homologado vs estimado

Documento de referência para evolução do índice local (`pncp_itens`). Consolidado em jun/2026 após implementação do fetch de `/resultados` no ingest.

---

## 1. Problema

O endpoint **`GET /itens`** devolve sobretudo valores **estimados** (planejamento da licitação):

| Campo típico no `/itens` | Significado |
|--------------------------|-------------|
| `valorUnitarioEstimado` | Preço unitário estimado no edital |
| `valorTotal` | Total estimado |
| `quantidade` | Quantidade planejada |
| `situacaoCompraItemNome` | Ex.: `"Homologado"` |
| `temResultado` | Indica que existe resultado publicado **em outro endpoint** |

Para **busca de preços**, o valor útil é o **homologado** (vencedor / resultado da disputa), que costuma estar em **`GET /resultados`**.

### Exemplo real (contrato `23066640000108` / compra `2025/39` / item `1`)

**`/itens` (catálogo):**

```json
{
  "numeroItem": 1,
  "descricao": "Consultoria e Assessoria - Recursos Humanos",
  "valorUnitarioEstimado": 157208.73,
  "valorTotal": 157208.73,
  "quantidade": 1,
  "situacaoCompraItemNome": "Homologado",
  "temResultado": true
}
```

**`/itens/1/resultados`:**

```json
{
  "valorUnitarioHomologado": 21.48,
  "valorTotalHomologado": 170121.6,
  "quantidadeHomologada": 7920,
  "niFornecedor": "01831685000180",
  "nomeRazaoSocialFornecedor": "COOPERATIVA DOS PROPRIETARIOS DE TRANSPORTE DE VEICULOS",
  "situacaoCompraItemResultadoNome": "Informado"
}
```

Estimado e homologado podem divergir **muito** (unidade, quantidade e preço).

---

## 2. Endpoints PNCP

| Recurso | URL (padrão) |
|---------|----------------|
| Itens da compra | `GET {PNCP_PNCP_API}/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens` |
| Resultados da compra (todos os itens) | `GET .../compras/{ano}/{seq}/resultados` |
| Resultado de um item | `GET .../compras/{ano}/{seq}/itens/{numeroItem}/resultados` |

Campos de preço homologado (quando publicados):

- `valorUnitarioHomologado`
- `valorTotalHomologado`
- `quantidadeHomologada`

Fornecedor vencedor: `niFornecedor`, `nomeRazaoSocialFornecedor`, etc.

**Limitação:** nem todo item `"Homologado"` tem preço em `/resultados` (estudos PNCP: parcela relevante sem `valorUnitarioHomologado` — compra não efetivada, anulada, etc.).

---

## 3. O que o docmaster faz hoje (pós-implementação)

### 3.1 Config

| Env | Default (compose) | Efeito |
|-----|-------------------|--------|
| `PNCP_INGEST_FETCH_ITEM_RESULTADOS` | `1` | Busca `/resultados` durante ingest de itens |
| `PNCP_INGEST_BACKFILL_MODE` | `1` | `REFRESH_DAYS` efetivo = 0 → re-fetch contínuo |

Código: `pncp_researcher_service/app/config.py`

### 3.2 Fluxo no ingest (`contract_items`)

Arquivo: `app/ingest_worker.py` → `process_contract_items_task`

1. `GET /itens`
2. Se `PNCP_INGEST_FETCH_ITEM_RESULTADOS=1` e item com `temResultado` ou situação homologada:
   - **1×** `GET .../resultados` (nível compra)
   - **Por item faltante:** `GET .../itens/{n}/resultados`
3. `upsert_contract_items(..., resultados_by_item=...)`

Lógica de fetch: `app/pncp_client.py` — `fetch_resultados_map_for_items`, `fetch_contract_items_with_resultados`

### 3.3 Persistência (`pncp_itens`)

Migração automática em `app/local_index.py` — `_migrate_pncp_itens_homolog_columns`.

| Coluna | Conteúdo |
|--------|----------|
| `valor_unitario_estimado`, `valor_total_estimado`, `quantidade_estimada` | Do `/itens` |
| `valor_unitario_homologado`, `valor_total_homologado`, `quantidade_homologada` | Do `/resultados` |
| `valor_unitario`, `valor_total`, `quantidade` | **Preferência homologado**; senão estimado |
| `cnpj_fornecedor`, `fornecedor`, `fornecedor_fonte` | Do resultado quando disponível |
| `resultado_resolvido_at` | Timestamp do enrich de preço homologado |

Update por `numero_pncp` + `numero_item` evita duplicata ao corrigir preço.

Helpers: `app/supplier_resolver.py` — `extract_homologated_pricing`, `item_row_needs_resultado_fetch`, `index_resultados_by_numero_item`

### 3.4 Busca local

`local_item_search` expõe colunas estimado e homologado nos resultados (`_row_to_local_item`).

Enrich na busca (`enrich_homolog_items_from_pncp`) continua focado em **fornecedor** para homologados sem CNPJ no índice — **não** substitui o backfill de preço em massa.

---

## 4. Itens já no DB antes do deploy

### 4.1 Estado imediato após deploy

| Situação | `valor_unitario` / `valor_total` | `valor_*_homologado` |
|----------|----------------------------------|----------------------|
| Indexado **antes** do código novo | Em geral **estimado** (só `/itens`) | `NULL` |
| **Re-processado** pelo worker novo | Homologado (se PNCP tiver) | Preenchido |
| **Fetch novo** após deploy | Homologado desde o início | Preenchido |

**Deploy sozinho não altera linhas existentes.**

### 4.2 O que significa “re-processado”

1. Contrato entra na fila `contract_items` (topup, catálogo, backfill `REFRESH=0`, etc.).
2. Worker chama PNCP (`/itens` + `/resultados` com código novo).
3. SQLite faz **UPDATE** na mesma linha (`numero_pncp` + `numero_item`).

Não é só redeploy nem só consultar a API de busca — é **passar outra vez pela fila de ingest**.

Com backfill 24/7, ~432k contratos rodam em **ciclos**; homologado enche **gradualmente**, não de uma vez.

### 4.3 Verificação no DESKTOP

```bash
# quantos já têm homologado
docker exec pncp_researcher_service sqlite3 /data/pncp/pncp_researcher_local.db \
  "SELECT COUNT(*) FROM pncp_itens WHERE valor_unitario_homologado IS NOT NULL;"

# total de itens
docker exec pncp_researcher_service sqlite3 /data/pncp/pncp_researcher_local.db \
  "SELECT COUNT(*) FROM pncp_itens;"

# amostra comparando estimado vs homologado
docker exec pncp_researcher_service sqlite3 /data/pncp/pncp_researcher_local.db \
  "SELECT numero_pncp, numero_item, valor_unitario_estimado, valor_unitario_homologado, valor_unitario
   FROM pncp_itens
   WHERE valor_unitario_homologado IS NOT NULL
   LIMIT 10;"
```

Teste manual PNCP (fora do container):

```bash
curl -s "https://pncp.gov.br/pncp-api/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens/{n}/resultados" | jq .
```

---

## 5. Enrich “só resultados” (implementado)

Contratos **já no índice** passam a receber preço homologado **sem refetch de `/itens`**.

### 5.1 Como funciona

1. **Planner** (a cada ciclo ~5 min): enfileira até `PNCP_INGEST_RESULTADOS_TOPUP_LIMIT` contratos (default **400**) com itens homologados e `valor_unitario_homologado IS NULL`.
2. **Worker**: se o contrato **não** precisa refresh de `/itens`, em vez de `skip` chama `enrich_contract_resultados_only`:
   - `GET .../resultados` (1× por contrato, fallback por item)
   - `UPDATE pncp_itens` in-place
3. Log: `ingest resultados-only {numero_pncp}: N itens homologados`

### 5.2 Config

| Env | Default | Efeito |
|-----|---------|--------|
| `PNCP_INGEST_FETCH_ITEM_RESULTADOS` | `1` | Liga fetch de `/resultados` |
| `PNCP_INGEST_RESULTADOS_TOPUP_ENABLED` | `1` | Planner enfileira contratos pendentes |
| `PNCP_INGEST_RESULTADOS_TOPUP_LIMIT` | `400` | Máx. contratos enfileirados por ciclo do planner |

### 5.3 Código

| Função | Arquivo |
|--------|---------|
| `enrich_contract_resultados_only` | `app/local_index.py` |
| `apply_resultados_to_stored_items` | `app/local_index.py` |
| `enqueue_contracts_needing_resultados` | `app/ingest_planner.py` |
| Worker resultados-only (ex-`skip`) | `app/ingest_worker.py` → `_run_item_task` |

### 5.4 Velocidade esperada

~400 contratos / 5 min do planner ≈ **~115k contratos/dia** enfileirados (se a fila absorver). Cada contrato = 1 GET `/resultados` (+ poucos GETs por item). O índice homologado enche **muito mais rápido** que esperar re-process completo (`/itens` + `/resultados`).

### 5.5 Verificação

```bash
docker logs pncp_researcher_service --since 30m | grep "resultados-only\|topup resultados"
```

```bash
docker exec pncp_researcher_service sqlite3 /data/pncp/pncp_researcher_local.db \
  "SELECT COUNT(*) FROM pncp_itens WHERE valor_unitario_homologado IS NOT NULL;"
```

---

## 6. Deploy do código actual (fetch no ingest + resultados-only)

```bash
git pull
./scripts/deploy-pncp-researcher-code.sh
docker compose -f docker-compose.pncp.yml -f docker-compose.pncp.noports.yml up -d --force-recreate pncp_researcher_service
```

Confirmar env:

```bash
docker exec pncp_researcher_service printenv | grep -E 'FETCH_ITEM_RESULTADOS|BACKFILL'
```

Desligar fetch de resultados (só ingest, sem homologado):

```bash
PNCP_INGEST_FETCH_ITEM_RESULTADOS=0
```

---

## 7. Testes

```bash
cd docmaster-core
PYTHONPATH=. .venv/bin/pytest pncp_researcher_service/tests/test_item_homolog_pricing.py -q
PYTHONPATH=. .venv/bin/pytest pncp_researcher_service/tests/test_supplier_resolver.py -q -k homolog
```

Fixtures: `tests/fixtures/resultado_item_pricing.json`

---

## 8. Referências no repositório

| Tópico | Arquivo |
|--------|---------|
| Config backfill + resultados | `app/config.py` |
| Fetch `/resultados` | `app/pncp_client.py` |
| Upsert + colunas homologado | `app/local_index.py` |
| Worker ingest itens | `app/ingest_worker.py` |
| Parsing preço / fornecedor | `app/supplier_resolver.py` |
| Compose envs | `docker-compose.pncp.yml` |
| Modo backfill (pipeline cheio) | plano `pncp_backfill_mode` (Cursor plans) |

Manual PNCP: campos `valorUnitarioHomologado`, `valorTotalHomologado` na API de resultados de item de contratação.

---

## 9. Decisões em aberto

- [x] Job **só resultados** para migrar itens existentes (planner + worker resultados-only)
- [ ] Métricas heartbeat `itens_com_homologado` / `resultados_ok_1h`
- [ ] Exibir estimado vs homologado na UI de pesquisa de preços
- [ ] Aumentar `RESULTADOS_TOPUP_LIMIT` se fila absorver sem 429

---

*Última atualização: junho 2026 — ingest + enrich resultados-only no worker/planner.*
