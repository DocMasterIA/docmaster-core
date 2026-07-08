# Catálogo comercial — módulos de integração multi-plataforma

Documento para **declarar escopo**, **precificar** e **vender** conexões além do PNCP.

Relacionado: [PLANO-FONTES-PRECOS-MULTIPLAS-PLATAFORMAS.md](./PLANO-FONTES-PRECOS-MULTIPLAS-PLATAFORMAS.md), [MODULO-FONTES-PRECOS-00-PREPARACAO.md](./MODULO-FONTES-PRECOS-00-PREPARACAO.md).

**Premissa comercial:** preço = **módulos fixos** (infra compartilhada) + **conectores** (por plataforma) + **opcionais** (autostart, índice local, credencial tenant).

**Premissa técnica:** nem toda plataforma tem API de **pesquisa de preço por termo livre** como o PNCP. Parte exige **catálogo**, **ingest batch** ou **parceria comercial** — isso muda muito o esforço.

---

## 1. Estrutura de módulos (como eu venderia)

```text
┌─────────────────────────────────────────────────────────────────┐
│ M0 — Núcleo federado (obrigatório, 1× por produto)              │
│   contrato MarketPriceHit, orquestrador, dedup, faixa, UI base  │
└────────────────────────────┬────────────────────────────────────┘
                             │
     ┌───────────────────────┼───────────────────────┐
     ▼                       ▼                       ▼
┌─────────┐           ┌─────────┐           ┌─────────┐
│ M-PNCP  │           │ M-CG    │           │ M-PCP   │  … conectores
│ (já)    │           │ Compras │           │ Portal  │
│         │           │ .gov    │           │ Compras │
└─────────┘           └─────────┘           └─────────┘

Opcionais transversais:
  O1 — Autostart multi-fonte
  O2 — Índice local + ingest (batch)
  O3 — Credenciais multi-tenant (vault)
  O4 — Relatório PDF / inciso por plataforma
  O5 — Manutenção anual por conector
```

---

## 2. Módulo M0 — Núcleo federado (base obrigatória)

**O que entrega**

| Item | Descrição |
|------|-----------|
| Interface `PriceSourceAdapter` | `search`, `health`, `capabilities` |
| `MarketPriceHit` canônico | Normalização cross-platform |
| Orquestrador | Paralelo, timeout por fonte, merge |
| Dedup | Hash orgão + data + preço + CNPJ + descrição |
| Faixa regional | Reuso `pricing_faixa` / gate direcional |
| Scoring unificado | Spec match + literal (pós-normalização) |
| Django | `source.plataforma`, `filtros.fontes_habilitadas` |
| UI mínima | Checkbox fontes na Busca Inteligente |
| Endpoint | `POST …/market-search/federated` (feature flag) |

**Complexidade:** ★★★★☆ (4/5) — refactor PNCP sem quebrar produção.

**Esforço referência:** 18–28 dias úteis (1 dev sênior + revisão).

**Preço sugerido (fórmula):** `R$ (dias × diária técnica × 1,2)` — margem discovery/refactor.

Exemplo com diária R$ 1.200: **R$ 26.000 – R$ 40.000** (M0 sozinho).

**Dependência:** PNCP estável (✅ jul/2026).

---

## 3. Conectores por plataforma

Escala de complexidade:

| Nota | Significado |
|------|-------------|
| ★☆☆☆☆ | API REST pública, busca por termo, doc Swagger |
| ★★☆☆☆ | API REST + mapeamento moderado |
| ★★★☆☆ | API com modelo diferente (catálogo, não texto livre) |
| ★★★★☆ | Batch/ingest ou parceria comercial |
| ★★★★★ | Sem API pública de preços / contrato fechado |

---

### 3.1 Compras.gov (Dados Abertos — Pesquisa de Preço)

**O que é hoje (2025–2026)**

- Painel de Preços / Painel de Compras **parou de atualizar** em jul/2025 ([comunicado MGI](https://www.gov.br/compras/pt-br/acesso-a-informacao/comunicados/2025/no-30-25-dados-do-painel-de-precos-e-do-painel-de-compras-deixam-de-ser-atualizados)).
- Caminho oficial: **API Dados Abertos** — `https://dadosabertos.compras.gov.br/swagger-ui/`
- Módulo **Pesquisa de Preço**: material e serviço, REST/JSON, paginação.
- Endpoints típicos: `modulo-pesquisa-preco/1_consultarMaterial`, `3_consultarServico`, variantes CSV/detalhe.

**Modelo de busca (crítico para preço)**

| Aspecto | PNCP (DocMaster) | Compras.gov API |
|---------|------------------|-----------------|
| Entrada | Termo livre («acebrofilina 50mg») | **`codigoItemCatalogo`** (catálogo SIASG) |
| Auth | Pública consulta | Pública (dados abertos) |
| Overlap | — | Alto com PNCP federal (Inciso I) |
| Valor para cliente | Base | Complemento SIASG / histórico Compras.gov |

**Implicação:** conector **não é plug-and-play**. Exige submódulo **M-CG-CAT** (mapeamento descrição → código catálogo) ou busca híbrida catálogo+PNCP.

**Módulos comerciais sugeridos**

| ID | Escopo | Complexidade | Dias | Notas |
|----|--------|--------------|------|-------|
| **M-CG-API** | Adapter consulta material/serviço por código catálogo + filtros UF/data | ★★★☆☆ | 8–12 | Swagger + normalização |
| **M-CG-CAT** | Resolver termo livre → `codigoItemCatalogo` (FTS catálogo ou LLM assistido) | ★★★★☆ | 12–20 | Maior risco técnico |
| **M-CG-ING** | Ingest periódico API → índice local (autostart) | ★★★★☆ | 15–25 | Opcional O2 |

**Inciso Art. 5º:** I (governamental federal).

**Risco:** overlap PNCP — cliente pode pagar e ver pouco ganho; vender como «camada SIASG / Compras.gov histórico».

**Faixa preço indicativa (M-CG-API + M-CG-CAT):** **R$ 24.000 – R$ 38.000** @ R$ 1.200/dia.

---

### 3.2 Portal de Compras Públicas (PCP — Ecustomize)

**O que é**

- Maior marketplace **independente** de licitações (municipal/estadual).
- Operado por ECUSTOMIZE; integrado ao PNCP.
- Foco: prefeituras, consórcios, terceiro setor — **Inciso II** forte.

**API / acesso**

| Canal | Situação |
|-------|----------|
| API / WebService parceiro | Existe — área **Parceiros / Desenvolvedores** ([portaldecompraspublicas.com.br/parceiros](https://www.portaldecompraspublicas.com.br/parceiros)) |
| Acesso público | Consulta processos; automação exige **credenciamento** e termos ([regulamento](https://www.portaldecompraspublicas.com.br/regulamento/brb)) |
| Documentação | **Não pública** — depende de **análise de parceria** comercial |
| Modelo provável | REST/SOAP + API key por parceiro/ERP |

**Implicação comercial**

1. **Fase comercial obrigatória** antes do dev (contrato parceiro, sandbox, ToS).
2. Escopo de «pesquisa de preços» depende do que a API expõe (processos homologados vs editais abertos).
3. Proibir scraping — regulamento trata coleta não autorizada.

**Módulos comerciais sugeridos**

| ID | Escopo | Complexidade | Dias | Notas |
|----|--------|--------------|------|-------|
| **M-PCP-DIS** | Discovery + homologação parceria (entregável doc, não código) | ★★☆☆☆ | 3–5 | Cobrar à parte |
| **M-PCP-API** | Adapter consulta preços/processos conforme doc parceiro | ★★★★☆ | 15–25 | Depende sandbox |
| **M-PCP-UI** | Fonte «PCP» na busca + save + PDF inciso II | ★★☆☆☆ | 5–8 | Após M-PCP-API |

**Inciso:** II (entes públicos municipais/estaduais).

**Faixa preço indicativa (M-PCP-DIS + M-PCP-API + M-PCP-UI):** **R$ 28.000 – R$ 46.000** — **+ custo/licença PCP** se houver.

---

### 3.3 TCE/RS (Dados Abertos — LicitaCon)

**O que é**

- Portal CKAN: [dados.tce.rs.gov.br](https://dados.tce.rs.gov.br/)
- API CKAN: `https://dados.tce.rs.gov.br/api/3/action/…`
- Dados: licitações **consolidadas** do **LicitaCon** (14 CSVs/ano: LICITACAO, ITEM, PROPOSTA, etc.).
- Atualização: anos recentes **diária**; anos antigos semanal.
- **Não é API de busca por produto** — é **download batch** + modelo relacional.

**Modelo técnico realista**

```text
Opção A — Consulta ao vivo: inviável (sem endpoint «buscar paracetamol»)
Opção B — Ingest batch: baixar ZIP → normalizar ITEM+PROPOSTA → índice FTS local
Opção C — Híbrido: índice local + refresh diário (cron)
```

**Módulos comerciais sugeridos**

| ID | Escopo | Complexidade | Dias | Notas |
|----|--------|--------------|------|-------|
| **M-TCE-RS-ING** | Pipeline ingest LicitaCon → SQLite/Postgres | ★★★★☆ | 20–30 | Parser 14 arquivos |
| **M-TCE-RS-SRC** | Adapter search no índice (termo + UF RS + faixa) | ★★★☆☆ | 10–15 | Depende ingest |
| **M-TCE-RS-OPS** | Cron refresh + monitoramento | ★★☆☆☆ | 5–8 | Manutenção |

**Inciso:** II (outros entes — estadual/municipal RS).

**Escalabilidade:** TCE/PR, TCE/SC = **novo módulo por UF** (layout LicitaCon similar, mas validar).

**Faixa preço indicativa (ingest + search RS):** **R$ 36.000 – R$ 54.000** @ R$ 1.200/dia.

**Template «TCE outra UF»:** 60–70% do preço RS após o primeiro (reuso parser).

---

### 3.4 BLL Compras

**O que a documentação pública mostra**

- Site: [bll.org.br](https://bll.org.br/) — plataforma de **disputa** + **Banco de Preços** (gratuito para órgãos).
- Manual integração ([PDF](https://lanceadmbll.azurewebsites.net/Arquivos/Manual%20de%20integra%C3%A7%C3%A3o%20webservice%20e%20csv.pdf)): Web Service SOAP/REST para **promotor** — compor processo, obter lances/propostas/resultados.
- Chave: gerada na tela **Promotor → Integração Web Service** (por órgão).
- **Não documenta API pública do Banco de Preços** para busca por termo externo.

**Overlap:** BLL declara integração PNCP — muitos preços já aparecem no PNCP.

**Cenários de produto**

| Cenário | Viabilidade | Módulo |
|---------|-------------|--------|
| A — Buscar no «Banco de Preços BLL» como usuário pesquisador | ⚠️ Exige API comercial não publicada | M-BLL-PRECOS (discovery) |
| B — Importar resultados de processos **do próprio órgão** promotor BLL | ✅ API documentada | M-BLL-PROC |
| C — Não integrar; usar PNCP + TCE | ✅ Zero custo BLL | — |

**Módulos comerciais sugeridos**

| ID | Escopo | Complexidade | Dias | Notas |
|----|--------|--------------|------|-------|
| **M-BLL-DIS** | Contato comercial BLL — API Banco de Preços | ★★☆☆☆ | 3–5 | Pré-requisito cenário A |
| **M-BLL-PRECOS** | Adapter pesquisa preços (se API existir) | ★★★★★ | ? | **Só após discovery** — orçar após doc |
| **M-BLL-PROC** | WS promotor: resultados homologados do órgão | ★★★★☆ | 12–18 | SOAP, chave tenant |
| **M-BLL-UI** | Fonte BLL na cotação | ★★☆☆☆ | 5–8 | Após adapter |

**Inciso:** I ou II conforme origem do preço no banco.

**Recomendação de venda:** **não vender M-BLL-PRECOS** sem carta da BLL confirmando endpoint de pesquisa. Oferecer M-BLL-DIS como pacote discovery pago.

**Faixa preço indicativa (M-BLL-PROC + UI, cenário B):** **R$ 20.000 – R$ 31.000**.

---

### 3.5 BNC (Bolsa Nacional de Compras)

**O que é**

- [bnc.org.br](https://bnc.org.br/) / [bnccompras.com](https://bnccompras.com/) — pregão eletrônico.
- **Sem API pública documentada** para pesquisa de preços.
- Evidência de API **privada** com `apikey` (libs terceiras, ex. [php-bnc](https://github.com/mathiconical/php-bnc)) — foco em **gestão de processo** (GUID, status, resultado), não catálogo de preços.
- Editais: acesso público sem cadastro; participação exige plano fornecedor.

**Implicação**

| Abordagem | Complexidade |
|-----------|--------------|
| Parceria oficial BNC + doc API | ★★★★☆ (se existir produto parceiro) |
| Engenharia reversa / não oficial | ★★★★★ + **risco legal/ToS** — não recomendado |
| Scraping | ★★★★★ + **proibido** sem autorização |

**Módulos comerciais sugeridos**

| ID | Escopo | Complexidade | Dias |
|----|--------|--------------|------|
| **M-BNC-DIS** | Discovery comercial + jurídico | ★★☆☆☆ | 3–5 |
| **M-BNC-API** | Adapter (somente após contrato + doc) | ★★★★★ | 20–40+ |
| **M-BNC-UI** | Fonte na cotação | ★★☆☆☆ | 5–8 |

**Recomendação:** vender **M-BNC-DIS** fixo; **M-BNC-API** como **orçamento fechado pós-discovery** (T&M ou risco).

**Faixa discovery:** **R$ 4.000 – R$ 6.000**. API: **sob consulta** (mínimo **R$ 35.000** se API existir).

---

## 4. Opcionais transversais

| ID | Escopo | Complexidade | Dias | Preço ref. (R$ 1.200/d) |
|----|--------|--------------|------|-------------------------|
| **O1** | Autostart multi-fonte (PNCP first + fallback) | ★★★★☆ | 12–18 | 14.400 – 21.600 |
| **O2** | Índice local genérico (schema multi-plataforma) | ★★★★☆ | 15–22 | 18.000 – 26.400 |
| **O3** | Vault credenciais por prefeitura (BNC/BLL/PCP) | ★★★☆☆ | 8–12 | 9.600 – 14.400 |
| **O4** | PDF/relatório — coluna plataforma + URL origem | ★★☆☆☆ | 5–8 | 6.000 – 9.600 |
| **O5** | Manutenção anual por conector ativo | ★★☆☆☆ | 12 d/ano | 20–30% do valor do conector/ano |

---

## 5. Pacotes sugeridos (para proposta)

### Pacote «Essencial federado»

- M0 + M-CG-API (sem catálogo automático — cliente informa código ou usa subset)
- **~R$ 50.000 – R$ 68.000**

### Pacote «RS estadual»

- M0 + M-TCE-RS-ING + M-TCE-RS-SRC + O4
- **~R$ 62.000 – R$ 88.000**

### Pacote «Marketplace municipal»

- M0 + M-PCP-DIS + M-PCP-API + M-PCP-UI + O3
- **~R$ 58.000 – R$ 90.000** (+ parceria PCP)

### Pacote «Completo discovery-first»

- M0 + DISCOVERY todas (PCP, BLL, BNC) + 1 piloto técnico (TCE-RS **ou** Compras.gov)
- **~R$ 45.000 – R$ 55.000** discovery + piloto **R$ 35.000 – R$ 54.000**

---

## 6. Matriz resumo — complexidade × API × preço

| Plataforma | API pesquisa preço | Auth | Modelo busca | Complexidade | Prioridade DocMaster | Faixa conector |
|------------|-------------------|------|--------------|--------------|----------------------|----------------|
| **PNCP** | ✅ REST pública | Não | Termo livre + índice | ★★ (já feito) | — | Incluso |
| **Compras.gov** | ✅ REST dados abertos | Não | **Código catálogo** | ★★★★ | Alta (federal) | R$ 24–38k |
| **Portal Compras Públicas** | ⚠️ Parceiro | API key parceiro | A definir | ★★★★ | Alta (municipal) | R$ 28–46k |
| **TCE/RS** | ⚠️ CKAN + CSV batch | Não | **Ingest + FTS** | ★★★★ | Alta (RS) | R$ 36–54k |
| **BLL** | ❌ Banco preços / ⚠️ WS promotor | Chave promotor | Processo, não catálogo | ★★★★★ / ★★★★ | Média (overlap PNCP) | R$ 20–31k (proc) |
| **BNC** | ❌ pública | apikey privada? | Indefinido | ★★★★★ | Baixa até discovery | Discovery 4–6k |

---

## 7. Ordem de implementação recomendada (ROI)

```text
1. M0 (núcleo)                    — habilita tudo
2. M-TCE-RS ou M-PCP              — maior gap vs PNCP (Inciso II)
3. M-CG-API + M-CG-CAT            — federal complementar (overlap)
4. M-BLL-PROC                     — só se cliente é promotor BLL
5. M-BNC                          — só pós-contrato BNC
6. O1 autostart                   — por último
```

---

## 8. Itens de proposta (checklist comercial)

Para cada conector, declarar no contrato:

- [ ] Objetivo (Inciso I/II, autostart ou manual)
- [ ] Fonte de dados (API oficial / batch / parceiro)
- [ ] SLA de disponibilidade (**best effort** se API terceira)
- [ ] Credenciais fornecidas pelo cliente (BLL promotor, PCP parceiro)
- [ ] Exclusões: scraping, overlap PNCP, homologação jurídica Art. 5º
- [ ] Manutenção (O5) — APIs mudam sem aviso (ex.: Compras.gov 2025)
- [ ] Discovery pago antes de fixed-price (PCP, BNC, BLL-PRECOS)

---

## 9. Perguntas para fechar escopo com o cliente

1. Qual **UF** e quais **TCEs** são mandatórios?
2. Cliente usa **BLL** como promotor ou só quer «banco de preços»?
3. Já é **parceiro PCP** ou aceita processo comercial Ecustomize?
4. Meta: **3 preços totais** ou diversidade por **inciso**?
5. Aceita **ingest noturno** (TCE) vs só consulta ao vivo?
6. Orçamento para **M0** + quantos conectores no v1?

---

*Última atualização: 2026-07-06 — mapeamento APIs públicas e modelo comercial; valores indicativos @ R$ 1.200/dia dev (ajustar diária).*
