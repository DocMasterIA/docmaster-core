# PNCP — regras de referência (fornecedor, enrich, PDF, busca)

**Atualizado:** junho/2026  
**Audiência:** desenvolvedores e agentes de IA — **ler antes de alterar** fornecedor, enrich, relatório PDF ou busca inteligente.  
**Relacionado:** [`PNCP-CONTEXTO-IA.md`](PNCP-CONTEXTO-IA.md) · [`PNCP-TESTES-FORNECEDOR.md`](PNCP-TESTES-FORNECEDOR.md) · [`PNCP-DECLARATIVO.md`](PNCP-DECLARATIVO.md)

Este documento fixa **invariantes de produto e de código**. Mudanças que violam estas regras tendem a regredir o que já foi corrigido (fornecedor “Não informado”, PDF vazio, site travando na busca).

---

## 1. Princípios de produto (não negociáveis)

1. **Nunca inventar fornecedor/CNPJ** que o PNCP não publicou. Preço estimado de edital ≠ lance homologado.
2. **CNPJ do órgão comprador ≠ CNPJ do fornecedor.** O prefixo do `numeroControlePNCP` é do órgão; não usar como `cnpj_fornecedor`.
3. **Metadados internos (`pncp_*`, `fornecedor_fonte` como nome)** não são razão social — rejeitar na exibição.
4. **Homologado/adjudicado** é o critério de qualidade para cotação “válida”; **em andamento** pode ter preço estimado, mas **sem vencedor** no portal.
5. Meta de cobertura (70–90%) aplica-se a **itens elegíveis na cotação/PDF**, não ao índice SQLite bruto (~1M+ linhas).

---

## 2. Quando o PDF deve mostrar o quê

| Situação PNCP | Fornecedor no PDF | CNPJ no PDF | Valor no PDF |
|---------------|-------------------|-------------|--------------|
| Homologado com vencedor no `/resultados` | Razão social (BrasilAPI se faltar contato) | CNPJ formatado | Preço da fonte |
| `temResultado=false` / “Em andamento” | `Sem fornecedor homologado (compra em andamento)` | `—` | `R$ X,XX (estimado)` |
| Homologado mas PNCP/BrasilAPI sem dado | `Não informado` | `Não informado` | Preço se existir na linha |

**Implementação:** `backend/app/services/pncp_relatorio_itens.py` — `_fonte_pncp_em_andamento_sem_fornecedor`, `_fornecedor_exibicao_relatorio`, `_cnpj_exibicao_relatorio`, `fonte_dict_de_item`.

**Persistir no `source` ao salvar cotação:** `situacaoCompraItemNome`, `temResultado`, `item_homologado` (frontend + `_SOURCE_KEEP_KEYS` no backend).

---

## 3. Pipeline de enriquecimento (ordem fixa)

Arquivo principal: `backend/app/services/pncp_supplier_enrichment.py`

### 3.1 Fluxo em `enrich_supplier_fields_in_payloads`

```
1. _ensure_pncp_compra_keys     → numero_pncp, ano_compra, sequencial_compra, numero_item
2. flatten_supplier_fields      → promover source aninhado (sourceRaw)
3. _promote_supplier_from_deep_walk
4. BrasilAPI (1ª passagem)      → itens que já têm CNPJ
5. Lookup PNCP por item         → get_contract_supplier_snapshot_sync
6. _merge_supplier_snap_into_payload
7. deep walk se merge vazio
8. BrasilAPI (2ª passagem)      → CNPJ obtido só após PNCP
9. Passagem final: deep walk + BrasilAPI
```

**Não inverter** passos 4–8 (BrasilAPI antes do PNCP quebrava itens que só ganhavam CNPJ depois).

### 3.2 Quando consultar PNCP

- `_should_attempt_pncp_supplier_lookup`: se `_pncp_compra_keys_present` → **sempre tentar**, mesmo não homologado (busca em lote).
- PDF / `enrich_missing_supplier_fields_for_cotacao`: **`only_homologated=False`** e `ignore_add_source_setting=True`.

### 3.3 Lookup PNCP

- Base URL Django: `https://pncp.gov.br/api/pncp` (`PNCP_API_BASE`).
- Researcher: `https://pncp.gov.br/pncp-api` — **não unificar** sem testar ambos os paths.
- Ordem por item: `/itens/{n}/resultados` → `/resultados` → catálogo → contratos → `_supplier_snapshot_compra_fallback`.
- **Fallback entre itens da mesma compra:** só quando o item específico não tem vencedor; não substituir vencedor de outro item no relatório sem `numero_item` correto.

### 3.4 Parse do controle PNCP

Formatos suportados em `_parse_ano_seq_from_numero_pncp`:

- `CNPJ-1-2024-42`
- `CNPJ-1-000026/2025`

Prioridade de ano/seq: colunas ORM → `source` → parse do `numero_pncp`.

---

## 4. Armadilhas de código (não reintroduzir)

| Problema | Sintoma | Regra |
|----------|---------|--------|
| `flatten` chama `_fornecedor_display_name_from_source` que chama `flatten` | `RecursionError`, PDF/sessão 500 | `_fornecedor_display_name_from_source` **não** chama `flatten` |
| `PNCP_ADD_SOURCE_ONLY_HOMOLOGATED=true` + busca lote | Itens entram sem enrich PNCP | Default **`false`**; PDF sempre `only_homologated=False` |
| Limites 12/48 lookups | Últimos itens sempre “Não informado” | PDF: 96 PNCP / 64 BrasilAPI; adicionar fonte: 96/96 |
| Ignorar `pncp_*` no flatten | Nome virava metadata e sumia | Rejeitar `pncp_*` e CNPJ-only como nome |
| `_supplier_snapshot_compra_fallback` ausente | `NameError` no enrich | Manter função antes de `get_contract_supplier_snapshot_sync` |
| Prefetch stale no PDF | Enrich grava DB mas PDF lê `source` velho | PDF usa `cotacao.cotacoes_itens` (query fresca), não confiar só em prefetch antigo |
| Bulk autostart após sair da página | API saturada, site trava | Pausar bulk ao navegar fora (`usePncpBulkAutostart`) |

---

## 5. Busca inteligente — modos

Arquivos: `frontend-vue/src/views/BuscaInteligenteCotacoes.vue`, `pncp_researcher_service/app/service.py`

| Modo | `somente_homologados` | `busca_lote` | Comportamento esperado |
|------|------------------------|--------------|------------------------|
| Manual / top-3 | `true` | `false` | Prioriza itens com vencedor; faixa de preço por item |
| Lote / autostart | `false` | `true` | Mais resultados; **muitos “em andamento” sem fornecedor** |

**Scoring (lote):** itens sem `cnpj_fornecedor` e `temResultado=false` levam penalidade **−35** no score — ficam no fim da lista, não no topo.

**Não alterar** `somente_homologados: !bulkMode` no frontend sem revisar esta tabela e o PDF.

---

## 6. Arquivos sensíveis (mudança exige teste)

| Área | Ficheiros |
|------|-----------|
| Enrich PNCP/BrasilAPI | `backend/app/services/pncp_supplier_enrichment.py` |
| PDF / fontes | `backend/app/services/pncp_relatorio_itens.py`, `pncp_relatorio_api.py`, `pncp_relatorio_pdf.py` |
| Salvar cotação | `backend/app/pncp_cotacao_api.py` (`_SOURCE_KEEP_KEYS`, enrich ao inserir) |
| Busca + score | `pncp_researcher_service/app/service.py`, `local_index.py`, `supplier_resolver.py` |
| Frontend busca/sessão | `BuscaInteligenteCotacoes.vue`, `usePncpBulkAutostart.js`, `useSessionUser.js`, `router/index.js` |
| Testes mínimos | `backend/app/tests/test_pncp_supplier_enrichment.py` |

---

## 7. Variáveis de ambiente (defaults jun/2026)

| Variável | Default | Notas |
|----------|---------|--------|
| `PNCP_ADD_SOURCE_ENRICH_SUPPLIER` | `true` | Desligar só em emergência de timeout |
| `PNCP_ADD_SOURCE_ONLY_HOMOLOGATED` | **`false`** | `true` quebra enrich em busca lote |
| `PNCP_ADD_SOURCE_MAX_PNCP_LOOKUPS` | `96` | |
| `PNCP_ADD_SOURCE_MAX_BRASILAPI_LOOKUPS` | `96` | |
| `PNCP_RELATORIO_PDF_SKIP_ENRICH` | `false` | |
| `PNCP_RELATORIO_PDF_MAX_PNCP_LOOKUPS` | `96` | |
| `PNCP_RELATORIO_PDF_MAX_BRASILAPI_LOOKUPS` | `64` | |

Definições: `backend/mdlicitatech/settings.py`.

---

## 8. Docker — dois composes

| Stack | Comando |
|-------|---------|
| Backend + Vue | `docker compose up -d --build backend frontend-vue` |
| PNCP researcher | `docker compose -f docker-compose.pncp.yml up -d --build pncp_researcher_service` |

**`pncp_researcher_service` não existe** no `docker-compose.yml` principal (isolado de propósito). Ver [`deploy/PNCP-RESEARCHER-24-7.md`](deploy/PNCP-RESEARCHER-24-7.md).

Produção com backfill: `PNCP_BUILD=1 ./scripts/ensure-pncp-researcher.sh` — evita `down -v`.

---

## 9. Checklist antes de merge (fornecedor/PDF)

1. `python -m py_compile backend/app/services/pncp_supplier_enrichment.py`
2. Testes: `backend/app/tests/test_pncp_supplier_enrichment.py` (19 casos)
3. **Caso A — em andamento:** `02267698000131-1-000026/2025` item 6 → sem fornecedor no PNCP; PDF com texto “compra em andamento”, não bug silencioso
4. **Caso B — homologado:** uma fonte com `temResultado=true` na busca manual → PDF com fornecedor + CNPJ após regerar
5. Busca lote: confirmar que penalidade de score ou filtro não foi removida sem decisão de produto
6. Navegar fora do pesquisador durante bulk → requests bulk pausam

---

## 10. O que **não** é bug

- Fornecedor vazio em pregão **“Em andamento”** com `temResultado=false` (ex.: Mossâmedes/GO acebrofilina R$ 9,97 estimado).
- Telefone/e-mail vazio quando Receita Federal não publica contato (limite BrasilAPI).
- `cobertura_cnpj_pct` baixo no índice total — KPI errado para qualidade da cotação.

---

## 11. Evoluções futuras (fora do escopo atual)

- Filtrar busca lote para **não gravar** fontes sem `cnpj_fornecedor` (decisão de produto).
- Backfill Fase B: persistir vencedor no índice SQLite na ingestão.
- Comando/API para re-enriquecer sessão inteira sem regerar PDF item a item.

Qualquer uma destas exige atualizar **este documento** e [`PNCP-TESTES-FORNECEDOR.md`](PNCP-TESTES-FORNECEDOR.md).

---

## 12. Busca inteligente — similaridade e camadas (recall)

**Problema típico:** descrição longa de cotação (`AGULHA … CX C/100 UNIDADES`) retorna 0 itens; termo mais curto encontra.

**Pipeline (`pncp_researcher_service`):**

1. **`preprocess_cotacao_search_term`** — compacta `13 X 4,5` → `13x45`, calibre `26 G½` → `26g`, remove embalagem (`CX C/100 UNIDADES`).
2. **`build_search_query_tiers`** — camadas em ordem:
   - `strict` — todos os tokens (prioridade máxima no score);
   - `core` — substantivos + specs, ratio 75% se ≥4 tokens (ex.: calibre opcional);
   - `flex` — k-of-n (`PNCP_SEARCH_TIER_FLEX_RATIO`, default 0.65);
   - `anchor` — 2 primeiros tokens do núcleo (último recurso).
3. **`local_item_search`** — FTS/LIKE pelo âncora (`agulha`); filtra linhas pela **camada mais estrita** que casar.
4. **Score** — bônus +10/+6/+2 por `search_tier` strict/core/flex.

**Não fazer:**

- Exigir AND de embalagem (`100`, `unidades`, `cx`) no match.
- Truncar descrição longa pegando tokens sequenciais sem `_pick_core_token_groups`.
- Remover `preprocess_cotacao_search_term` antes de tokenizar (quebra dimensões `13x45`).

**Deploy:** `docker compose -f docker-compose.pncp.yml up -d --build pncp_researcher_service`

**Testes:** `pytest pncp_researcher_service/tests/test_search_recall_helpers.py -v` (caso agulha).
