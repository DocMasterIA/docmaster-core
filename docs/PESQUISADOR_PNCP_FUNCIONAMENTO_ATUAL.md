# Pesquisador PNCP - Funcionamento Atual

Este documento descreve o estado atual do modulo **Pesquisador PNCP** no projeto `docmaster-core`, incluindo arquitetura, fluxos, regras de negocio e endpoints.

## 1) Objetivo do modulo

O Pesquisador PNCP foi implementado para:

- criar e gerenciar cotacoes de pesquisa de precos por usuario;
- buscar itens via PNCP (busca inteligente e busca manual);
- importar itens por planilha (Excel/CSV, inclusive export do Google Sheets);
- consolidar itens por fontes de preco (Art. 5o) e aplicar formula de calculo;
- gerar relatorio PDF institucional com possibilidade de anexar PDF do fornecedor no final.

## 2) Arquitetura atual

### 2.1 Frontend

Projeto Vue em `frontend-vue/`, com telas principais:

- `src/views/PncpResearcher.vue`: lista/criacao/exclusao de cotacoes;
- `src/views/CotacaoDetalhe.vue`: detalhes da cotacao, gestao de itens, formula, importacoes e relatorio;
- `src/views/BuscaManualCotacoes.vue`: pesquisa manual com filtros/ordenacao/UF/modalidade/faixa;
- `src/views/BuscaInteligenteCotacoes.vue`: fluxo de busca inteligente;
- `src/views/RelatorioPesquisaPrecos.vue`: pre-visualizacao de layout.

Servico de API:

- `src/services/pncpResearch.js`

Roteamento com controle de autenticacao:

- `src/router/index.js`

### 2.2 Backend Django

APIs do modulo:

- `backend/app/pncp_cotacao_api.py`: CRUD de cotacao, itens, importacao, anexos de fornecedor;
- `backend/app/pncp_relatorio_api.py`: geracao de PDF de relatorio e verificacao;
- `backend/app/urls.py`: rotas da API.

Modelos:

- `backend/app/models/pncp_cotacao.py`
  - `PncpCotacao`
  - `PncpCotacaoItem`
  - `PncpCotacaoAnexo` (PDF do fornecedor)

Servico de consolidacao/calculo:

- `backend/app/services/pncp_relatorio_itens.py`

Servico de renderizacao PDF:

- `backend/app/services/pncp_relatorio_pdf.py`

### 2.3 Servico PNCP pesquisador (FastAPI)

Servico externo integrado por proxy Django:

- `pncp_researcher_service/`

Usado para indexacao local, backfill e busca de itens.

## 3) Controle de acesso (autenticacao)

As rotas do Pesquisador PNCP **nao sao publicas**.

No `router.beforeEach`:

- se usuario nao autenticado tentar acessar `pesquisador-pncp` (e subrotas), e redirecionado para `/login` imediatamente;
- login autenticado recebe redirecionamento para destino (`query.redirect`) quando aplicavel.

## 4) Fluxo de cotacoes

### 4.1 Criacao

Criada via `POST /api/pncp/cotacoes/research/sessions`.

Campos principais:

- `titulo`
- `termo_busca`
- `modelo_cotacao`
- `filtros` (JSON sanitizado e limitado)

### 4.2 Status da cotacao

Status suportados:

- `aberta`
- `finalizada`
- `cancelada`

Regras:

- cotacao fechada (`finalizada`/`cancelada`) bloqueia adicionar/importar/excluir itens;
- frontend possui botao para **fechar** e para **reabrir** cotacao (volta para `aberta`).

## 5) Busca manual e adicao de itens

Implementacoes atuais em `BuscaManualCotacoes.vue`:

- filtros: termo, periodo, tipo, modalidade, UF, ordenacao, base + variacao;
- busca ampla (`max_paginas` alto) com ordenacao/filtro client-side;
- exclusao de itens com valor `R$ 0,00`;
- adicao em lote para cotacao com chunk de payload.

Ao salvar item da busca manual, sao enviados metadados para rastreabilidade:

- campos de descricao/quantidade/unidade/valores;
- orgao/municipio/UF/modalidade;
- origem;
- dados de faixa regional por item:
  - `valor_base`
  - `variacao_percentual`
  - `faixa_regional` (objeto com os dois campos)

## 6) Importacao por planilha

Endpoint:

- `POST /api/pncp/cotacoes/research/sessions/<sessao_id>/items/import`

Formato:

- `.csv`
- `.xlsx`

Padronizacao:

- `docs/IMPORTACAO_PLANILHA_COTACAO_MANUAL.md`

Modelos disponiveis no frontend:

- `frontend-vue/public/modelos/cotacao-manual-modelo-docmasteria.xlsx`
- `frontend-vue/public/modelos/cotacao-manual-modelo.csv`

## 7) Formula de calculo de precos

A formula e selecionada na tela de detalhes (`CotacaoDetalhe.vue`) e persistida na cotacao.

IDs suportados:

- `media_aritmetica_precos_obtidos`
- `mediana_precos_obtidos`
- `menor_preco`
- `media_saneada`
- `media_ponderada`
- `media_relativa_25_50`

Persistencia:

- armazenada em `cotacao.filtros.formula_calculo` (aceita update por ID ou label).

Calculo:

- implementado em `backend/app/services/pncp_relatorio_itens.py` (`resumo_calculo_precos`);
- aplicado sobre os valores das fontes agrupadas por item.

## 8) Fontes de preco e status do item

No detalhamento da cotacao:

- status por item e exibido como:
  - `Completo` (>= 3 fontes/precos)
  - `Incompleto` (< 3 fontes/precos)

Regra baseada nos grupos consolidados do relatorio (`grupos_relatorio`).

## 9) Faixa Regional do Item (por item)

A faixa regional nao e global da sessao.

Implementacao atual:

- cada item pode carregar sua propria base/variacao em `source`;
- exibicao na tabela do detalhe usa os dados do proprio item;
- evita padronizacao indevida entre itens diferentes.

## 10) Relatorio PDF

Endpoint:

- `POST /api/pncp/cotacoes/research/sessions/<sessao_id>/relatorio/pdf`

Motor:

- HTML/CSS + WeasyPrint
- template em `backend/app/services/pncp_relatorio_pdf.py`
- estilos em `backend/app/services/relatorio-pesquisa-precos.css`

Conteudo institucional atual inclui:

- Metodologia Aplicada
- Conclusao Tecnica
- Resultado consolidado e detalhamento por fontes
- CNPJs identificados
- QR code para abrir a cotacao no sistema

## 11) Anexo da cotacao do fornecedor (PDF)

Objetivo:

- anexar um PDF de fornecedor na cotacao e acrescentar suas paginas ao final do relatorio gerado.

Backend:

- model `PncpCotacaoAnexo` (OneToOne com `PncpCotacao`);
- endpoint de upload:
  - `POST /api/pncp/cotacoes/research/sessions/<sessao_id>/attachments/supplier-pdf`
- validacoes:
  - apenas PDF
  - tamanho maximo configuravel (`PNCP_COTACAO_MAX_ANEXO_PDF_BYTES`, default 30MB)

Geracao do PDF final:

- gera relatorio base;
- se houver anexo, concatena com `pypdf` ao final.

Frontend:

- botao "Anexar Cotacao do Fornecedor" em `CotacaoDetalhe.vue`;
- indica quando existe anexo e permite troca.

## 12) Endpoints principais (resumo)

- `GET/POST /api/pncp/cotacoes/research/sessions`
- `GET/DELETE /api/pncp/cotacoes/research/sessions/<sessao_id>`
- `POST /api/pncp/cotacoes/research/sessions/<sessao_id>/update`
- `POST /api/pncp/cotacoes/research/sessions/<sessao_id>/items`
- `POST /api/pncp/cotacoes/research/sessions/<sessao_id>/items/import`
- `POST /api/pncp/cotacoes/research/sessions/<sessao_id>/items/delete`
- `POST /api/pncp/cotacoes/research/sessions/<sessao_id>/attachments/supplier-pdf`
- `POST /api/pncp/cotacoes/research/sessions/<sessao_id>/relatorio/pdf`
- `GET /api/pncp/cotacoes/research/sessions/<sessao_id>/relatorio/verificar`

## 13) Dependencias relevantes

- `weasyprint` (render PDF)
- `qrcode` (QR no relatorio)
- `pypdf` (merge relatorio + anexo fornecedor)
- `openpyxl` (importacao/geracao de planilha xlsx)

## 14) Observacoes operacionais

- apos mudancas de modelo/migration, executar:
  - `python manage.py migrate`
- para novo suporte de bibliotecas:
  - `pip install -r requirements.txt`

---

Se este modulo continuar evoluindo, recomenda-se manter este arquivo como documento de referencia de estado atual para onboarding tecnico e auditoria de comportamento.
