# PNCP V2 — deploy no servidor

## Fases implementadas

| Fase | Conteúdo |
|------|----------|
| 1 | Ingestão resiliente (autopause, watermarks, `GET /local-index/ingest-status`) |
| 2 | FTS5 em `pncp_itens` (`PNCP_FTS5_ENABLED`) |
| 3 | Fallback híbrido na busca inteligente (`PNCP_HYBRID_*`) |
| 4 | `GET /local-index/operational-status`, `fts-status`, `POST fts-rebuild` |

## Atualizar o contentor PNCP

```bash
cd /home/docmaster
PNCP_BUILD=1 docker compose -f docker-compose.pncp.yml \
  -f docker-compose.pncp.override.yml \
  -f docker-compose.pncp.noports.yml \
  up -d --build --force-recreate pncp_researcher_service
```

## Reconstruir índice FTS (uma vez após upgrade, ~568k itens)

```bash
docker exec pncp_researcher_service python -c "
import urllib.request
req = urllib.request.Request(
    'http://127.0.0.1:8012/api/pncp-research/local-index/fts-rebuild',
    method='POST',
    data=b'',
)
print(urllib.request.urlopen(req, timeout=3600).read().decode())
"
```

Ou pelo host (se porta 8012 estiver mapeada):

```bash
curl -sS -X POST http://127.0.0.1:8012/api/pncp-research/local-index/fts-rebuild
```

## Verificar

```bash
curl -s http://127.0.0.1:8012/api/pncp-research/local-index/operational-status | python3 -m json.tool
```

`fts.needs_rebuild` deve ficar `false` após o rebuild.

## Variáveis (opcional)

| Variável | Default | Função |
|----------|---------|--------|
| `PNCP_INGEST_WATERMARK_RESUME` | 1 | Backfill retoma de `last_page+1` |
| `PNCP_BACKFILL_ITEM_CONCURRENCY` | 12 | GET de itens em paralelo no backfill |
| `PNCP_FTS5_ENABLED` | 1 | Busca FTS5 vs LIKE |
| `PNCP_HYBRID_FALLBACK_ENABLED` | 1 | Complemento PNCP ao vivo |
| `PNCP_HYBRID_MIN_LOCAL_RESULTS` | 8 | Limiar para acionar live |
| `PNCP_HYBRID_MAX_LIVE_PAGES` | 6 | Páginas live no fallback |

Documentação completa:

- [README.md](./README.md) — índice
- [PNCP-INGESTAO-INDEX-24-7.md](./PNCP-INGESTAO-INDEX-24-7.md) — loop 24/7, volumes, troubleshooting
- [PNCP-API-INDICE-LOCAL.md](./PNCP-API-INDICE-LOCAL.md) — endpoints detalhados
- [PNCP-SCRIPTS-REFERENCIA.md](./PNCP-SCRIPTS-REFERENCIA.md) — scripts e compose
