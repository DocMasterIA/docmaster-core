# Arquitetura — feeds independentes → pesquisador de preços

Objetivo: **nenhuma plataforma depende do PNCP para existir ou ser alimentada.**  
Cada fonte tem (ou compartilha o padrão de) um **feed de escrita**; o **researcher** só lê índices e orquestra (Camada B).

---

## 1. Diagrama

```text
┌─────────────────────────┐     /data/pncp/*.db
│ price_index_feed_pncp   │────►  PNCP legacy index
│ SERVICE_MODE=feed       │
│ FEED_PLATFORM=pncp      │
│ :8013                   │
└─────────────────────────┘
                                      ┐
┌─────────────────────────┐           │  volumes compartilhados
│ price_index_feed_tce_rs │────►      │  (somente arquivos .db)
│ SERVICE_MODE=feed       │ /data/platforms/tce_rs_local.db
│ FEED_PLATFORM=tce_rs    │           │
│ :8014                   │           │
└─────────────────────────┘           │
                                      │
┌─────────────────────────┐           │  /data/crosslink/*.db
│ price_index_feed_<id>   │────►      │  (escrito sob demanda
│ (futuro)                │           │   pelo researcher no merge)
└─────────────────────────┘           ┘
                 escritura
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│           price_researcher_service :8012          │
│  SERVICE_MODE=researcher                         │
│  • adapters (pncp, tce_rs, …)  — só leitura      │
│  • federated merge + Camada B (faixa/score/top3) │
│  • Django proxy inalterado                       │
└─────────────────────────────────────────────────┘
                      │
                      ▼
              Vue / Django (Camada C)
```

**Regra:** feed N **não importa** código de ingest do feed M.  
O researcher **não** sobe worker PNCP nem roda ingest TCE.

---

## 2. Fronteiras

| Camada | Responsabilidade | Não faz |
|--------|------------------|---------|
| **Feed PNCP** | API PNCP → SQLite legacy, FTS, worker 24/7 | Conhecer LicitaCon / scoring / UI |
| **Feed TCE-RS** | CSV/CKAN → `platform_index` TCE | Chamar PNCP; federar busca |
| **Feed \<plataforma\>** | Mesmo contrato: popular `.db` próprio | Acoplar a outro feed |
| **Researcher** | Ler DBs + adapters + orquestração | Ingest / cron de plataforma |
| **Produto** | Fontes, save, PDF | Schema SQLite de feed |

Contrato entre feed e researcher: **arquivo SQLite + schema conhecido**  
(`legacy_pncp` ou `platform_index`), nunca HTTP entre feeds.

---

## 3. Variáveis de processo

| Env | Valores | Efeito |
|-----|---------|--------|
| `SERVICE_MODE` | `feed` \| `researcher` \| `all` | Papel do processo |
| `FEED_PLATFORM` | `pncp` \| `tce_rs` \| *(vazio=legado)* | Qual pipeline de escrita sobe |
| `PNCP_INGEST_WORKER_ENABLED` | 0/1 | Só respeitado se `FEED_PLATFORM=pncp` (ou feed monolito) |

Compose alvo:

| Container | Porta | Envs |
|-----------|-------|------|
| `price_index_feed_pncp` | 8013 | `feed` + `pncp` |
| `price_index_feed_tce_rs` | 8014 | `feed` + `tce_rs` |
| `pncp_researcher_service` (researcher) | 8012 | `researcher` |

`price_index_feed_service` (sem `FEED_PLATFORM`) permanece como **legado monolito** só se alguém precisar; produção usa feeds separados.

---

## 4. Rotas HTTP (isolamento)

| Prefixo | Quem sobe |
|---------|-----------|
| `/api/pncp-feed/local-index/*` | só feed PNCP (ou monolito) |
| `/api/pncp-feed/price-platform-indexes/tce_rs/*` | só feed TCE-RS (ou monolito) |
| `/api/pncp-feed/health` | qualquer feed (payload indica `feed_platform`) |
| `/api/pncp-research/*` | só researcher |

Adicionar plataforma nova:

1. Pacote `platform_index/ingest/<id>/`  
2. Spec no `registry`  
3. Rotas no feed filtradas por `FEED_PLATFORM=<id>`  
4. Serviço compose `price_index_feed_<id>`  
5. Adapter de **leitura** no researcher  

**Sem** alterar o feed PNCP.

---

## 5. Volumes

| Volume | Escrita | Leitura |
|--------|---------|---------|
| `pncp_researcher_data` → `/data/pncp` | feed PNCP | researcher |
| `price_platform_data` → `/data/platforms` | feeds batch (cada um o seu `.db`) | researcher |
| `price_crosslink_data` → `/data/crosslink` | researcher (merge) | researcher |

Feeds **não** montam banco um do outro como dependência de código — só compartilham o volume de platforms se conveniente; paths são distintos (`tce_rs_local.db`, futuro `xyz_local.db`).

---

## 6. Evolução de pastas (código)

Hoje (mesma imagem, modos diferentes) — ok.

```text
pncp_researcher_service/
  app/
    api_feed.py / api_researcher.py
    platform_index/ingest/tce_rs/   # domínio TCE isolado
    adapters/                      # só researcher
    service.py                     # Camada B
  data/tce_rs/raw/                 # dados LicitaCon (gitignored)
```

Depois (opcional, Phase 2 repo split):

```text
price_common/          # schema platform_index, MarketPriceHit
price_feed_pncp/
price_feed_tce_rs/
price_researcher/
```

Imagem única + `FEED_PLATFORM` já entrega a separação operacional **sem** multi-repo.

---

## 7. Checklist «plataforma nova»

- [ ] SQLite próprio sob `/data/platforms/<id>_local.db`  
- [ ] Ingest só no container `FEED_PLATFORM=<id>`  
- [ ] Adapter de busca no researcher (sem lógica de download)  
- [ ] Não chama endpoints do feed PNCP  
- [ ] `fontes_habilitadas` inclui o id  
- [ ] Camada B única (já compartilhada)  

---

*Arquitetura de feeds — jul/2026.*
