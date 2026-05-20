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
curl -s http://127.0.0.1:8012/health
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

## Reinício automático

`restart: always` no ficheiro PNCP — após reboot do Docker, suba de novo só o PNCP:

```bash
./scripts/ensure-pncp-researcher.sh
```
