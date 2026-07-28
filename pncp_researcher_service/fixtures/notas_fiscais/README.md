# Fixtures Notas Fiscais (Portal da Transparência)

Mínimo para E2E de ingest:
- `fixture-NotaFiscal.csv` — 1 nota autorizada + 1 rejeitada (`Sem informação`)
- `fixture-NotaFiscalItem.csv` — 2 itens da autorizada + 1 da rejeitada (não deve entrar)

Encoding: cp1252-compatible ASCII; delimiter `;`.

Uso: `ingest_notas_fiscais_sample()` / `POST …/ingest-sample`
