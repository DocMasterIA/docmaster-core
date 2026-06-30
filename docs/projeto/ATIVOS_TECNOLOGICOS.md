## Ativos Tecnológicos Extraíveis – Visão Geral

### 1. TR/DFD/Ofício Template Engine

- **Nome sugerido**: `tr_dfd_oficio_template_engine`
- **O que resolve**: Preenchimento de modelos DOCX (Termo de Referência, DFD e Solicitação/Ofício) a partir de um conjunto de slots tipados, incluindo:
  - mapeamento de placeholders padronizados;
  - montagem de tabela de itens via âncora `(TR_TABELA_ITENS)` ou estrutura legado;
  - normalização de blocos de texto (objeto, justificativa, problema/benefício, datas, etc.);
  - padronização de fonte (Times New Roman) e estilo de tabela.
- **Esforço de extração**: **Médio** – depende de `python-docx` e de uma definição de slots; é pouco acoplado ao restante do sistema.
- **Forma de serviço sugerida**:
  - Biblioteca Python reutilizável (`tr_dfd_oficio_engine`) com funções `render_tr_from_slots`, `render_dfd_from_tr_slots`, `render_oficio_from_slots`.
  - Micro-serviço FastAPI com endpoints `/render/tr`, `/render/dfd`, `/render/oficio` recebendo JSON de slots + referência de template.

---

### 2. Engine de Slots do TR (Lei 14.133)

- **Nome sugerido**: `tr_slots_llm_engine_14133`
- **O que resolve**: Geração automática de slots para Termo de Referência com base em prompt e contexto:
  - `objeto` (cláusula formal expandida em múltiplos parágrafos);
  - complementos de objeto: `objeto_escopo`, `objeto_entregas`, `objeto_resultados`;
  - `dispensa` (artigo 75 fixo, inciso escolhido por fluxo específico);
  - `itens` (descrição/unidade/quantidade);
  - `justificativa`, `problema_administrativo`, `beneficio_esperado`;
  - campos complementares para DFD e Ofício.
  - integra com llm_agent, llm_api e RAG (exemplos PNCP/TR reais).
- **Esforço de extração**: **Alto** – integra múltiplas camadas externas (orquestrador LLM, agente, Chroma, PNCP).
- **Forma de serviço sugerida**:
  - API especializada `/api/tr-slots/fill` (input: prompt + overrides; output: JSON de slots).
  - Produto B2B “preenchedor oficial de TR” para ERPs, consultorias e outras soluções de compras públicas.

---

### 3. Motor de Geração de Documento Completo (ETP/TR/DFD via RAG)

- **Nome sugerido**: `docmaster_rag_document_engine`
- **O que resolve**: Geração de documentos completos a partir de prompt:
  - estrutura de seções/cláusulas (`structure`);
  - textos por seção (`section_texts`);
  - conversão para DOCX/PDF (via `json_to_docx_and_pdf`);
  - instruções específicas por tipo de documento (ETP, TR, DFD);
  - correção pós-processamento (text_corrector_service).
- **Esforço de extração**: **Médio–Alto** – bem isolado no `rag_service`, mas com forte domínio de documentos públicos.
- **Forma de serviço sugerida**:
  - Micro-serviço “Document Engine as a Service” com endpoints:
    - `/api/docs/generate` → JSON structure + texts;
    - `/api/docs/render` → DOCX/PDF a partir do JSON.

---

### 4. Analisador de Documentos (Compliance)

- **Nome sugerido**: `document_compliance_checker_14133`
- **O que resolve**: Análise de documentos (DOCX/PDF) frente à Lei 14.133:
  - extrai texto e consulta RAG;
  - gera resumo executivo;
  - lista acertos/erros e pontos de atenção de conformidade.
- **Esforço de extração**: **Médio** – pipeline já exposto via endpoint (`/api/rag/analyze-document`), acoplado apenas ao backend Django para upload.
- **Forma de serviço sugerida**:
  - API REST `/api/analyze` (upload ou texto), retornando JSON com `resumo`, `acertos`, `erros`, `referencias`.
  - Micro-SaaS plugável em outras plataformas de gestão de contratos/licitações.

---

### 5. Wrapper RAG + ChromaDB + LLM (Infraestrutura)

- **Nome sugerido**: `rag_core_service`
- **O que resolve**:
  - ingestão em ChromaDB (`/ingest`);
  - queries RAG (`/query`);
  - geração estruturada (`/generate-document`);
  - renderização de JSON em DOCX/PDF (`/render-document`);
  - parametrização por `CHROMA_HOST`, `LLM_ORCHESTRATION_BASE_URL`, etc.
- **Esforço de extração**: **Médio** – já está encapsulado no `rag_service` com Docker próprio.
- **Forma de serviço sugerida**:
  - Micro-serviço genérico de RAG para uso em múltiplos produtos 7Atlas, não apenas o DocMaster.

---

### 6. Text Corrector Service

- **Nome sugerido**: `text_corrector_service`
- **O que resolve**: Correção gramatical e estilística com:
  - LanguageTool;
  - regras manuais pós-processamento (ex.: ETC→ETP, remoção de CJK, normalização de construções recorrentes).
- **Esforço de extração**: **Baixo** – já é um micro-serviço independente com API simples.
- **Forma de serviço sugerida**:
  - API `/correct` com `{text, mode, language}`, usada como utilitário em qualquer pipeline de geração/edição de texto.

---

### 7. PNCP Researcher Service (Micro-serviço Independente)

- **Nome sugerido**: `pncp_market_intel_service`
- **O que resolve**:
  - integração em tempo real com a API oficial do PNCP (`/v1/contratacoes/publicacao`);
  - busca de contratações por UF/município/período/modalidade;
  - filtro por termo de busca no objeto;
  - cálculo de estatísticas de mercado:
    - `valor_min`, `valor_max`, `valor_medio`, `valor_mediano`,
    - lista de contratações com metadados para análise.
- **Esforço de extração**: **Baixo** – módulo já está totalmente desacoplado (`pncp_researcher_service`).
- **Forma de serviço sugerida**:
  - Micro-SaaS de “inteligência de mercado PNCP” com endpoint principal `/api/pncp-research/market-search`.
  - Poder ser usado diretamente em dashboards internos ou na tela `PncpResearcher.vue` de outros produtos.

---

### 8. Shell de Aplicação Governamental (UI/UX)

- **Nome sugerido**: `gov_shell_vue`
- **O que resolve**:
  - layout SPA com:
    - topbar (logo, UF, prefeitura, botão de logout);
    - sidebar com seções expansíveis e links;
    - corpo principal com `router-view`.
  - estilo coeso voltado para aplicações públicas/governamentais.
- **Esforço de extração**: **Médio** – estrutura e CSS já prontos; exigiría parametrização de branding/rotas.
- **Forma de serviço sugerida**:
  - Biblioteca de componentes Vue (`@7atlas/gov-shell`) com:
    - `<GovShell>`, `<GovSidebar>`, `<GovTopbarUserInfo>`, configuração via props/slots.

---

### 9. UI de Geração de Documentos com Slots (Vue)

- **Nome sugerido**: `llm_doc_generator_ui`
- **O que resolve**:
  - tela integrada de geração de documentos com:
    - prompt livre;
    - card lateral de “Dados do assistente (slots)” com seções configuráveis;
    - dropdowns com catálogo de valores persistidos;
    - botões de geração e download de múltiplos formatos (TR/DFD/Ofício/ZIP);
    - feedback visual (loading, mensagens de sucesso/erro).
- **Esforço de extração**: **Médio–Alto** – lógica de domínio TR/DFD é forte, mas o padrão de UI é reaproveitável para outros fluxos LLM.
- **Forma de serviço sugerida**:
  - Template Vue base desacoplado do domínio, com slots para:
    - definição dos campos de assistente;
    - callbacks para chamar diferentes backends de geração.

---

### 10. Pesquisador de Dados PNCP (UI)

- **Nome sugerido**: `pncp_researcher_ui`
- **O que resolve**:
  - interface de pesquisa PNCP com:
    - barra de pesquisa por termo;
    - contador de resultados;
    - cards de resultados (título, preço, órgão, UF/município, modalidade, situação, tema, data).
- **Esforço de extração**: **Baixo** – componente Vue praticamente isolado (`PncpResearcher.vue`).
- **Forma de serviço sugerida**:
  - Componente Vue consumindo o `pncp_market_intel_service`, configurável via prop `apiBaseUrl`.

---

### 11. Micro-SaaS Potenciais (Resumo)

1. **DocMaster RAG Engine** (`docmaster_rag_document_engine`)
   - **O que resolve**: geração de documentos jurídicos (ETP/TR/DFD) completa.
   - **Esforço**: Médio–Alto.
   - **Exposição**: Micro-serviço HTTP (JSON → DOCX/PDF).

2. **TR Slots Filler 14133** (`tr_slots_llm_engine_14133`)
   - **O que resolve**: preenchimento de TR oficial com slots prontos para templates DOCX.
   - **Esforço**: Alto.
   - **Exposição**: API REST especializada.

3. **Document Compliance Checker** (`document_compliance_checker_14133`)
   - **O que resolve**: análise de conformidade de documentos frente à Lei 14.133.
   - **Esforço**: Médio.
   - **Exposição**: API única `/analyze` com upload.

4. **PNCP Market Intelligence** (`pncp_market_intel_service` + `pncp_researcher_ui`)
   - **O que resolve**: painel de mercado público em tempo real via PNCP.
   - **Esforço**: Baixo–Médio.
   - **Exposição**: API + UI plugável.

5. **Text Corrector Service** (`text_corrector_service`)
   - **O que resolve**: correção de texto e ajustes de estilo/jurídicos.
   - **Esforço**: Baixo.
   - **Exposição**: micro-serviço HTTP simples.

6. **DOCX Template Engine** (`tr_dfd_oficio_template_engine` generalizado)
   - **O que resolve**: preenchimento de templates DOCX com base em slots/JSON.
   - **Esforço**: Médio.
   - **Exposição**: Biblioteca Python + Endpoint `/render-docx`.

