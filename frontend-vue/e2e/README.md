# E2E — Technical audit of AI Search / Manual Search

## AI Search (bulk quotation)

The test **runs** the search, waits for it to finish, and produces an engineering analysis:

1. Compares **quotation term × each price title** (tokens, specs %, mg, conflicting families)
2. Price statistics per item: min/median/mean/max, σ, **CV%**, max/min, Δ% vs BASE, position in the range
3. Catalog of **mismatches** (wrong product even when the price is “inside the VAR”)
4. Per-item tables of the worst cases + an appendix of every item

```bash
cd frontend-vue
npm run test:e2e:ia
# or: npm run test:e2e -- e2e/busca-ia-cotacao.spec.mjs
```

Output: `e2e-artifacts/busca-ia-audit-<id>-<ts>.md` (+ `.json`).

**Fails if:** `critical > 0` (outside the range **or** term×candidate mismatch).

## Manual Search (whole quotation, item by item)

Walks **every** quotation item: for each one it opens  
`/pesquisador-pncp/cotacoes/{id}/busca-manual?itemId=…`, waits for the auto-search, and audits.

1. Login → session item list via API
2. Loop: one item at a time (same UX as the individual manual search)
3. Aggregated report: hits per source, UI platforms, out of range, critical

```bash
cd frontend-vue
# .env.e2e: PLAYWRIGHT_COTACAO_ID=138
# optional: PLAYWRIGHT_ITEM_ID=31869          (a single item)
# optional: PLAYWRIGHT_MANUAL_MAX_ITEMS=10    (first N)
npm run test:e2e:manual
```

Output: `e2e-artifacts/busca-manual-cotacao-<id>-<ts>.md` (+ `.json`).

**Fails if:** any item has 0 results, a search error, an empty description, or a price outside the range.  
A lexical mismatch on the broad list is a **warning** (does not fail), unless `PLAYWRIGHT_MANUAL_FAIL_ON_MISMATCH=1`.
