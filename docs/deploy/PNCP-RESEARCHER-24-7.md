# PNCP Researcher — rodar 24h sem cair no `up -d`

**Guia completo de alimentação do índice (loop, watermarks, paralelo, monitorização, o que não fazer):**  
→ [PNCP-INGESTAO-INDEX-24-7.md](./PNCP-INGESTAO-INDEX-24-7.md)

## Checklist 24/7 (produção)

1. **Volume fixo** (uma vez, com o `.db` grande):
   ```bash
   ./scripts/find-pncp-db-volumes.sh
   PNCP_DATA_VOLUME=docmaster_pncp_researcher_data ./scripts/attach-pncp-volume.sh
   ```
   Isso cria `docker-compose.pncp.override.yml` (volume `external`). **Não apague** esse ficheiro.

2. **Subir / manter** (após reboot, deploy de código, etc.):
   ```bash
   ./scripts/ensure-pncp-researcher.sh
   ```
   Usa `up -d --no-recreate` — não mata o contentor nem o backfill em curso.

3. **Rebuild de imagem** (só quando mudar código):
   ```bash
   PNCP_BUILD=1 ./scripts/ensure-pncp-researcher.sh
   ```
   Evite `down -v`. O índice fica no volume, não na imagem.

4. **Nunca** `docker compose -f docker-compose.pncp.yml down -v` (apaga o SQLite).

5. **Alimentar o índice (cobertura de busca alta)** é outro processo do que «manter API 24/7»:
   - `ensure-pncp-researcher.sh` → só sobe o contentor.
   - `run-pncp-index-ingest-loop.sh` → busca no PNCP e grava contratos/itens no SQLite (rode em `nohup` ou cron).
   - Com **`PNCP_INGEST_WATERMARK_RESUME=1`** (default), cada corrida retoma de `last_page+1` por UF/modalidade; ao esgotar o catálogo, volta à página 1 (novos editais no topo). O que importa é **`next_page` subir** em `GET /local-index/ingest-status`, não só `total_itens`/dia.
   - Busca inteligente: FTS5 local + fallback híbrido PNCP ao vivo quando local < 8 resultados (`PNCP_HYBRID_*`).
   - Não use um único `curl` com `max_paginas: null` no Brasil inteiro (trava dias).

```bash
nohup ./scripts/run-pncp-index-ingest-loop.sh >> ~/pncp-ingest.log 2>&1 &
tail -f ~/pncp-ingest.log
# Ver progresso no Docker:
docker logs -f pncp_researcher_service 2>&1 | grep backfill
```

6. **Monitorar**:
   ```bash
   curl -s http://127.0.0.1:8012/api/pncp-research/health | python3 -m json.tool
   ```
   `db_bytes` deve ser centenas de MB; `index_hint` vazio. Se avisar `/tmp` ou índice pequeno → volume errado.

## Por que caía antes

Com `pncp_researcher_service` no **mesmo** `docker-compose.yml`, um `docker compose up -d backend` (ou grafana, etc.) **reconcilia o projeto inteiro** e pode **recriar** o contentor PNCP. Qualquer backfill/alimentação longa morre no meio.

## Solução

Stack **isolada**: `docker-compose.pncp.yml` + rede `docmaster_net`.

O compose principal (`docker-compose.yml`) **não** define mais o serviço PNCP; o `backend` só se liga pela rede partilhada.

## Uso diário

### 1. Subir o PNCP (uma vez após reboot / deploy)

A partir de **`~`** (compose na home, código em `~/docmaster-core/`):

```bash
# Copie/atualize para ~: docker-compose.pncp.yml e scripts/ensure-pncp-researcher.sh
./scripts/ensure-pncp-researcher.sh
```

O script define `PNCP_BUILD_CONTEXT=docmaster-core` automaticamente.

A partir de **`~/docmaster-core`**:

```bash
cd ~/docmaster-core
./scripts/ensure-pncp-researcher.sh
```

O aviso `orphan containers` **não aparece** com o projeto `name: docmaster-pncp` (ficheiro atualizado). Se ainda aparecer, ignore — são os outros serviços no projeto `docmaster`, não erro do PNCP.

Na primeira subida, `OFF` no health por 10–30s é normal (`health: starting`).

### 2. Subir outros serviços **sem mexer no PNCP**

```bash
docker compose up -d --no-recreate backend
docker compose up -d --no-recreate grafana prometheus
```

Evite `docker compose up -d` **sem** serviço e **sem** `--no-recreate` se o PNCP estiver a alimentar — isso ainda pode recriar tudo do ficheiro principal.

**Nunca** use `docker compose down` no projeto principal se quiser manter o PNCP; para parar só o backend:

```bash
docker compose stop backend
```

### 3. Logs / saúde

```bash
docker compose -f docker-compose.pncp.yml logs -f
curl -s http://127.0.0.1:8012/api/pncp-research/health
```

### 4. Backfill do índice local

```bash
curl -sS -X POST "http://127.0.0.1:8012/api/pncp-research/local-index/backfill" \
  -H "Content-Type: application/json" \
  -d '{"months": 12, "max_paginas": null, "tamanho_pagina": 50, "uf": null, "codigo_municipio_ibge": null, "include_items": true}'
```

Se aparecer `unable to open database file`, reconstrua a imagem (entrypoint corrige permissões em `/data/pncp`):

```bash
docker compose -f docker-compose.pncp.yml up -d --build --force-recreate
```

## Rede

| Contentor | Rede |
|-----------|------|
| `pncp_researcher_service` | `docmaster_net` |
| `backend` | `default` + `docmaster_net` |

URL no Django (inalterada): `PNCP_RESEARCHER_BASE_URL=http://pncp_researcher_service:8012`

## Compose a partir de `~` (pai do repo)

Se o `docker-compose.yml` principal usa `context: docmaster-core`, no `docker-compose.pncp.yml` use:

```yaml
build:
  context: docmaster-core
  dockerfile: pncp_researcher_service/Dockerfile
```

e execute os comandos `-f docker-compose.pncp.yml` **a partir de `~`**, ou copie o ficheiro `.pncp.yml` para a mesma pasta do compose principal.

## Recuperar índice antigo (800k+ itens → volume novo vazio)

Ao mudar para `docker-compose.pncp.yml` (projeto `docmaster-pncp`), o Docker criou um **volume novo** vazio. O SQLite grande ficou no volume **antigo** (outro nome).

### 1. Achar o volume certo

```bash
./scripts/find-pncp-db-volumes.sh
```

Procure o volume com **centenas de MB** (ex.: `docmaster_pncp_researcher_data`, `docmaster-core_pncp_researcher_data`, `docmaster-pncp_pncp_researcher_data`).

### 2. Ligar o PNCP a esse volume

```bash
# troque pelo nome que o script mostrou com o .db grande
PNCP_DATA_VOLUME=docmaster_pncp_researcher_data ./scripts/attach-pncp-volume.sh
```

Confira:

```bash
curl -s http://127.0.0.1:8012/api/pncp-research/local-index/stats
```

`total_itens` / `total_contratos` devem voltar perto do que tinha antes.

### 3. Não apague volumes sem olhar

```bash
docker volume ls | grep pncp
```

O volume pequeno novo pode ser `docmaster-pncp_pncp_researcher_data` (2100 contratos) — pode remover **depois** de confirmar que o grande está montado.

### 4. Se nenhum volume tiver o .db grande

O índice só volta com **novo backfill** (demora) ou **restauro de backup** `.db` copiado para `/data/pncp/pncp_researcher_local.db` no volume.

## Reinício automático

`restart: always` no compose PNCP — o Docker **reinicia o contentor** após crash.

Após **reboot do servidor**, o daemon Docker sobe contentores com `restart: always` automaticamente **se** o volume override já estiver configurado.

Se o host não tiver Docker a iniciar no boot, agende no cron (ex. a cada 5 min):

```bash
*/5 * * * * /caminho/docmaster-core/scripts/ensure-pncp-researcher.sh >> /var/log/pncp-ensure.log 2>&1
```

Ou rode manualmente após reboot:

```bash
./scripts/ensure-pncp-researcher.sh
```
