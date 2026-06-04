# PNCP — alimentação do índice local 24/7 (guia completo)

Documentação de produção para o servidor **DESKTOP / docmaster** (`/home/docmaster`): manter o serviço PNCP no ar, alimentar o SQLite continuamente com **constância e rapidez**, e evitar operações que interrompem ou enfraquecem a ingestão.

Documentos relacionados:

- [README.md](./README.md) — índice de toda a documentação de deploy
- [PNCP-RESEARCHER-24-7.md](./PNCP-RESEARCHER-24-7.md) — stack isolada, volume, `ensure-pncp-researcher.sh`
- [PNCP-V2-DEPLOY.md](./PNCP-V2-DEPLOY.md) — FTS5, busca híbrida, endpoints V2
- [PNCP-SCRIPTS-REFERENCIA.md](./PNCP-SCRIPTS-REFERENCIA.md) — todos os scripts e compose PNCP
- [PNCP-API-INDICE-LOCAL.md](./PNCP-API-INDICE-LOCAL.md) — endpoints, FTS, busca inteligente
- [CHANGELOG-OPERACOES-2026-06.md](./CHANGELOG-OPERACOES-2026-06.md) — alterações da sessão DESKTOP
- [BOOT-AUTOMATICO.md](./BOOT-AUTOMATICO.md) — systemd e `--with-pncp-ingest`

---

## 1. Visão geral

### 1.1 Dois processos distintos

| Processo | Script / serviço | Função |
|----------|------------------|--------|
| **API 24/7** | `ensure-pncp-researcher.sh` → contentor `pncp_researcher_service` | Health, busca, backfill sob pedido HTTP |
| **Alimentação contínua** | `run-pncp-index-ingest-loop.sh` (nohup) | Loop por 27 UFs → POST backfill → grava no SQLite |

O `ensure` **não** substitui o loop. Sem o loop, `total_itens` quase não sobe.

### 1.2 Onde vivem os dados

- Ficheiro: `/data/pncp/pncp_researcher_local.db` **dentro** do contentor
- Persistência: volume Docker (não na imagem)
- Em produção (DESKTOP): volume **`docmaster-pncp_pncp_researcher_data`** via `~/docker-compose.pncp.override.yml`

### 1.3 Objetivo de produto

1. **Constância** — ingestão 24/7 sem parar por `docker compose up` no stack principal
2. **Rapidez** — muitos itens novos por hora (paralelo de GET de itens + mais páginas por UF)
3. **Cobertura de busca** — índice local profundo (watermark) + FTS5 + fallback híbrido ao PNCP ao vivo

O indicador de **cobertura** não é só `total_itens`/dia: é **`next_page`** a subir em `ingest-status` enquanto o watermark avança.

---

## 2. Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│  Host (WSL)                                                 │
│  nohup run-pncp-index-ingest-loop.sh                         │
│       │ docker exec → POST /local-index/backfill            │
│       ▼                                                     │
│  ┌──────────────────────────────┐                           │
│  │ pncp_researcher_service      │  restart: always          │
│  │  FastAPI :8012 (rede Docker) │                           │
│  │  SQLite ← volume external    │                           │
│  └──────────────┬───────────────┘                           │
│                 │ docmaster_net                             │
│  ┌──────────────▼───────────────┐                           │
│  │ backend (Django)             │                           │
│  │ PNCP_RESEARCHER_BASE_URL=    │                           │
│  │   http://pncp_researcher_    │                           │
│  │   service:8012               │                           │
│  └──────────────────────────────┘                           │
└─────────────────────────────────────────────────────────────┘
         │ HTTPS
         ▼
   pncp.gov.br (API consulta + API itens)
```

- **Projeto Compose:** `name: docmaster-pncp` (`docker-compose.pncp.yml`)
- **Sem porta no host (opcional):** `docker-compose.pncp.noports.yml` — health/backfill via `docker exec`
- **Stack principal** (`docmaster`): não deve recriar o PNCP

---

## 3. Funcionalidades do backfill (código)

### 3.1 Watermark (`PNCP_INGEST_WATERMARK_RESUME=1`)

Por **UF + modalidade** (6, 7, 8, 9, 10), estado em `pncp_ingest_state`:

| Campo | Significado |
|-------|-------------|
| `last_page` | Última página processada com sucesso |
| `next_page` (API) | `last_page + 1`, ou `1` se catálogo reiniciado |
| Fim de catálogo | Lote vazio ou &lt; 10 contratos → `last_page = 0` → próxima volta começa na página 1 (novos editais) |

Cada corrida do loop processa até **`PNCP_INGEST_MAX_PAGINAS`** páginas **a partir de** `next_page` (não repete só 1–25 para sempre).

### 3.2 Paralelo de itens (`PNCP_BACKFILL_ITEM_CONCURRENCY`)

Por página de contratos (~50), os GET de itens no PNCP correm em paralelo (default **12**, configurável até ~16). Upserts no SQLite são sequenciais após os fetchs.

Antes: 1 contrato de cada vez → dezenas de minutos por página.  
Depois: páginas em segundos a ~1 min conforme o PNCP responde.

### 3.3 Autopause

Em erro de rate limit / timeout / JSON inválido, a modalidade/UF pode ficar em `paused_blocked` com backoff. O loop segue para outras modalidades/UFs.

### 3.4 Busca (fora do loop, mas depende do índice)

- **FTS5** em `pncp_itens_fts` (`PNCP_FTS5_ENABLED=1`)
- **Híbrido:** se local &lt; 8 resultados, complementa com PNCP ao vivo (`PNCP_HYBRID_*`)

---

## 4. Variáveis de ambiente

### 4.1 Contentor (`docker-compose.pncp.yml`)

| Variável | Default | Função |
|----------|---------|--------|
| `PNCP_LOCAL_DB_PATH` | `/data/pncp/pncp_researcher_local.db` | Caminho do SQLite |
| `PNCP_LOCAL_BACKFILL_MONTHS` | `12` | Janela histórica (meses) |
| `PNCP_INGEST_WATERMARK_RESUME` | `1` | Retomar de `last_page+1` |
| `PNCP_BACKFILL_ITEM_CONCURRENCY` | `12` | Paralelismo de GET itens no backfill |
| `PNCP_BACKFILL_ITEM_TIMEOUT_SECONDS` | `45` | Timeout por contrato |
| `PNCP_INGEST_AUTOPAUSE_*` | ver compose | Pausas em bloqueio PNCP |
| `PNCP_FTS5_ENABLED` | `1` | FTS5 local |
| `PNCP_HYBRID_FALLBACK_ENABLED` | `1` | Fallback ao vivo |
| `PNCP_HYBRID_MIN_LOCAL_RESULTS` | `8` | Limiar híbrido |
| `PNCP_HYBRID_MAX_LIVE_PAGES` | `6` | Páginas live no híbrido |
| `PNCP_MAX_PAGINAS_PER_REQUEST` | `120` | Teto API por pedido de backfill |

### 4.2 Loop (`run-pncp-index-ingest-loop.sh`)

| Variável | Default (atual) | Função |
|----------|-----------------|--------|
| `DOCMASTER_DEPLOY_DIR` | `~/docmaster-core` ou `~` | Onde estão compose + noports |
| `PNCP_INGEST_MAX_PAGINAS` | `60` | Páginas por modalidade por UF/corrida |
| `PNCP_INGEST_MONTHS` | `12` | Meses no body do backfill |
| `PNCP_INGEST_TAMANHO_PAGINA` | `50` | Máximo PNCP |
| `PNCP_INGEST_SLEEP_UF_SEC` | `10` | Pausa entre UFs |
| `PNCP_INGEST_SLEEP_CYCLE_SEC` | `180` | Pausa após 27 UFs |
| `PNCP_INGEST_CURL_MAX_TIME_SEC` | `7200` | Timeout do POST backfill |
| `PNCP_INGEST_VIA_DOCKER` | auto | `1` se contentor existe (recomendado) |
| `PNCP_INGEST_JSON_LOG` | `~/pncp-ingest-responses.jsonl` | JSON grande fora do log legível |

**Importante:** `export PNCP_BACKFILL_ITEM_CONCURRENCY=16` **no shell do host** não altera o contentor. Para mudar, use compose + recreate ou `docker cp` + variável no compose.

---

## 5. Instalação e arranque (produção)

### 5.1 Pré-requisitos (uma vez)

```bash
# Na home do deploy (~ = /home/docmaster)
cd ~

# Volume com índice (ajuste o nome após find-pncp-db-volumes.sh)
./scripts/find-pncp-db-volumes.sh
PNCP_DATA_VOLUME=docmaster-pncp_pncp_researcher_data ./scripts/attach-pncp-volume.sh

# Confirma override
cat ~/docker-compose.pncp.override.yml
```

### 5.2 Subir API

```bash
cd ~
./scripts/ensure-pncp-researcher.sh
```

Com código novo:

```bash
cd ~/docmaster-core && git pull origin main
cp ~/docmaster-core/docker-compose.pncp.yml ~/docker-compose.pncp.yml
PNCP_BUILD=1 PNCP_FORCE_RECREATE=1 ./scripts/ensure-pncp-researcher.sh
```

### 5.3 Iniciar alimentação 24/7

**Opção A — manual (`nohup`):**

```bash
export DOCMASTER_DEPLOY_DIR=/home/docmaster

# Um único loop
pkill -f run-pncp-index-ingest-loop || true
rm -f /home/docmaster/.pncp-index-ingest.lock

nohup ~/docmaster-core/scripts/run-pncp-index-ingest-loop.sh >> ~/pncp-ingest.log 2>&1 &

sleep 3
tail -6 ~/pncp-ingest.log
```

**Opção B — idempotente (`ensure-pncp-ingest-loop.sh`):**

```bash
./scripts/ensure-pncp-ingest-loop.sh
# Usa ~/.pncp-index-ingest.pid; não inicia duplicado
```

**Opção C — boot systemd:**

```bash
sudo ./scripts/install-docmaster-boot-service.sh --with-pncp-ingest
# Unit: docmaster-pncp-ingest.service → run-pncp-index-ingest-loop.sh
```

Ou no stack ensure: `DOCMASTER_START_PNCP_INGEST=1 ./scripts/ensure-docmaster-stack.sh`

**Linhas esperadas:**

```text
PNCP ingest loop — via docker exec pncp_researcher_service (sem 8012 no host)
STATS início: contratos=... itens=...
INGEST START uf=AC max_paginas=60 (timeout 7200s — aguarde)
```

Sem `INGEST FAIL` imediato na linha seguinte.

### 5.4 WSL (Windows)

Em `C:\Users\<user>\.wslconfig`:

```ini
[wsl2]
vmIdleTimeout=-1
```

Depois: `wsl --shutdown` e reabrir o WSL. Evita o VM parar e matar o `nohup`.

### 5.5 Boot automático (opcional)

- Docker: `restart: always` no PNCP
- Stack: `scripts/install-docmaster-boot-service.sh` / `ensure-docmaster-stack.sh`
- **Loop:** após reboot, relançar o `nohup` (não sobe sozinho)

---

## 6. Monitorização

### 6.1 Checklist diário (~30 s)

```bash
pgrep -af run-pncp-index-ingest-loop || echo "LOOP PARADO"

docker ps --filter name=pncp_researcher --format '{{.Names}} {{.Status}}'

docker exec pncp_researcher_service python -c "
import urllib.request, json
h=json.load(urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/health', timeout=15))
s=json.load(urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/local-index/stats', timeout=30))
print('ok:', h.get('ok'), 'db_bytes:', h.get('db_bytes'), 'db_on_volume:', h.get('db_on_data_volume'))
print('contratos:', s.get('total_contratos'), 'itens:', s.get('total_itens'))
"

grep -E 'INGEST OK|INGEST FAIL|via docker exec|max_paginas=60' ~/pncp-ingest.log | tail -8
```

### 6.2 Cobertura (watermark)

```bash
docker exec pncp_researcher_service python -c "
import urllib.request, json
r=json.load(urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/local-index/ingest-status', timeout=30))
print('overall:', r.get('overall_status'), 'pausados:', r.get('scopes_paused'))
for s in r.get('scopes', [])[:12]:
  w=s['watermark']
  print(s['uf'], 'mod', s['modalidade'], 'last=', w.get('last_page'), 'next=', w.get('next_page'))
"
```

`next_page` a aumentar (26, 51, 76…) = crawl profundo activo.

### 6.3 Progresso do loop (log legível)

```bash
grep -E '^(20[0-9-]+T.* (INGEST|STATS|ERRO|PNCP ingest))' ~/pncp-ingest.log | tail -20
```

### 6.4 Backfill ao vivo (contentor)

```bash
docker logs -f pncp_researcher_service 2>&1 | grep -E 'backfill modalidade|backfill resume|429|paused'
```

### 6.5 Stats em tempo quase real (sem curl no host)

Com `noports`, **não** use `curl localhost:8012` como referência.

```bash
watch -n 30 'docker exec pncp_researcher_service python -c "
import urllib.request, json
s=json.load(urllib.request.urlopen(\"http://127.0.0.1:8012/api/pncp-research/local-index/stats\", timeout=30))
print(\"itens:\", s[\"total_itens\"], \"contratos:\", s[\"total_contratos\"])
"'
```

### 6.6 Comparar volume vs API

```bash
docker run --rm -v docmaster-pncp_pncp_researcher_data:/v:ro docmaster-pncp_researcher_service \
  python3 -c "
import sqlite3
c=sqlite3.connect('/v/pncp_researcher_local.db')
print('volume itens:', c.execute('select count(*) from pncp_itens').fetchone()[0])
"
```

Deve bater com `stats` no contentor (diferença pequena = timing).

---

## 7. Ritmo esperado

### 7.1 Por UF (config actual)

- **~10–35 min** por UF com `max_paginas=60` e itens (UFs grandes mais longas)
- **27 UFs** → **~8–20 h** por volta completa + `PNCP_INGEST_SLEEP_CYCLE_SEC` (180s)

### 7.2 Crescimento de `total_itens`

| Fase | Comportamento |
|------|----------------|
| Páginas já ingeridas | Muitos upserts, **pouco** aumento de COUNT |
| Páginas novas (watermark) | Saltos visíveis em `total_itens` |
| Referência observada em produção | **~300k itens / ~10 h** após paralelo + 60 páginas |

Não espere +500k itens **novos** todos os dias se o crawl estiver na mesma profundidade; espere **cobertura** (`next_page`) + picos quando houver páginas novas.

### 7.3 Tempos por página (após paralelo)

Logs típicos: `pagina=N` → `pagina=N+1` em **segundos a ~1 min** (antes: vários minutos).

---

## 8. O que NÃO fazer

| Proibido / evitar | Motivo |
|-------------------|--------|
| `docker compose -f docker-compose.pncp.yml down -v` | Apaga volume SQLite |
| Mudar `PNCP_DATA_VOLUME` / override sem comparar contagens | Monta DB errado (~600k vs ~1M) |
| Vários `nohup` do loop | Lock / backfills paralelos no mesmo DB |
| `pkill` loop sem relançar | Para alimentação |
| `rm` lock com loop a correr | Dois loops |
| Backfill manual pesado + loop ao mesmo tempo | Sobrecarga / SQLite lock |
| `curl localhost:8012` com noports | Falso negativo |
| `PNCP_FORCE_RECREATE` sem necessidade | Corta backfill em curso |
| Apagar `~/docker-compose.pncp.override.yml` | Perde volume external |
| `docker volume rm` em volumes `*pncp*` | Perda de dados |

---

## 9. O que é seguro fazer

| Comando | Efeito |
|---------|--------|
| `./scripts/ensure-pncp-researcher.sh` | Mantém contentor (`--no-recreate` por defeito) |
| `docker compose up -d --no-recreate backend` | Não mexe no projeto `docmaster-pncp` |
| Um `nohup` do loop com `DOCMASTER_DEPLOY_DIR=/home/docmaster` | Alimentação |
| `git pull` + `docker cp` + `docker restart pncp_researcher_service` | Hotfix sem rebuild |
| `PNCP_BUILD=1` + recreate quando mudar Dockerfile/deps | Deploy código |

---

## 10. Recuperação após falhas

### 10.1 Loop parado (reboot / WSL)

```bash
cd ~ && ./scripts/ensure-pncp-researcher.sh
export DOCMASTER_DEPLOY_DIR=/home/docmaster
rm -f /home/docmaster/.pncp-index-ingest.lock
nohup ~/docmaster-core/scripts/run-pncp-index-ingest-loop.sh >> ~/pncp-ingest.log 2>&1 &
```

### 10.2 `INGEST FAIL` exit 1 (HTTP 500)

Causa histórica corrigida: `sqlite3.Row` sem `.get()` em `_resolve_backfill_start_page`.  
Confirmar no contentor:

```bash
docker exec pncp_researcher_service grep -n 'state\["last_page"\]' \
  /app/pncp_researcher_service/app/local_index.py | head -2
```

Se faltar, `docker cp` de `local_index.py` + `docker restart`.

### 10.3 `INGEST FAIL` exit 137

**SIGKILL** — `pkill` ou restart durante backfill. Reiniciar loop; não é falha do PNCP.

### 10.4 Loop “travado” no terminal

O POST backfill **bloqueia** até terminar (até 7200s). Normal. Ver actividade:

```bash
docker logs pncp_researcher_service 2>&1 | grep 'backfill modalidade' | tail -5
```

### 10.5 `total_itens` parado, mas ingest OK

Verificar `next_page` em `ingest-status`. Se avança, está a alimentar cobertura.  
Se `scopes_paused` alto, aguardar autopause ou reduzir `PNCP_BACKFILL_ITEM_CONCURRENCY` para 12.

### 10.6 Dois volumes / contagens diferentes

Volumes comuns no DESKTOP:

| Volume | Notas |
|--------|--------|
| `docmaster-pncp_pncp_researcher_data` | Produção actual (override) |
| `docmaster_pncp_researcher_data` | Pode existir sem `.db` válido — não usar sem verificar |

```bash
for vol in docmaster-pncp_pncp_researcher_data docmaster_pncp_researcher_data; do
  echo "=== $vol ==="
  docker run --rm -v "${vol}":/v:ro docmaster-pncp_researcher_service \
    python3 -c "
import sqlite3
import os
p='/v/pncp_researcher_local.db'
if not os.path.isfile(p): p='/v/pncp/pncp_researcher_local.db'
c=sqlite3.connect(p)
print('itens:', c.execute('select count(*) from pncp_itens').fetchone()[0])
" 2>/dev/null || echo "sem db"
done
```

### 10.7 Atualizar código com alimentação a correr

```bash
cd ~/docmaster-core && git pull
docker cp ~/docmaster-core/pncp_researcher_service/app/local_index.py \
  pncp_researcher_service:/app/pncp_researcher_service/app/local_index.py
docker cp ~/docmaster-core/pncp_researcher_service/app/config.py \
  pncp_researcher_service:/app/pncp_researcher_service/app/config.py
docker restart pncp_researcher_service
# Relançar loop se foi morto pelo restart
```

---

## 11. Endpoints úteis

Base (dentro do contentor): `http://127.0.0.1:8012/api/pncp-research/`

| Método | Path | Uso |
|--------|------|-----|
| GET | `/health` | `db_bytes`, `db_on_data_volume` |
| GET | `/local-index/stats` | `total_contratos`, `total_itens` |
| GET | `/local-index/ingest-status` | Watermarks, pausas |
| GET | `/local-index/operational-status` | FTS, saúde operacional |
| POST | `/local-index/backfill` | Ingestão (body: `months`, `max_paginas`, `uf`, `include_items`) |
| POST | `/local-index/fts-rebuild` | Rebuild FTS após muitos itens novos |

Exemplo backfill manual (UF, 2 páginas, teste):

```bash
docker exec pncp_researcher_service python -c "
import json, urllib.request
body=json.dumps({'months':12,'max_paginas':2,'tamanho_pagina':50,'uf':'AC','include_items':True}).encode()
req=urllib.request.Request('http://127.0.0.1:8012/api/pncp-research/local-index/backfill', data=body, method='POST', headers={'Content-Type':'application/json'})
print(urllib.request.urlopen(req, timeout=600).read()[:400].decode())
"
```

---

## 12. Ficheiros e caminhos (DESKTOP)

| Caminho | Descrição |
|---------|-----------|
| `~/docmaster-core/` | Código fonte |
| `~/docker-compose.pncp.yml` | Compose PNCP (copiar do repo após pull) |
| `~/docker-compose.pncp.override.yml` | Volume external — **não apagar** |
| `~/docker-compose.pncp.noports.yml` | Sem 8012 no host |
| `~/scripts/ensure-pncp-researcher.sh` | Sobe API |
| `~/docmaster-core/scripts/run-pncp-index-ingest-loop.sh` | Loop ingestão |
| `~/pncp-ingest.log` | Log legível (INGEST/STATS) |
| `~/pncp-ingest-responses.jsonl` | Respostas JSON grandes do backfill |
| `~/.pncp-index-ingest.lock` | Lock do loop (flock) |

---

## 13. Histórico de problemas resolvidos (sessão DESKTOP)

| Problema | Solução |
|----------|---------|
| Loop usava `curl` no host com noports | `docker exec` automático se contentor existe |
| HTTP 500 no backfill | `state["last_page"]` em vez de `state.get()` |
| Só páginas 1–25 repetidas | Watermark `PNCP_INGEST_WATERMARK_RESUME` |
| Ingestão muito lenta | `PNCP_BACKFILL_ITEM_CONCURRENCY` + defaults 60 páginas / sleeps menores |
| JSON no log ilegível | `pncp-ingest-responses.jsonl` |
| Volume errado (~600k vs ~1.2M no log antigo) | Fixar `docmaster-pncp_pncp_researcher_data`; validar com `sqlite3` no volume |
| Vários nohup / lock | Um processo; `pkill` + `rm` lock só sem loop |

---

## 14. Regra de ouro

1. **Um volume** (`docmaster-pncp_pncp_researcher_data` no override)  
2. **Um loop** (`nohup` + `DOCMASTER_DEPLOY_DIR=/home/docmaster`)  
3. **`ensure`** para o contentor; **nunca** `down -v`  
4. Monitorizar **`itens`**, **`INGEST OK`**, e **`next_page`**  
5. Após reboot: `ensure` + relançar `nohup`

Com isso, o PNCP fica **a rodar e a alimentar** de forma estável e rápida; interrupções previstas: reboot/WSL, limites do portal PNCP (autopause), e fases de crawl onde `total_itens` sobe devagar mas a **cobertura** continua a crescer.
