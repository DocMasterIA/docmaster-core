# Módulo fontes de preços — 05 Notas Fiscais

**Status:** Fase 2 (ingest) — parser + materialize ativos.

## IDs

| Campo | Valor |
|-------|--------|
| `platform_id` | `notas_fiscais` |
| Inciso | `inciso_v` → bucket UI `notasFiscais` |
| Esfera | `federal` |
| Feed | `price_index_feed_notas_fiscais` `:8017` |
| DB | `/data/platforms/notas_fiscais_local.db` |
| Raw | `…/data/notas_fiscais/raw/{YYYY}/{YYYYMM}_NFe/` |

## Mapeamento de preço

- `VALOR UNITÁRIO` → `valor_unitario` **e** `valor_unitario_homologado` (preço efetivo da NF)
- Join `NotaFiscal` por `CHAVE DE ACESSO`; só `EVENTO MAIS RECENTE` ≈ Autorização de Uso
- Órgão preferido da Nota (Item muitas vezes vem “Sem informação”)

## Endpoints (feed)

- `GET  …/notas_fiscais/ingest-status`
- `POST …/notas_fiscais/ensure`
- `POST …/notas_fiscais/validate-structure`
- `POST …/notas_fiscais/ingest` (`data_dir`)
- `POST …/notas_fiscais/ingest-sample`

## Ingest completo (exemplo)

```bash
docker compose -f docker-compose.pncp.yml up -d --build price_index_feed_notas_fiscais
docker exec -d price_index_feed_notas_fiscais sh -c '
python -c "
import json,urllib.request
body=json.dumps({\"data_dir\":\"/data/notas_fiscais/raw\"}).encode()
req=urllib.request.Request(
  \"http://127.0.0.1:8017/api/pncp-feed/price-platform-indexes/notas_fiscais/ingest\",
  data=body,method=\"POST\",headers={\"Content-Type\":\"application/json\"})
open(\"/tmp/nf_ingest_out.json\",\"w\").write(urllib.request.urlopen(req,timeout=14400).read().decode())
" > /tmp/nf_ingest.log 2>&1
'
```
