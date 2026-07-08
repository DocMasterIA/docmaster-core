# Portal de Compras Públicas (PCP) — integração para busca de preços

Pesquisa técnica e operacional (jul/2026) para conectar o DocMaster ao **Portal de Compras Públicas** (ECUSTOMIZE) no mesmo espírito da busca PNCP: termo livre → preços homologados → `MarketPriceHit` → scoring/faixa/Art. 5º.

Complementa:

- [MODULO-FONTES-PRECOS-00-PREPARACAO.md](./MODULO-FONTES-PRECOS-00-PREPARACAO.md) — contrato federado
- [MODULO-FONTES-PRECOS-02-PARTICIONAMENTO.md](./MODULO-FONTES-PRECOS-02-PARTICIONAMENTO.md) — épico **1-PCP-***

---

## 1. O que é o PCP (contexto)

| Aspecto | Detalhe |
|---------|---------|
| Operador | **ECUSTOMIZE** — marketplace privado de licitações eletrônicas |
| Público | Prefeituras, consórcios, autarquias, terceiro setor (forte **municipal/estadual**) |
| Relação PNCP | Processos costumam ser **espelhados no PNCP** após publicação — overlap alto |
| Inciso Art. 5º | **II** — outros entes públicos / domínio amplo municipal-estadual |
| Site | [portaldecompraspublicas.com.br](https://www.portaldecompraspublicas.com.br/) |
| Biblioteca oficial | [Biblioteca de Dados PCP (Zendesk)](https://bibliotecapcp.zendesk.com/hc/pt-br) |

**Valor para o DocMaster:** cobrir compras que **nasceram no PCP** e podem demorar ou faltar no índice PNCP local; reforçar Inciso II em relatório Art. 5º.

---

## 2. Duas rotas de integração (decisão crítica)

Existem **dois caminhos distintos**. Não misturar legalmente nem tecnicamente.

### 2.1 Rota A — Parceiro oficial (recomendada para produção)

| Item | Detalhe |
|------|---------|
| O quê | API/WebService documentado após **credenciamento de parceiro** |
| Como obter | Formulário Zendesk → setor **Relações Institucionais**, área **ERP**, assunto integração ([artigo oficial](https://bibliotecapcp.zendesk.com/hc/pt-br/articles/4593549708570-Parceiros-Consulta-p%C3%BAblica-de-processos-via-API)) |
| Credencial | **PublicKey** enviada por e-mail em até **7 dias úteis** |
| Documentação | Seção **Integração via API** na Biblioteca de Dados: |
| | • Parceiros — Consulta pública de processos via API |
| | • Parceiros — Consulta processos **finalizados** via API |
| | • Comprador — Integração via WebService (escopo **comprador**, não pesquisa de mercado) |
| Página comercial | [portaldecompraspublicas.com.br/parceiros](https://www.portaldecompraspublicas.com.br/parceiros) |
| Regulamento | Automação só na área **Desenvolvedores** com permissão expressa ([regulamento §5.3.1, §6.7](https://www.portaldecompraspublicas.com.br/regulamento/brb)) |

**Próximo passo operacional:** abrir chamado como **DocMaster / parceiro ERP**, solicitar sandbox + doc de endpoints de processos finalizados + limites de rate.

### 2.2 Rota B — API v2 do frontend (descoberta técnica, risco legal)

A interface web do portal consome uma API JSON **sem autenticação** observada em jul/2026:

```text
Base: https://compras.api.portaldecompraspublicas.com.br/v2/
```

| Endpoint | Método | Uso |
|----------|--------|-----|
| `/licitacao/processos` | GET | Busca processos (paginação, filtros) |
| `/licitacao/{codigoLicitacao}/itens` | GET | Itens/lotes do processo |
| `/licitacao/processos?uf={codigo}` | GET | UF numérica interna (ex.: `100135` = SP) |

**Validação em jul/2026 (spike HTTP):**

```bash
# Processos finalizados com "paracetamol" no resumo
curl -s "https://compras.api.portaldecompraspublicas.com.br/v2/licitacao/processos?pagina=1&objeto=paracetamol&status=3"

# Itens homologados — filtro por descrição dentro do processo
curl -s "https://compras.api.portaldecompraspublicas.com.br/v2/licitacao/458772/itens?filtro=paracetamol&pagina=1"
```

**Riscos da Rota B:**

- **Não é API pública documentada** — pode mudar, bloquear IP ou exigir auth sem aviso.
- **Regulamento ECUSTOMIZE** proíbe coleta automatizada sem permissão (robôs, scrape, garimpo de dados — §5.3.1.1, §6.7).
- **Sem SLA** — uso em produção DocMaster exige Rota A ou contrato escrito.

**Uso recomendado da Rota B:** spike de discovery, protótipo interno, dimensionamento de ingest — **não** autostart em cliente sem parceria.

---

## 3. Modelo de dados da API v2 (spike jul/2026)

### 3.1 Busca de processos — `GET /licitacao/processos`

Parâmetros observados (query string):

| Parâmetro | Exemplo | Notas |
|-----------|---------|-------|
| `objeto` | `paracetamol` | Busca textual no **resumo** do processo |
| `status` | `3` | `3` = em andamento/finalizado na UI pública; homologados usam `7` no objeto `status` da resposta |
| `pagina` | `1` | Paginação 1-based |
| `uf` | `100135` | Código interno (não é sigla `SP`) — lista em `get_search_parameters` em wrappers de terceiros |
| `orgao`, `processo`, `modalidade`, `dataInicial`, `dataFinal`, `tipoData`, `municipio`, `julgamento`, `realizacao` | — | Presentes na UI; validar com doc parceiro |

Resposta (campos úteis por processo):

```json
{
  "codigoLicitacao": 458772,
  "identificacao": "11594258/2025",
  "numero": "…",
  "resumo": "…",
  "razaoSocial": "Prefeitura …",
  "status": { "codigo": 7, "descricao": "Processo Finalizado" },
  "unidadeCompradora": { "cidade": "…", "uf": "ES" },
  "urlReferencia": "/es/prefeitura-…/…-458772",
  "dataHoraPublicacao": "…"
}
```

Paginação: `result`, `pageCount`, `currentPage`, `nextPage`, `total`.

### 3.2 Itens do processo — `GET /licitacao/{codigo}/itens`

| Campo item | Significado | Uso DocMaster |
|------------|-------------|---------------|
| `descricao` | Descrição + código catálogo (ex. SIASG `2.32.02.0151-8`) | Scoring literal/spec |
| `unidade` | UN, FR, CAP, L… | Normalização |
| `quantidade` | Qtd licitada | Cálculo unitário |
| `valorReferencia` | Preço **referência unitário** (edital) | Fallback se sem homologação |
| `melhorLance` | Valor **total** do lance vencedor (não unitário) | `valor_unitario = melhorLance / quantidade` |
| `situacao.codigo` | `7` = Homologado, `8` = Adjudicado | Filtro `somente_homologados` |
| `participacao` | Ampla concorrência, ME/EPP… | Metadado |
| `isLote` + `lotes.result[].itens[]` | Estrutura aninhada | Achatar lotes → lista plana |

**Exemplo validado (processo 458772, paracetamol):**

- `valorReferencia`: 1,3244
- `melhorLance`: 32.635 (total)
- `quantidade`: 30.500
- **Preço unitário homologado calculado:** 32.635 / 30.500 ≈ **R$ 1,07**

**Parâmetro `filtro`:** filtra itens **dentro** do processo por texto na descrição — essencial porque `objeto` só busca no resumo do certame.

### 3.3 O que a API v2 **não** expõe (gap vs PNCP)

| Dado | PNCP (DocMaster hoje) | PCP API v2 (spike) |
|------|------------------------|---------------------|
| CNPJ fornecedor vencedor | Sim (`enrich_homolog_items_from_pncp`) | **Não** nos endpoints testados |
| Nome fornecedor | Sim | **Não** |
| Detalhe processo | `/contratos/.../itens/resultados` | `GET /licitacao/{id}` retornou vazio no spike |
| Busca direta por item | Índice FTS local SQLite | **2 saltos**: processos → itens |
| Anexos / edital PDF | Parcial | Não na API v2 observada |

**Mitigação:** após obter `codigoLicitacao`, tentar **enriquecer via PNCP** (mesmo processo publicado) para CNPJ — reforça dedup Camada B.

---

## 4. Fluxo proposto no DocMaster (Camada A → B)

### 4.1 Diferença mental vs PNCP

```text
PNCP (hoje):
  termo → FTS índice local (milhões de itens) → top candidatos → enrich API resultados → faixa

PCP (proposto):
  termo → API processos (resumo) → N processos → API itens (+ filtro) → homologados → faixa
```

PCP é **process-centric**; PNCP no DocMaster é **item-centric** com índice pré-ingestido.

### 4.2 Algoritmo `PortalComprasPublicasAdapter.search()`

```text
1. Entrada: FederatedSearchQuery (termo_busca, uf, somente_homologados, timeout)

2. Normalizar UF:
   - Se query.uf = "SP" → resolver codigo PCP (cache estático ou GET parametros parceiro)

3. GET /licitacao/processos:
   - objeto = derive_anchor_search_term(termo)  # reutilizar product_spec_match
   - status = 3 (finalizados) ou conforme doc parceiro
   - uf, pagina=1..max_paginas (cap ex.: 3–5 páginas / 36–60 processos)

4. Para cada codigoLicitacao (paralelo com semáforo, ex. 5 concurrent):
   GET /licitacao/{id}/itens?filtro={termo}&pagina=1

5. Achatar lotes → itens; filtrar situacao in (7, 8) se somente_homologados

6. Para cada item:
   - valor_unitario_homologado = melhorLance / quantidade  (se melhorLance > 0)
   - senão valor_unitario = valorReferencia (marcar confiança menor)
   - descricao_item, unidade, orgao, municipio, uf de unidadeCompradora
   - plataforma = "portal_compras_publicas"
   - plataforma_item_id = f"pcp:{codigoLicitacao}:{codigo_item}"
   - url_origem = https://www.portaldecompraspublicas.com.br{urlReferencia}
   - inciso_classificacao = inciso_ii; esfera = municipal|estadual (heurística razaoSocial)

7. Scoring/spec/faixa — **Camada B** (mesmo pipeline PNCP pós-normalização)

8. Dedup com hits PNCP:
   - chave fraca: (uf, orgao_norm, desc_norm[:80], round(valor, 2))
   - chave forte se existir: numero processo cruzado PNCP/PCP
```

### 4.3 Performance e limites

| Fator | Estimativa |
|-------|------------|
| Latência | 1 busca processos + 20–60 GET itens → **5–25 s** sem cache |
| Rate limit | Desconhecido oficial; spike não retornou headers `X-RateLimit` |
| Autostart 696 itens | **Inviável** live API — exige **ingest 24/7** (modelo `vieira-a/api-licitacoes-br`) |
| Cache | Redis/SQLite staging: processos finalizados + itens, refresh diário |

### 4.4 Estratégia ingest (recomendada para paridade PNCP)

Inspirado em projetos comunitários ([daniel-prando/desafio-backend](https://github.com/daniel-prando/desafio-backend), [vieira-a/api-licitacoes-br](https://github.com/vieira-a/api-licitacoes-br)):

```text
Job cron (4×/dia ou diário):
  - Varre processos status=finalizado, janela rolling 90–180 dias
  - Persiste PROCESSO + ITEM em SQLite/Postgres fonte=pcp
  - FTS em descricao_item (mesmo padrão local_index PNCP)

Adapter.search():
  - Preferir índice local se hit_count >= threshold
  - Fallback live API só para termos frios ou health índice
```

---

## 5. Mapeamento → `MarketPriceHit`

| Campo canônico | Origem PCP |
|----------------|------------|
| `plataforma` | `"portal_compras_publicas"` |
| `plataforma_item_id` | `"pcp:{codigoLicitacao}:{codigo}"` |
| `descricao_item` | `descricao` |
| `valor_unitario` | `valorReferencia` |
| `valor_unitario_homologado` | `melhorLance / quantidade` se homologado |
| `unidade_medida` | `unidade` |
| `quantidade` | `quantidade` |
| `orgao` | `razaoSocial` ou `unidadeCompradora.nomeUnidadeCompradora` |
| `municipio` | `unidadeCompradora.cidade` |
| `uf` | `unidadeCompradora.uf` |
| `fornecedor_nome` | null (v2) — enrich PNCP ou doc parceiro |
| `fornecedor_cnpj` | null (v2) |
| `data_referencia` | `dataHoraPublicacao` do processo |
| `inciso_classificacao` | `inciso_ii` |
| `esfera` | `municipal` (default) |
| `url_origem` | URL pública do processo |
| `raw` | snapshot truncado JSON item + processo |

Persistência Django (`PncpCotacaoItemCotacao.source`):

```json
{
  "plataforma": "portal_compras_publicas",
  "inciso": "inciso_ii",
  "codigo_licitacao": 458772,
  "identificacao": "11594258/2025",
  "situacao_item": 7,
  "valor_referencia": 1.3244,
  "melhor_lance_total": 32635.0
}
```

---

## 6. Overlap PNCP e deduplicação

Muitos processos PCP são **publicados no PNCP** (integração ECUSTOMIZE). Efeitos:

| Cenário | Comportamento desejado |
|---------|------------------------|
| Mesmo item PNCP + PCP | **1 hit** na UI (dedup Camada B) |
| Só no PCP | Novo preço Inciso II |
| Só no PNCP | Mantém fluxo atual |
| Preços divergentes | Preferir **PNCP homologado** (fonte federal); log audit |

Heurística dedup: mesmo `identificacao`/`numero` processo + `codigo` item ou similaridade descrição + valor ±1%.

---

## 7. Épicos (referência particionamento)

| ID | Entrega | Notas |
|----|---------|-------|
| **1-PCP-DIS** | Chamado parceiro + PublicKey + doc sandbox | **Bloqueante legal produção** |
| **1-PCP-SPIKE** | Client v2 read-only + testes campos preço | Rota B — concluído parcialmente jul/2026 |
| **1-PCP-HTTP** | `pcp_client.py` — retry, timeout, paginação | Reutilizar padrão `pncp_client.py` |
| **1-PCP-NORM** | `to_market_price_hit(item, processo)` | Cuidado `melhorLance` total vs unitário |
| **1-PCP-ADAPTER** | `PortalComprasPublicasAdapter` | Depende Parte 0 núcleo federado |
| **1-PCP-ING** | Job ingest + FTS local | Necessário para autostart |
| **1-PCP-ENRICH** | CNPJ via PNCP crosswalk | Opcional v1 |
| **1-PCP-UI** | Checkbox «Portal Compras Públicas» | Multi-select fontes |

**Dependência:** [MODULO-FONTES-PRECOS-02-PARTICIONAMENTO.md](./MODULO-FONTES-PRECOS-02-PARTICIONAMENTO.md) Parte **0** antes de adapter.

---

## 8. Aspectos legais e operacionais

1. **Regulamento §5.3.1.1 / §6.7:** automação externa (robôs, scrape, garimpo) **proibida** sem permissão ECUSTOMIZE.
2. **Consulta manual gratuita** (§5.2) não autoriza ingest em massa.
3. **Rota produção:** parceria + PublicKey + termos área Desenvolvedores.
4. **LGPD:** dados de fornecedores — tratar como dados comerciais públicos de licitação; política ECUSTOMIZE aplica.
5. **Contrato cliente:** posicionar PCP como **fonte complementar Inciso II**, não substituto PNCP.

---

## 9. Comparativo resumido PNCP × PCP

| | PNCP (DocMaster) | PCP |
|--|------------------|-----|
| Auth produção | API pública federal | PublicKey parceiro |
| Busca | Item FTS local | Processo → itens (2 hops) |
| Homologado | `valorUnitarioHomologado` API | `melhorLance / quantidade` |
| Fornecedor | CNPJ via enrich | Gap na v2 — enrich PNCP |
| Índice | SQLite 24/7 ingest | A construir (1-PCP-ING) |
| Inciso | I | II |
| Overlap | — | Alto com PNCP |

---

## 10. Próximos passos recomendados

1. **Comercial:** abrir chamado Zendesk (Relações Institucionais / ERP) em nome DocMaster.
2. **Técnico:** com PublicKey, comparar endpoints parceiro vs v2 frontend — unificar client.
3. **Produto:** definir se busca manual federada usa live API (lento) ou só índice após ingest.
4. **Código:** após Parte 0, implementar `1-PCP-HTTP` + `1-PCP-NORM` + testes unitários preço unitário.
5. **Não fazer:** scraping HTML; autostart live sem cache; ignorar dedup PNCP.

---

## 11. Referências

| Recurso | URL |
|---------|-----|
| Biblioteca de Dados PCP | https://bibliotecapcp.zendesk.com/hc/pt-br |
| Parceiros — API processos | https://bibliotecapcp.zendesk.com/hc/pt-br/articles/4593549708570 |
| Página parceiros | https://www.portaldecompraspublicas.com.br/parceiros |
| Regulamento | https://www.portaldecompraspublicas.com.br/regulamento/brb |
| API v2 (frontend) | https://compras.api.portaldecompraspublicas.com.br/v2/ |
| Projeto referência ingest | https://github.com/vieira-a/api-licitacoes-br |
| Desafio backend (campos) | https://github.com/daniel-prando/desafio-backend |

---

*Documento gerado jul/2026 — spike HTTP validado em ambiente de desenvolvimento; endpoints não oficiais podem mudar.*
