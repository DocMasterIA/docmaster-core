# Invoice fixtures (Transparency Portal)

Minimum set for ingest E2E:
- `fixture-NotaFiscal.csv` — 1 authorized invoice + 1 rejected (`Sem informação`)
- `fixture-NotaFiscalItem.csv` — 2 items from the authorized invoice + 1 from the rejected one (must not be ingested)

Encoding: cp1252-compatible ASCII; delimiter `;`.

Usage: `ingest_notas_fiscais_sample()` / `POST …/ingest-sample`
