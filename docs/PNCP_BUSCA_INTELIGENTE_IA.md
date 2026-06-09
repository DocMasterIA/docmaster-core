# PNCP - Busca Inteligente com IA (Implementação Atual)

Este documento descreve como a busca inteligente do modulo PNCP foi implementada no estado atual do projeto.

## 1) Objetivo

Entregar, para cada busca inteligente:

- **exatamente 3 cotações** selecionadas automaticamente;
- classificação com:
  - `score_aprovacao` (0 a 100),
  - `confiabilidade` (Alta / Média / Baixa),
  - `risco` (Baixo / Médio / Alto),
  - `status` (Aprovado / Revisar).

## 2) Arquitetura da integração

### Backend (serviço PNCP)

- Arquivo principal de lógica: `pncp_researcher_service/app/service.py`
- Arquivo de rotas: `pncp_researcher_service/app/api.py`

Novo endpoint criado:

- `POST /api/pncp-research/market-search/intelligent`

Esse endpoint reutiliza a busca PNCP existente e aplica uma camada de seleção inteligente.

### Frontend (tela de busca inteligente)

- View: `frontend-vue/src/views/BuscaInteligenteCotacoes.vue`
- Service: `frontend-vue/src/services/pncpResearch.js`

No frontend, a tela passou a consumir o endpoint inteligente e exibir os 3 resultados com as métricas.

## 3) Fluxo técnico no backend

### 3.1 Busca base

A função `market_search_intelligent(payload)` chama primeiro:

- `market_search(payload)`

Isso mantém toda a estratégia de coleta já existente no PNCP (paginação, filtros e extração de itens).

### 3.2 Scoring por item

Para cada item retornado, o score final é composto por sinais:

1. **Aderência semântica/técnica**
   - base em `score_relevancia` (pipeline de match existente).
2. **Confirmação na tabela de itens**
   - usa `confirmado_nos_itens` quando disponível.
3. **Recência**
   - calcula com base em `data_publicacao`.
4. **Coerência de valor**
   - compara o valor do item com a mediana dos valores encontrados.

Resultado:

- `score_aprovacao`: inteiro no intervalo 0..100.

### 3.3 Classificação derivada

Com base no `score_aprovacao`:

- `confiabilidade`:
  - Alta: >= 80
  - Média: >= `PNCP_SEARCH_MIN_SCORE_APROVACAO` (default **50**)
  - Baixa: abaixo do mínimo
- `risco`:
  - Baixo: >= 80
  - Médio: >= mínimo configurado
  - Alto: abaixo do mínimo
- `status`:
  - Aprovado: >= mínimo (default **50**; antes ~55–60 implícito)
  - Revisar: abaixo do mínimo

### 3.4 Seleção final (exatamente 3)

Após ordenar por score:

- aplica seleção com diversidade de órgão (evitar repetição);
- retorna no máximo 3 com prioridade para diversidade;
- fallback completa até 3 se necessário.

Regra final do endpoint:

- resposta contém **somente 3 itens selecionados** (`top3`).

## 4) Contrato da resposta (resumo)

A resposta do endpoint inteligente mantém formato compatível com `MarketSearchResponse`:

- `ok`
- `filtros`
- `stats`
- `itens` (somente os 3 selecionados)

Campos relevantes por item:

- `score_aprovacao`
- `confiabilidade`
- `risco`
- `status`
- `score_relevancia`
- `confirmado_nos_itens`
- `data_publicacao`

## 5) Alterações realizadas por arquivo

### `pncp_researcher_service/app/service.py`

- adicionadas funções auxiliares de score e classificação;
- adicionada função principal:
  - `market_search_intelligent(payload)`;
- inclusão de `data_publicacao` no payload de item processado.

### `pncp_researcher_service/app/api.py`

- import da função inteligente;
- novo endpoint:
  - `@router.post("/market-search/intelligent")`

### `frontend-vue/src/services/pncpResearch.js`

- nova função:
  - `intelligentMarketSearch(payload, signal)`

### `frontend-vue/src/views/BuscaInteligenteCotacoes.vue`

- troca da chamada para `intelligentMarketSearch`;
- mapeamento da tabela para usar métricas reais:
  - score/confiabilidade/risco/status;
- comportamento focado na lista retornada pela IA (3 selecionados).

## 6) Alinhamento com especificação funcional

A implementação segue os pontos do documento de módulo:

- seleção automática de 3 cotações;
- análise por compatibilidade/recência/coerência;
- saída com indicadores de risco e confiança para apoio ao modo assistido.

## 7) Limitações atuais

- a camada inteligente atual é predominantemente **algorítmica/heurística**;
- não executa inferência LLM item-a-item no `pncp_researcher_service`.

Isso reduz custo e latência, mantendo previsibilidade operacional.

## 8) Evoluções sugeridas

1. incorporar explicabilidade por item (`motivos do score`);
2. registrar histórico de decisão (auditoria de seleção);
3. opção de "modo rigoroso" (descartar itens sem confirmação em tabela);
4. opcional de reranking por LLM quando necessário.
