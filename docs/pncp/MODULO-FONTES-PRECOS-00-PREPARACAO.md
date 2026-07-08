# Módulo Fontes de Preços — preparação para esquematização

Documento de **síntese** (jul/2026) para iniciar o desenho do módulo que conecta **APIs além do PNCP** (TCE, Painel de Preços, BNC, BLL, etc.).

**Plano original:** [PLANO-FONTES-PRECOS-MULTIPLAS-PLATAFORMAS.md](./PLANO-FONTES-PRECOS-MULTIPLAS-PLATAFORMAS.md) (22/jun/2026).

**Pré-requisito cumprido:** PNCP estável em produção — ver [PNCP-PERFIL-OPERACIONAL-JUL2026.md](./PNCP-PERFIL-OPERACIONAL-JUL2026.md) (`c3c1aa86+`). A ordem recomendada no plano original («não iniciar multi-fonte antes da paridade PNCP») **já pode avançar para Fase 0 / Fase 1**.

---

## 1. Problema de produto

| Dor | Hoje | Com multi-fonte |
|-----|------|-----------------|
| Item sem match no índice PNCP | 0–1 preços, autostart vazio | Fallback TCE / agregador |
| Compra só no portal estadual | PNCP tardio ou ausente | Inciso II preenchido |
| Cliente com licença BNC/BLL | Busca manual fora do DocMaster | Busca unificada |
| Relatório Art. 5º exige diversidade | Só Inciso I automatizado | Incisos I–III via conectores |

**Meta legal:** Lei 14.133/2021, Art. 5º — cinco incisos de fontes de preço; relatório PDF já tem colunas para todos.

---

## 2. O que já existe no DocMaster (reaproveitar)

### 2.1 UI — Art. 5º pronto na planilha

`frontend-vue/src/views/CotacaoDetalhe.vue` — cinco colunas de contagem por item:

| Coluna UI | Bucket backend | Inciso |
|-----------|----------------|--------|
| Preços governamentais | `governamentais` | I |
| Outros entes públicos | `entesPublicos` | II |
| Domínio amplo | `dominioAmplo` | III |
| Cotação direta | `cotacaoDireta` | IV |
| Notas fiscais | `notasFiscais` | V |

Status do item: **Completo** (≥ 3 fontes) / **Incompleto** — `PESQUISADOR_PNCP_FUNCIONAMENTO_ATUAL.md`.

### 2.2 Django — persistência e classificação

| Peça | Arquivo | Papel |
|------|---------|-------|
| Modelos | `backend/app/models/pncp_cotacao.py` | `PncpCotacao`, `PncpCotacaoItem`, `PncpCotacaoItemCotacao` |
| JSON `source` | campos em Item + ItemCotacao | Snapshot auditável por preço salvo |
| Buckets inciso | `pncp_cotacao_api._fonte_bucket_from_source` | Resolve I/II por inciso, esfera ou texto |
| Contagem fontes | `_count_fontes_por_item` | Alimenta UI e relatório |
| Relatório PDF | `pncp_relatorio_pdf.py`, `pncp_relatorio_itens.py` | Consolidação Art. 5º |
| Filtros sessão | `PncpCotacao.filtros` JSON | Hoje: fórmula, variação global — **cabe** `fontes_habilitadas` |

Campos PNCP-centric (`numero_pncp`, `ano_compra`, …) podem ficar **vazios** quando `source.plataforma != pncp` (plano original, §7).

### 2.3 Researcher PNCP — motor de busca (vira adapter #1)

| Peça | Arquivo | Reuso multi-fonte |
|------|---------|-------------------|
| Busca inteligente | `service.market_search_intelligent` | Wrapper `PncpAdapter.search()` |
| Scoring | literal, spec, faixa, federal-first | **Genérico** pós-normalização |
| Spec match | `product_spec_match.py` | Mesmo para qualquer `descricao_item` |
| Faixa regional | `pricing_faixa.py`, `pricing_display.py` | Mesmo contrato de preço |
| Índice local | `local_index.py` SQLite FTS | Específico PNCP — **não** generalizar DB |
| Proxy Django | rotas `/api/pncp-research/...` | Padrão para novo `/api/price-research/...` |

### 2.4 O que **não** existe (zero código)

- Interface `PriceSourceAdapter` / `MarketPriceHit`
- Endpoint `POST /market-search/federated`
- Campo `source.plataforma` preenchido sistematicamente (implicitamente `pncp` hoje)
- Conectores TCE, BNC, BLL, Painel de Preços
- UI checkbox «fontes» na Busca Inteligente
- Autostart multi-fonte
- Credenciais por tenant (API keys BNC/BLL)

---

## 3. Mapa de plataformas (discovery pendente)

Do plano original — **validar com cliente** antes de implementar:

| ID sugerido | Plataforma | Inciso provável | Prioridade | API / acesso |
|-------------|------------|-----------------|------------|--------------|
| `pncp` | PNCP federal | I | ✅ produção | REST pública |
| `painel_precos` | Compras.gov / Painel | I | Alta | API limitada; overlap PNCP |
| `tce_*` | TCE por UF (PR, SC, RS…) | II | Alta | **Variável** — 1 conector por UF |
| `bnc` | BNC (agregador) | I ou II | Média | Licença + API parceiro |
| `bll` | BLL (SaaS) | I–III | Média | SSO / export / API |
| `bec_sp` | BEC-SP, portais estaduais | II | Baixa/média | Pontual |
| — | Cotação direta / NF | IV–V | Fora escopo v1 | Upload manual (já parcial) |

**Regra:** TCE/BNC/BLL são **famílias de conectores**, não um plug único.

---

## 4. Arquitetura alvo (rascunho para esquematizar)

### 4.1 Diagrama

```text
┌──────────────────────────────────────────────────────────────────┐
│ Vue — CotacaoDetalhe / BuscaInteligente / BuscaManual            │
│   fontes_habilitadas[] + faixa + UF + termo                      │
└────────────────────────────┬─────────────────────────────────────┘
                             │ POST /api/pncp/cotacoes/.../search
                             │ (ou novo /api/price-research/federated)
┌────────────────────────────▼─────────────────────────────────────┐
│ Django — fonte de verdade, save, PDF, multi-tenant               │
│   PncpCotacaoItemCotacao.source { plataforma, inciso, raw, … } │
└────────────────────────────┬─────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
   PncpAdapter         TcePrAdapter         BllAdapter
   (refactor)          (novo)               (novo)
         │                   │                   │
         ▼                   ▼                   ▼
   SQLite PNCP          API/cache UF         API parceiro
```

### 4.2 Contrato canônico `MarketPriceHit`

Normalizar **toda** plataforma antes de scoring/save:

```python
@dataclass
class MarketPriceHit:
    plataforma: str                    # pncp | tce_pr | bll | …
    plataforma_item_id: str
    descricao_item: str
    valor_unitario: float
    valor_unitario_homologado: float | None
    unidade_medida: str | None
    quantidade: float | None
    orgao: str | None
    municipio: str | None
    uf: str | None
    fornecedor_nome: str | None
    fornecedor_cnpj: str | None
    data_referencia: str | None
    inciso_classificacao: str | None   # inciso_i … inciso_v
    esfera: str | None                 # federal | estadual | municipal
    url_origem: str | None
    raw: dict | None                   # truncado
```

Adapter interface:

```python
class PriceSourceAdapter(Protocol):
    id: str
    def capabilities(self) -> dict: ...
    async def health(self) -> bool: ...
    async def search(self, query: FederatedSearchQuery) -> list[MarketPriceHit]: ...
```

`FederatedSearchQuery` reutiliza campos já usados no PNCP: `termo_busca`, `uf`, `valor_base`, `variacao_pct`, `sentido`, `somente_homologados`, timeout.

### 4.3 Orquestração federada

1. Resolver `fontes_habilitadas` da sessão + tenant (credenciais).
2. `asyncio.gather` com timeout **por adapter** (15–25 s).
3. Normalizar → `MarketPriceHit[]`.
4. **Dedup** cross-platform: hash `(orgao_norm, data, valor±ε, desc_norm, cnpj)`.
5. Scoring unificado (mover lógica comum para módulo `price_scoring` ou pacote dentro do researcher).
6. Top-N + regra diversidade de inciso (produto a definir).
7. Save Django com `source.plataforma` explícito.

### 4.4 Onde hospedar código (decisão aberta)

| Opção | Quando |
|-------|--------|
| **A.** Pacote `adapters/` dentro de `pncp_researcher_service` | Fase 1 — 1º adapter extra |
| **B.** Microserviço `market_price_service` | ≥2 fontes com índice próprio |
| **C.** Só Django | Spike único; **não** para autostart 696 itens |

**Recomendação mantida:** A → B gradual.

---

## 5. Fases (atualizado jul/2026)

| Fase | Escopo | Status |
|------|--------|--------|
| **0** Discovery | Matriz fonte × API × inciso × legal | ⬜ Próximo |
| **1** Contrato | `PriceSourceAdapter`, PNCP refactor, `plataforma=pncp`, flag federated | ⬜ |
| **2** Piloto público | Painel de Preços **ou** 1 TCE | ⬜ |
| **3** Comercial | BNC/BLL + credencial tenant | ⬜ |
| **4** Autostart multi-fonte | PNCP first + fallback; budget tempo | ⬜ |

PNCP paridade: ~~bloqueador~~ **concluído** (`c3c1aa86+`).

---

## 6. Decisões de produto (responder antes de codar)

1. **Meta de preços:** 3 totais por item ou 3 **por inciso**?
2. **UF/TCE** obrigatórios no v1?
3. Cliente já tem **BNC/BLL**? Documentação de API?
4. **Somente homologados** também em TCE/BNC?
5. Consulta **ao vivo** vs **índice local** por fonte?
6. Inciso no PDF para preço de agregador comercial (III vs I)?
7. Dedup: mesma compra PNCP + Painel — qual prevalece?

---

## 7. Riscos (do plano original, ainda válidos)

| Risco | Mitigação |
|-------|-----------|
| TCE sem API estável | Ingest noturno + cache TTL |
| ToS proíbe scraping | Só API oficial / export licenciado |
| Custo por consulta BLL/BNC | Flag tenant + limite diário |
| Autostart × N fontes | Paralelo com cap; PNCP first |
| Relatório jurídico | `url_origem` + snapshot em `source` |

---

## 8. Impacto em dados (rascunho)

### `PncpCotacao.filtros` (evolução)

```json
{
  "variacao_percentual_global": 50,
  "variacao_sentido_global": "cima",
  "fontes_habilitadas": ["pncp", "tce_pr"],
  "autostart_fallback": ["tce_pr"],
  "bll_credencial_ref": "vault:prefeitura:42"
}
```

### `PncpCotacaoItemCotacao.source` (evolução)

```json
{
  "plataforma": "tce_pr",
  "plataforma_item_id": "…",
  "inciso_classificacao": "inciso_ii",
  "url_origem": "https://…",
  "snapshot_at": "2026-07-06T…",
  "valor_unitario_homologado": 19.5
}
```

Renomear modelos (`CotacaoPrecoItem`) — **só** quando ≥2 fontes em produção.

---

## 9. Critérios de aceite v1

- [ ] Item com 0 no PNCP recebe ≥1 de fonte alternativa configurada
- [ ] PDF mostra plataforma/inciso corretos
- [ ] Save exige identificador auditável (CNPJ ou ID plataforma)
- [ ] Busca manual e autostart usam mesmas `fontes_habilitadas`
- [ ] Desligar fonte não quebra cotações antigas (snapshot)
- [ ] Faixa regional `cima`/`baixo` respeitada em hits de qualquer adapter

---

## 10. Próximos passos imediatos (esquematização)

1. **Workshop discovery** — preencher matriz §3 com links/APIs reais (Fase 0).
2. **ADR** — escolher A vs B (§4.4) + local do pacote `adapters/`.
3. **Esquema OpenAPI** — `FederatedSearchRequest` / `FederatedSearchResponse`.
4. **Spike** — `scripts/spike_price_source_search.py` (stdout JSON, 1 TCE manual).
5. **Diagrama de sequência** — busca federada vs save vs PDF.
6. **Epic backlog** — issues Fase 1 fatiadas (interface, refactor PNCP, flag, campo plataforma).

---

## 11. Referências cruzadas

| Documento | Conteúdo |
|-----------|----------|
| [PLANO-FONTES-PRECOS-MULTIPLAS-PLATAFORMAS.md](./PLANO-FONTES-PRECOS-MULTIPLAS-PLATAFORMAS.md) | Plano original completo |
| [PNCP-PERFIL-OPERACIONAL-JUL2026.md](./PNCP-PERFIL-OPERACIONAL-JUL2026.md) | PNCP estável — pré-requisito OK |
| [PNCP-FORNECEDOR-RELATORIO-REGRAS.md](./PNCP-FORNECEDOR-RELATORIO-REGRAS.md) | Homologado, CNPJ, PDF |
| [PESQUISADOR_PNCP_FUNCIONAMENTO_ATUAL.md](./PESQUISADOR_PNCP_FUNCIONAMENTO_ATUAL.md) | Fluxo atual mono-PNCP |
| [planejamento/06-BUSCA-E-FORNECEDOR.md](./planejamento/06-BUSCA-E-FORNECEDOR.md) | Pipeline busca PNCP |
| [PNCP-NOTAS-PENDENCIAS.md](./PNCP-NOTAS-PENDENCIAS.md) | Nota 22/jun multi-plataforma |
| [SISTEMA-DOCMASTER-VISAO-COMPLETA.md](../SISTEMA-DOCMASTER-VISAO-COMPLETA.md) §9 | Visão módulo PNCP |

---

*Última atualização: 2026-07-06 — preparação pós-estabilização PNCP; nenhum conector extra implementado.*
