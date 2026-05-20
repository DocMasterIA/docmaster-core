# PNCP Researcher — rodar 24h sem cair no `up -d`

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

`restart: always` no ficheiro PNCP — após reboot do Docker, suba de novo só o PNCP:

```bash
./scripts/ensure-pncp-researcher.sh
```
