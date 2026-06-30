# Plano — Fontes de preços além do PNCP (TCE, BNC, BLL, etc.)

Documento de **planejamento** (jun/2026). Não é especificação de implementação.

**Objetivo:** ampliar o Pesquisador de Preços para encontrar itens de cotação em **outras plataformas** de referência de preços públicos e agregadores comerciais, mantendo conformidade com a **Lei 14.133/2021 (Art. 5º)** e reutilizando o que já existe no módulo PNCP.

Relacionado:

- [`PNCP-PLANEJAMENTO/06-BUSCA-E-FORNECEDOR.md`](PNCP-PLANEJAMENTO/06-BUSCA-E-FORNECEDOR.md) — fluxo atual (só PNCP)
- [`PNCP-PLANO-PARIDADE-BUSCA.md`](PNCP-PLANO-PARIDADE-BUSCA.md) — estabilizar PNCP antes/durante expansão
- UI Art. 5º: `frontend-vue/src/views/CotacaoDetalhe.vue` (5 colunas de fonte)

---

## 1. Por que expandir

| Situação | Efeito |
|----------|--------|
| Item recente ainda não indexado no PNCP local | 0–1 preços na cotação |
| Órgão estadual/municipal publicou só no painel do **TCE** ou portal estadual | PNCP não cobre ou cobre tarde |
| Cliente já possui licença **BNC / BLL** | Expectativa de busca unificada no DocMaster |
| Relatório exige **≥ 3 fontes** (Incisos I–V) | PNCP sozinho pode não bastar por item |

Hoje o DocMaster concentra busca + índice em **`pncp_researcher_service`**. As colunas do relatório já preveem **cinco incisos**; a busca automatizada, porém, alimenta essencialmente **Inciso I (Preços Governamentais)** via PNCP.

---

## 2. Mapa de plataformas candidatas

Lista inicial para **discovery** com o cliente — validar siglas, contratos e APIs reais.

| Plataforma | Tipo | Art. 5º provável | Acesso típico | Prioridade sugerida |
|------------|------|------------------|---------------|---------------------|
| **PNCP** | Federal, oficial | Inciso I | API REST pública (`pncp.gov.br`) | ✅ já integrado |
| **Painel de Preços** (Compras.gov / Gov.br) | Federal, histórico SIASG | Inciso I | API/scraping limitado; sobreposição PNCP | Alta — complemento federal |
| **TCE** (estadual) | Painéis/bancos por UF (PR, SC, RS, MG…) | Inciso II (outros entes) | Variável por estado; muitas sem API estável | Alta — gap regional |
| **BNC** | Agregador comercial / banco nacional | I ou II conforme origem | API parceiro ou export (validar produto exato) | Média — depende de licença |
| **BLL** | SaaS de pesquisa de preços | I–III conforme fonte | API parceiro, SSO ou export CSV | Média — depende de licença |
| **BEC-SP**, portais estaduais (Licitações-e, etc.) | Estadual | Inciso II | APIs pontuais ou scraping | Média/baixa por UF |
| **Cotação direta / NF** (Incisos IV–V) | Fornecedor + nota fiscal | IV / V | Upload manual + OCR (futuro) | Fora do escopo deste plano |

**Nota:** TCE, BNC e BLL não são um único endpoint — cada UF/produto tem regras, campos e restrições diferentes. Tratar como **famílias de conectores**, não um “plug único”.

---

## 3. Princípios de arquitetura

### 3.1 Modelo mental: agregador com adaptadores

```
┌─────────────────────────────────────────────────────────────────┐
│ Frontend — Busca Inteligente / Manual / Autostart               │
│   termo + faixa + UF + fontes[]  (ex.: pncp, tce_pr, bll)       │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│ Django — proxy + persistência cotação (fonte de verdade)        │
│   PncpCotacaoItem.source { plataforma, inciso, ids, snapshot }  │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ PNCP adapter  │   │ TCE adapter   │   │ BLL/BNC       │
│ (existente)   │   │ (por UF)      │   │ adapter       │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        ▼                   ▼                   ▼
   índice local         índice/API           API parceiro
   SQLite PNCP          por conector         + cache
```

### 3.2 Contrato canônico (`MarketPriceHit`)

Normalizar toda plataforma para um JSON compatível com o que o Django já grava em `PncpCotacaoItem.source` + campos de exibição:

| Campo | Uso |
|-------|-----|
| `plataforma` | `pncp`, `tce_pr`, `painel_precos`, `bnc`, `bll`, … |
| `plataforma_item_id` | ID estável na origem |
| `descricao_item` | Texto para match/scoring |
| `valor_unitario` / `valor_unitario_homologado` | Preço canônico |
| `unidade_medida`, `quantidade` | Spec match |
| `orgao`, `municipio`, `uf` | Filtro geo + relatório |
| `fornecedor_nome`, `fornecedor_cnpj` | Save + PDF |
| `data_referencia` | Recência |
| `inciso_classificacao` | `inciso_i` … `inciso_v` |
| `esfera` | `federal` / `estadual` / `municipal` |
| `url_origem` | Link auditável no relatório |
| `raw` | Payload bruto (opcional, truncado) |

Reutilizar:

- `product_spec_match.py` — equivalência de produto (ml, %, embalagem)
- `pricing_display.py` — prioridade homologado → unitário → estimado
- Regras de inciso já em `pncp_cotacao_api.py` (`inciso_resolvido`, buckets governamentais/entes)

### 3.3 Onde viver no código (decisão futura)

| Opção | Prós | Contras |
|-------|------|---------|
| **A.** Estender `pncp_researcher_service` → `price_research_service` | Reuso imediato de scoring/busca | Nome e DB acoplados a PNCP |
| **B.** Novo microserviço `market_price_service` + PNCP como adapter | Separação clara | Mais deploy/ops |
| **C.** Conectores só no Django (sem índice) | Rápido para 1 API REST | Não escala para autostart 696 itens |

**Recomendação preliminar:** **A → B gradual** — primeiro adaptador interface dentro do researcher; quando ≥2 fontes com índice, extrair serviço federado.

---

## 4. Fluxo de produto desejado

1. Usuário define item na cotação (descrição, qtd, unidade, faixa regional).
2. Busca Inteligente permite marcar **fontes** (default: PNCP; opcional: TCE-UF, BNC, BLL se licenciado).
3. Backend consulta adaptadores **em paralelo** (timeout por fonte, ex. 15–25 s).
4. **Merge + dedup** por `(descrição normalizada, CNPJ, preço ±ε, data)` — não duplicar mesma compra em PNCP e Painel.
5. Scoring unificado (literal, spec, faixa, recência) — independente da plataforma.
6. Top **3 por item por inciso** ou top 3 global respeitando diversidade de fonte (regra de produto a definir).
7. Save grava `source.plataforma` + metadados para o PDF Art. 5º.

---

## 5. Fases de trabalho

### Fase 0 — Discovery (1–2 semanas, sem código)

- [ ] Confirmar com cliente o que é **BNC** e **BLL** (produto, contrato, API, custo por consulta).
- [ ] Listar **TCEs** prioritários (UF do cliente + vizinhas).
- [ ] Para cada fonte: existe API oficial? ToS permite cache? exige credencial?
- [ ] Amostra manual: 10 itens buscados à mão em PNCP vs TCE vs BLL — medir overlap.
- [ ] Definir regra de **inciso** por plataforma para o relatório.

**Entregável:** matriz fonte × API × inciso × risco legal.

### Fase 1 — Contrato e stub (1 sprint)

- [ ] Interface Python `PriceSourceAdapter`: `search(query) -> list[MarketPriceHit]`, `health()`, `capabilities()`.
- [ ] Refatorar entrada PNCP para implementar a interface (sem mudar comportamento).
- [ ] Endpoint experimental `POST /market-search/federated` (feature flag).
- [ ] Campo `source.plataforma` preenchido em saves novos (`pncp` default retroativo).

### Fase 2 — Piloto uma fonte pública (2–3 semanas)

Ordem sugerida:

1. **Painel de Preços / Compras.gov** (se API viável) — overlap PNCP, valida merge/dedup.
2. **Um TCE** com melhor documentação (ex. painel estadual com export ou API).

- [ ] Ingest ou consulta ao vivo com cache TTL curto.
- [ ] UI: checkbox “Incluir TCE-XX” na Busca Inteligente.
- [ ] Testes golden: mesmo termo, resultados normalizados.

### Fase 3 — Agregadores comerciais (depende contrato)

- [ ] Conector BNC/BLL via API key por tenant (Prefeitura).
- [ ] Rate limit e auditoria de uso (faturamento cliente).
- [ ] Não misturar credenciais entre prefeituras (multi-tenant).

### Fase 4 — Autostart multi-fonte

Somente após [`PNCP-PLANO-PARIDADE-BUSCA.md`](PNCP-PLANO-PARIDADE-BUSCA.md) estabilizado:

- [ ] Autostart consulta PNCP + fontes marcadas na cotação.
- [ ] Orçamento de tempo: ex. 60 s/item × fontes, ou PNCP first + fallback TCE se `< 3` preços.
- [ ] Métricas por plataforma: hits, timeout, custo.

---

## 6. Riscos e restrições

| Risco | Mitigação |
|-------|-----------|
| API fechada ou instável (TCE) | Cache + ingest batch noturno; fallback manual |
| Termos de uso proíbem scraping | Só integração oficial ou export licenciado |
| BLL/BNC custo por consulta | Feature flag por tenant; limite diário |
| Duplicata PNCP × Painel × TCE | Dedup por hash `(orgao, data, valor, desc_norm)` |
| Relatório jurídico | Sempre persistir `url_origem` + snapshot mínimo |
| Performance autostart | Não N×fontes em serial; paralelo com cap |

---

## 7. Impacto no modelo de dados (rascunho)

Hoje `PncpCotacaoItem` é PNCP-centric (`numero_pncp`, etc.). Evolução possível **sem breaking change**:

- Generalizar campos opcionais: `numero_pncp` vazio quando `source.plataforma != pncp`.
- `source` passa a ser o identificador primário cross-platform.
- Futuro: renomear modelo para `CotacaoPrecoItem` (migração Django — só quando ≥2 fontes em produção).

Filtros da cotação (`PncpCotacao.filtros` JSON):

```json
{
  "fontes_habilitadas": ["pncp", "tce_pr"],
  "autostart_fallback": ["tce_pr"],
  "bnc_api_key_ref": "vault:prefeitura:123"
}
```

---

## 8. Critérios de aceite (produto)

- [ ] Item com 0 preços só no PNCP pode receber ≥1 de TCE/BNC/BLL configurado.
- [ ] Relatório PDF mostra plataforma/inciso corretos por linha.
- [ ] Save exige CNPJ ou ID auditável equivalente por plataforma.
- [ ] Busca individual e lote respeitam mesmas fontes habilitadas.
- [ ] Desligar uma fonte não quebra cotações antigas (snapshot em `source`).

---

## 9. Ordem recomendada vs. trabalho PNCP atual

```
1. Estabilizar PNCP (paridade lote ↔ individual)     ← em andamento
2. Fase 0 discovery (matriz fontes)                  ← paralelo, baixo custo
3. Fase 1 contrato adapter + plataforma=pncp         ← preparação
4. Fase 2 piloto TCE ou Painel                       ← primeiro valor além PNCP
5. Fase 3 BNC/BLL se houver licença                  ← comercial
```

Não iniciar autostart multi-fonte antes do PNCP estar previsível — evita debug combinatório.

---

## 10. Perguntas abertas (alinhar com cliente)

1. Quais **UF/TCE** são obrigatórios no primeiro release?
2. Cliente já paga **BNC** ou **BLL**? Há documentação de API?
3. Preços de agregador comercial entram em qual **inciso** no relatório institucional?
4. Meta é **3 preços totais** ou **3 por inciso**?
5. Aceita consulta ao vivo (lenta) ou exige índice local por fonte?
6. Há exigência de **somente homologados** também em TCE/BNC?

---

## 11. Próximos passos imediatos (leves)

1. Preencher tabela da **Fase 0** com 3–5 links/APIs reais por fonte citada.
2. Script spike `scripts/spike_price_source_search.py` — uma função por adapter, stdout JSON.
3. Revisão jurídica/compliance sobre cache de dados TCE e termos BLL/BNC.

---

*Última atualização: 2026-06-22 — planejamento inicial; nenhum conector além do PNCP implementado.*
