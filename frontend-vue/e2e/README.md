# E2E — Auditoria técnica Busca IA / Manual

## Busca IA (bulk cotação)

O teste **executa** a busca, espera concluir e produz análise para engenharia:

1. Compara **termo da cotação × título de cada preço** (tokens, specs %, mg, famílias conflitantes)
2. Estatística de preço por item: min/mediana/média/max, σ, **CV%**, max/min, Δ% vs BASE, posição na faixa
3. Catálogo de **mismatches** (produto errado mesmo com preço “dentro da VAR”)
4. Tabelas por item dos piores casos + anexo de todos os itens

```bash
cd frontend-vue
npm run test:e2e:ia
# ou: npm run test:e2e -- e2e/busca-ia-cotacao.spec.mjs
```

Saída: `e2e-artifacts/busca-ia-audit-<id>-<ts>.md` (+ `.json`).

**Falha se:** `critical > 0` (fora da faixa **ou** mismatch termo×candidato).

## Busca Manual (cotação inteira, item a item)

Percorre **todos** os itens da cotação: para cada um abre  
`/pesquisador-pncp/cotacoes/{id}/busca-manual?itemId=…`, espera a auto-busca e audita.

1. Login → lista itens da sessão via API
2. Loop: um item por vez (mesma UX da manual individual)
3. Relatório agregado: hits por fonte, plataformas UI, fora da faixa, críticos

```bash
cd frontend-vue
# .env.e2e: PLAYWRIGHT_COTACAO_ID=138
# opcional: PLAYWRIGHT_ITEM_ID=31869          (só um item)
# opcional: PLAYWRIGHT_MANUAL_MAX_ITEMS=10    (N primeiros)
npm run test:e2e:manual
```

Saída: `e2e-artifacts/busca-manual-cotacao-<id>-<ts>.md` (+ `.json`).

**Falha se:** algum item com 0 resultados, erro de busca, descrição vazia, ou preço fora da faixa.  
Mismatch lexical na lista ampla = **aviso** (não falha), salvo `PLAYWRIGHT_MANUAL_FAIL_ON_MISMATCH=1`.
