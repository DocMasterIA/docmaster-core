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
# 1) Token do túnel (obrigatório — sem isto = erro 1033)
cp .env.example .env
nano .env   # CLOUDFLARE_TUNNEL_TOKEN=eyJ...  (Dashboard Cloudflare → Tunnels → token)

# 2) Verificar antes do systemd
chmod +x scripts/*.sh
./scripts/check-docmaster-boot-prereqs.sh

# 3) Stack completa no boot (recomendado)
sudo ./scripts/install-docmaster-boot-service.sh

# Com ingestão PNCP contínua (índice a crescer sozinho)
sudo ./scripts/install-docmaster-boot-service.sh --with-pncp-ingest
```

**Pré-requisitos:**

- `.env` na raiz do DEPLOY com `CLOUDFLARE_TUNNEL_TOKEN=...` (e demais vars do compose).
- Utilizador no grupo `docker` (ex.: `sudo usermod -aG docker docmaster` + relogar).
- O serviço corre como o dono da pasta do projeto (não como `root`). Se `sudo` acusar «root fora do grupo docker», atualize os scripts e volte a instalar.
- Volume PNCP configurado se aplicável (`attach-pncp-volume.sh`).

## Estado actual deste servidor (checklist)

| Item | Comando / acção |
|------|-----------------|
| `.env` com token | `grep CLOUDFLARE_TUNNEL_TOKEN .env` (não commitar) |
| Pré-requisitos | `./scripts/check-docmaster-boot-prereqs.sh` |
| systemd instalado | `systemctl is-enabled docmaster-stack` → `enabled` |
| Túnel no ar | `docker ps \| grep cloudflared` → `Up` |

Se só Grafana/Prometheus estiverem `Up` e não `backend`/`cloudflared`, o site fica **1033** até `./scripts/ensure-docmaster-stack.sh`.

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

## WSL / PC Windows (DESKTOP — o seu caso)

Se o `docmaster-stack.service` está **OK** no WSL mas o site só volta **depois de abrir o terminal**, o systemd Linux está certo — falta **acordar o WSL no login do Windows**.

| Camada | O que faz |
|--------|-----------|
| `docmaster-stack.service` (Linux) | Sobe Docker **quando o WSL já está ligado** |
| Tarefa Windows `DocMaster-WSL-Stack` | **Liga o WSL** após login / boot |
| `.wslconfig` `vmIdleTimeout=-1` | Evita a VM dormir com o PC ligado |

**Guia passo a passo:** [WSL-BOOT-WINDOWS.md](WSL-BOOT-WINDOWS.md)

```powershell
# PowerShell no Windows (ajuste a distro se não for Debian: wsl -l -v)
powershell -ExecutionPolicy Bypass -File \\wsl$\Debian\home\docmaster\scripts\windows-register-wsl-boot.ps1
```

Produção 24/7 ideal: **VPS Linux** (sem WSL) — só o systemd deste documento.
