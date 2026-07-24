# E2E — Auditoria técnica Busca IA

O teste **executa** a busca, espera concluir e produz análise para engenharia:

1. Compara **termo da cotação × título de cada preço** (tokens, specs %, mg, famílias conflitantes)
2. Estatística de preço por item: min/mediana/média/max, σ, **CV%**, max/min, Δ% vs BASE, posição na faixa
3. Catálogo de **mismatches** (produto errado mesmo com preço “dentro da VAR”)
4. Tabelas por item dos piores casos + anexo de todos os itens

## Rodar

```bash
cd frontend-vue
npm run test:e2e:unit
npm run test:e2e   # ~10–20 min na cotação 138
```

Saída: `e2e-artifacts/busca-ia-audit-<id>-<ts>.md` (+ `.json` com `itemReports`).

Reprocessar JSON antigo (se tiver `data.groups`):

```bash
node --input-type=module -e "..."  # ver scripts ad-hoc / re-run test:e2e
```

**Critérios de falha do teste:** `critical > 0` (fora da faixa **ou** mismatch termo×candidato).
