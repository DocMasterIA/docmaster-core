# PNCP — referência de scripts e ficheiros Compose

Todos os scripts relacionados ao PNCP Researcher e à ingestão do índice. Deploy típico: `/home/docmaster` com código em `/home/docmaster/docmaster-core`.

Índice geral: [README.md](./README.md) · Ingestão 24/7: [PNCP-INGESTAO-INDEX-24-7.md](./PNCP-INGESTAO-INDEX-24-7.md)

---

## Ficheiros Compose

| Ficheiro | Localização típica | Função |
|----------|-------------------|--------|
| `docker-compose.pncp.yml` | `~/` (copiar do repo) | Stack isolada, `name: docmaster-pncp` |
| `docker-compose.pncp.override.yml` | `~/` | Volume `external` com índice existente |
| `docker-compose.pncp.noports.yml` | `~/` | Remove bind `127.0.0.1:8012` (WSL/Desktop) |

Variável de build: `PNCP_BUILD_CONTEXT=docmaster-core` quando o deploy é `~` e o repo está em `~/docmaster-core/`.

---

## `scripts/ensure-pncp-researcher.sh`

**Função:** Sobe ou mantém o contentor `pncp_researcher_service` sem apagar o volume.

| Comportamento | Detalhe |
|---------------|---------|
| Default | `docker compose up -d --no-recreate` |
| `PNCP_BUILD=1` | Adiciona `--build` |
| `PNCP_FORCE_RECREATE=1` | Adiciona `--force-recreate` |
| Health | `curl` em 8012 **ou** `docker exec` se `noports` |
| Volume | Avisa se override ausente ou volume inexistente |

```bash
cd ~
PNCP_BUILD=1 ./scripts/ensure-pncp-researcher.sh
```

**Nunca** `down -v`.

---

## `scripts/run-pncp-index-ingest-loop.sh`

**Função:** Loop infinito — 27 UFs, POST backfill, pausas configuráveis.

### Detecção `PNCP_INGEST_VIA_DOCKER`

1. Se contentor `pncp_researcher_service` existe → **`docker exec`** (recomendado)
2. Senão, se `docker-compose.pncp.noports.yml` em `DEPLOY` ou `HOME`
3. Senão, se health em `127.0.0.1:8012` falha

Log esperado:

```text
PNCP ingest loop — via docker exec pncp_researcher_service (sem 8012 no host)
```

### Lock

- Ficheiro: `~/.pncp-index-ingest.lock` (`flock`)
- Um processo por máquina

### Logs

| Destino | Conteúdo |
|---------|----------|
| `~/pncp-ingest.log` | Linhas `INGEST`, `STATS`, erros |
| `~/pncp-ingest-responses.jsonl` | JSON completo da resposta do backfill |

### Variáveis (loop)

Ver secção 4 em [PNCP-INGESTAO-INDEX-24-7.md](./PNCP-INGESTAO-INDEX-24-7.md).

### Uso

```bash
export DOCMASTER_DEPLOY_DIR=/home/docmaster
nohup ~/docmaster-core/scripts/run-pncp-index-ingest-loop.sh >> ~/pncp-ingest.log 2>&1 &

# Uma volta só (teste)
PNCP_INGEST_ONCE=1 ./scripts/run-pncp-index-ingest-loop.sh
```

---

## `scripts/ensure-pncp-ingest-loop.sh`

**Função:** Idempotente — inicia o loop **só se** não estiver a correr (cron, systemd, ou após boot).

| Mecanismo | Ficheiro |
|-----------|----------|
| PID file | `~/.pncp-index-ingest.pid` |
| Lock | `~/.pncp-index-ingest.lock` |
| Espera API | Até 30×4s por `curl` em 8012 (falha com noports — preferir loop já com docker exec após PNCP up) |

```bash
./scripts/ensure-pncp-ingest-loop.sh
```

Integrado em:

- `ensure-docmaster-stack.sh` se `DOCMASTER_START_PNCP_INGEST=1`
- `install-docmaster-boot-service.sh --with-pncp-ingest` → unit `docmaster-pncp-ingest.service`

---

## `scripts/attach-pncp-volume.sh`

**Função:** Gera `docker-compose.pncp.override.yml` apontando para volume Docker existente.

```bash
PNCP_DATA_VOLUME=docmaster-pncp_pncp_researcher_data ./scripts/attach-pncp-volume.sh
```

- Cria override com `external: true`
- Opcionalmente `docker-compose.pncp.noports.yml` se `PNCP_PUBLISH_HOST_PORT != 1`
- `docker compose up -d --force-recreate` do PNCP
- Mostra health + stats

**Correr uma vez** quando o volume já está certo; não repetir sem motivo.

---

## `scripts/find-pncp-db-volumes.sh`

**Função:** Lista volumes Docker que contêm `pncp_researcher_local.db`.

```bash
./scripts/find-pncp-db-volumes.sh
```

### Limitação no WSL

O script usa `docker run ... alpine` por volume. Se **nenhum** volume aparecer mas o PNCP tem dados, use inspecção manual:

```bash
for vol in $(docker volume ls -q | grep -i pncp); do
  echo "=== $vol ==="
  docker run --rm -v "${vol}":/v:ro docmaster-pncp_researcher_service \
    python3 -c "
import os, sqlite3
for p in ('/v/pncp_researcher_local.db', '/v/pncp/pncp_researcher_local.db'):
  if os.path.isfile(p):
    c=sqlite3.connect(p)
    print(p, 'itens', c.execute('select count(*) from pncp_itens').fetchone()[0])
"
done
```

---

## `scripts/lib/pncp-compose-args.sh`

Partilhado por `ensure-pncp-researcher.sh` e `attach-pncp-volume.sh`.

- Monta `COMPOSE_ARGS` (-f pncp, override, noports)
- `pncp_health_ok`, `pncp_print_health`, `pncp_print_stats_summary` com suporte `docker exec`

---

## `pncp_researcher_service/docker-entrypoint.sh`

Antes de arrancar a API:

- `mkdir -p` do diretório do DB
- `chown appuser:appuser` em `/data/pncp`

Evita `unable to open database file` quando o volume vem como root.

---

## Systemd (templates em `deploy/`)

| Unit | Template | Função |
|------|----------|--------|
| `docmaster-stack.service` | `deploy/docmaster-stack.service.example` | `ensure-docmaster-stack.sh` no boot |
| `docmaster-pncp-ingest.service` | `deploy/docmaster-pncp-ingest.service.example` | Loop de ingestão (`--with-pncp-ingest`) |

Instalação:

```bash
sudo ./scripts/install-docmaster-boot-service.sh --with-pncp-ingest
```

Ajustar paths no template via `install-docmaster-boot-service.sh` (User, WorkingDirectory, HOME).

---

## Rede e URLs

| De | Para | URL |
|----|------|-----|
| `backend` | PNCP | `http://pncp_researcher_service:8012` |
| Host (se porta mapeada) | PNCP | `http://127.0.0.1:8012` |
| Loop / health (noports) | PNCP | `docker exec … http://127.0.0.1:8012` |

Rede: `docmaster_net` (externa, criada pelo stack principal ou manualmente).
