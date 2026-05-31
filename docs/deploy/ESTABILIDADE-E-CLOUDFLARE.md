# Estabilidade do servidor e erro Cloudflare 1033

Com Prometheus/Grafana ok, estes passos reduzem quedas e o **1033** (“túnel não alcança a origem”).

## O que é o erro 1033

Não é bug do Django. A Cloudflare **não consegue falar com o `cloudflared`** na sua máquina (túnel parado, PC desligado, Docker parado, ou origem `backend`/`frontend-vue` down).

É diferente de **524/timeout** (pedido LLM longo; ver `deploy/nginx-gerar-tr-e-dfd-timeout.conf.example`).

## Checklist rápido quando aparecer 1033

```bash
cd DEPLOY   # pasta do docker-compose
docker ps | grep -E 'cloudflared|backend|frontend'
docker compose logs --tail 50 cloudflared-tunnel
```

| Verificação | Esperado |
|-------------|----------|
| `cloudflared-tunnel` | `Up` |
| `backend`, `frontend-vue` | `Up` |
| `.env` com `CLOUDFLARE_TUNNEL_TOKEN` | definido (sem warning no `compose up`) |
| Dashboard CF → Tunnels | status **Healthy** |

Recuperar:

```bash
./scripts/ensure-observability.sh   # se só métricas caíram
docker compose up -d backend frontend-vue cloudflared-tunnel
```

## WSL “dorme” com o Windows ligado (sintoma clássico do 1033)

Se o PC está ligado mas o site só volta quando você **abre um terminal WSL**, o problema quase sempre é:

- a VM do WSL2 entra em idle e **pausa** (Docker + `cloudflared` param dentro dela);
- o Windows continua “ligado”, mas a origem do túnel **não responde** até o WSL acordar.

Isso **não** é falha do Django nem do Prometheus.

### Ajuste no Windows (recomendado se continuar no WSL)

Crie ou edite **`C:\Users\SEU_USUARIO\.wslconfig`** (no Windows, não dentro do Linux):

```ini
[wsl2]
# -1 = não desligar a VM WSL por inatividade (evita 1033 até abrir terminal)
vmIdleTimeout=-1
```

Depois, no **PowerShell ou CMD**:

```text
wsl --shutdown
```

Abra o WSL de novo e suba a stack:

```bash
cd ~/docmaster-core
docker compose up -d backend frontend-vue cloudflared-tunnel
```

Outras dicas Windows:

- Docker Desktop → Settings → **Start when you sign in**
- Evitar “Modo de economia de energia” agressivo enquanto o PC é “servidor”
- Não usar `wsl --shutdown` no dia a dia se o túnel precisa ficar 24/7

### Solução definitiva para produção

Rodar **túnel + backend + frontend na VPS Linux** (sem WSL). O PC vira só ambiente de desenvolvimento; o 1033 por WSL idle deixa de existir para usuários do site.

## Onde o túnel deve rodar

- **VPS sempre ligada** → túnel + stack no servidor (recomendado para produção).
- **PC/WSL** → aceitável para testes; com WSL idle, 1033 é esperado até acordar a VM ou aplicar `vmIdleTimeout=-1`.

## Estabilidade (sem mexer no que já funciona)

### 1. Docker e reinício

- Linux: `sudo systemctl enable docker`
- WSL: Docker Desktop → iniciar com o Windows
- Serviços críticos com `restart: always` no compose (grafana, prometheus, node_exporter, cloudflared)
- Após reboot: `docker compose up -d` na pasta DEPLOY (ou systemd em `deploy/docmaster-observability.service.example` só para métricas; para site público inclua backend + tunnel no mesmo unit ou script)

### 2. Um único DEPLOY

Só **uma** pasta com `docker-compose.yml` + `config/`. Evita conflito de nome `prometheus`/`grafana` e túnel apontando para stack errada.

### 3. Token do túnel

```bash
# .env na pasta do compose (nunca commitar)
CLOUDFLARE_TUNNEL_TOKEN=eyJ...
```

Sem token, o contentor `cloudflared-tunnel` sobe vazio e o site cai.

### 4. Origem no painel Cloudflare

Ingress do túnel deve bater com os **nomes dos serviços Docker**:

- API → `http://backend:8000` (porta interna do contentor)
- Site → `http://frontend-vue:80`

Se apontar para `localhost` dentro do painel, falha dentro da rede Docker.

### 5. Pedidos longos (LLM) ≠ 1033

Plano gratuito Cloudflare ~**100 s** na borda. TR+DFD pode precisar de:

- timeouts altos no nginx (`deploy/nginx-gerar-tr-e-dfd-timeout.conf.example`)
- `RAG_HTTP_TIMEOUT_TR_DFD_MAX=900` no backend (já no compose)
- ou subdomínio **DNS only** (grey cloud) só para API pesada

### 6. Alertas (já tem Grafana)

Sugestão de regras simples (manual ou Contact point depois):

- `max(up{job="backend"}) == 0` → API scrape down
- `max(up{job="node"}) == 0` → host metrics down
- Disco &lt; 15% livre (`node_filesystem_avail_bytes`)

### 7. Backups

```bash
docker run --rm -v DEPLOY_backend_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/backend-data-$(date +%F).tar.gz -C /data .
```

### 8. Versões fixas (opcional)

Trocar `cloudflared:latest` / `grafana:latest` por tag fixa após um deploy estável evita surpresa em `docker compose pull`.

## Boot automático após reinício (recomendado)

```bash
cd ~/docmaster-core
sudo ./scripts/install-docmaster-boot-service.sh
```

Isso instala `docmaster-stack.service` (systemd), que sobe app + túnel Cloudflare + PNCP + observabilidade no boot. Ver [BOOT-AUTOMATICO.md](BOOT-AUTOMATICO.md).

Subida manual (sem reboot):

```bash
./scripts/ensure-docmaster-stack.sh
```

## PNCP Researcher (alimentação 24h)

Se o `pncp_researcher_service` cai a cada `docker compose up -d`, use a stack isolada: [PNCP-RESEARCHER-24-7.md](PNCP-RESEARCHER-24-7.md) e `./scripts/ensure-pncp-researcher.sh`.

## Ordem de prioridade

1. Túnel + stack na **VPS**, não no PC que desliga  
2. `CLOUDFLARE_TUNNEL_TOKEN` + `restart: always` no cloudflared  
3. `docker compose up -d` após cada reboot  
4. Logs do túnel quando 1033 voltar  
5. Timeouts/nginx só se o problema for **lentidão/502**, não 1033  
