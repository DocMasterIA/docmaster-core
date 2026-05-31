# Boot automático após reinício do servidor

## Problema

Com `restart: always` no Docker, os contentores **voltam sozinhos** depois de um reboot **somente se**:

1. o Docker inicia com o sistema (`systemctl enable docker`);
2. os contentores **não** foram parados com `docker compose down` antes do desligamento;
3. variáveis como `CLOUDFLARE_TUNNEL_TOKEN` continuam disponíveis (`.env`);
4. a rede `docmaster_net` e a stack PNCP isolada também sobem.

Na prática, após desligar o PC/servidor, o site ficava offline (erro **1033** no Cloudflare) até alguém rodar `docker compose up -d` manualmente.

## Solução

Script único + serviço **systemd** no boot:

| Artefato | Função |
|----------|--------|
| `scripts/ensure-docmaster-stack.sh` | Sobe app, túnel, PNCP, Grafana/Prometheus |
| `scripts/install-docmaster-boot-service.sh` | Instala e ativa o unit systemd |
| `deploy/docmaster-stack.service.example` | Template do serviço |
| `deploy/docmaster-pncp-ingest.service.example` | Opcional: loop de ingestão PNCP 24/7 |

## Instalação (uma vez)

Na pasta do projeto (ex.: `~/docmaster-core`):

```bash
chmod +x scripts/ensure-docmaster-stack.sh scripts/install-docmaster-boot-service.sh

# Stack completa no boot (recomendado)
sudo ./scripts/install-docmaster-boot-service.sh

# Com ingestão PNCP contínua (índice a crescer sozinho)
sudo ./scripts/install-docmaster-boot-service.sh --with-pncp-ingest
```

**Pré-requisitos:**

- `.env` na raiz do DEPLOY com `CLOUDFLARE_TUNNEL_TOKEN=...` (e demais vars do compose).
- Utilizador no grupo `docker` (ex.: `sudo usermod -aG docker adryan` + relogar).
- Volume PNCP configurado se aplicável (`attach-pncp-volume.sh`).

## Verificação

```bash
systemctl status docmaster-stack.service
journalctl -u docmaster-stack.service -n 80 --no-pager

docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'backend|frontend|cloudflared|pncp|grafana'

curl -sf http://127.0.0.1:8001/metrics >/dev/null && echo "backend OK"
curl -sf http://127.0.0.1:8012/api/pncp-research/health | python3 -m json.tool
```

Simular reboot (sem reiniciar o host):

```bash
sudo systemctl restart docmaster-stack.service
```

## Comandos úteis

```bash
# Subir manualmente (sem reboot)
./scripts/ensure-docmaster-stack.sh

# Rebuild de imagens no boot script
DOCMASTER_BUILD=1 ./scripts/ensure-docmaster-stack.sh

# Só stack principal + PNCP API (ingestão manual/nohup)
./scripts/ensure-docmaster-stack.sh

# Ingestão em background (sem systemd dedicado)
./scripts/ensure-pncp-ingest-loop.sh
```

## O que sobe em cada camada

1. **systemd** `docmaster-stack.service` — no boot do Linux, após `docker.service`.
2. **ensure-docmaster-stack.sh** — `docker compose up -d` (backend, frontend, cloudflared, LLM, RAG, observabilidade).
3. **ensure-pncp-researcher.sh** — stack isolada `docker-compose.pncp.yml`.
4. **docmaster-pncp-ingest.service** (opcional) — loop `run-pncp-index-ingest-loop.sh`.

## WSL / PC de desenvolvimento

No WSL, além disto, configure Docker Desktop para iniciar com o Windows e, se usar túnel local, `vmIdleTimeout=-1` em `.wslconfig` — ver [ESTABILIDADE-E-CLOUDFLARE.md](ESTABILIDADE-E-CLOUDFLARE.md).

Produção 24/7 ideal: **VPS Linux** com este systemd ativo.
