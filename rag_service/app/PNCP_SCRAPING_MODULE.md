### Módulo de integração PNCP / Web Scraping – Esquematização

Este arquivo resume as ideias e decisões já levantadas para o módulo de integração com o PNCP, incluindo uso da API oficial e web scraping complementar, focado em melhorar a geração de ETP, TR e DFD.

---

#### 1. Papel do PNCP na arquitetura do DocMaster

- PNCP é a principal fonte pública de dados de contratações (Lei 14.133/2021):
  - avisos, editais, licitações, atas, contratos, documentos fiscais etc.
- Na arquitetura atual do DocMaster (RAG + llm_agent + slots TR/DFD/ETP), o PNCP entra como:
  - **Fonte estruturada** de contexto (via API):
    - objeto resumido, modalidade, fase, órgão, município/UF, valores, datas, etc.
  - **Fonte textual rica** (via scraping):
    - textos integrais de TR, ETP, minutas de contratos e outros anexos para alimentar o RAG.

Objetivo principal: usar PNCP para produzir documentos (ETP, TR, DFD) **mais formais, detalhados e ancorados na prática real** da Administração, reduzindo textos genéricos.

---

#### 2. Camadas de integração com o PNCP

1. **API de consultas (já iniciada)**
   - Base: `https://pncp.gov.br/api/consulta`.
   - Cliente: `pncp_client.py` com função assíncrona `search_contracts(...)`.
   - Serviço de domínio: `pncp_service.py` com `get_similar_contracts_for_request(...)`, que:
     - usa `user_prompt` + `user_context` (órgão, município, UF) para montar a query;
     - chama `search_contracts`;
     - devolve:
       - lista de `PNCPContractRef`;
       - texto pronto “Foram encontradas as seguintes contratações similares no PNCP...”.

2. **Web scraping / anexos**
   - Camada web do PNCP (ex.: `https://pncp.gov.br/app/editais`) lista editais e, para cada um, normalmente há:
     - página de detalhe do edital;
     - anexos (PDF/DOCX) – frequentemente contendo TR, ETP, minutas etc.
   - Scraping entra para:
     - baixar e extrair texto desses anexos;
     - classificar o tipo de documento (TR, ETP, contrato etc.);
     - alimentar o vector store com **cláusulas reais**.

---

#### 3. O que faz sentido scrappear (e por quê)

Não é interessante scrappear tudo que já vem bem estruturado na API. A web/scraping deve focar em:

1. **Páginas de detalhe de edital**
   - Podem ter descrições mais longas do que o objeto resumido da API.
   - Úteis como contexto textual adicional, mas menos prioritárias que anexos.

2. **Anexos dos editais**
   - Arquivos PDF/DOCX com:
     - Termos de Referência;
     - Estudos Técnicos Preliminares (ETP);
     - minutas de contrato;
     - outros documentos com redação de cláusulas.
   - São a principal fonte para:
     - exemplos de **cláusulas reais** de objeto, justificativa, riscos etc.;
     - estilo, vocabulário e estrutura típicos da Administração;
     - melhores prompts e respostas no RAG/LLM.

Conclusão: **API para metadados estruturados e estatística; scraping para textos integrais de TR/ETP/minutas, usados como base do RAG.**

---

#### 4. Estratégia de filtragem (selecionar bem o que ingerir)

Camadas de filtro sugeridas:

- **Na API (antes de baixar anexos):**
  - Geografia: `municipio`, `uf`, órgão/unidade (priorizar entes-alvo do produto).
  - Temporal: ano de publicação (focar últimos 3–5 anos).
  - Modalidade/tipo: pregão, concorrência, dispensa, inexigibilidade etc.
  - Palavras-chave no objeto: “pneus”, “limpeza”, “saúde”, “TI”, etc.

- **Após baixar anexos:**
  - Classificar tipo de documento:
    - `termo_referencia`, `etp`, `minuta_contrato`, `outro`.
  - Ingerir em massa principalmente TR/ETP/minutas (documentos de cláusulas).

---

#### 5. Modelo de dados e etiquetamento refinado

Para ingestão em massa no vector store, cada chunk deve ter metadados ricos:

- `document_type`: `termo_referencia`, `etp`, `contrato`, etc.
- `fonte`: `pncp`.
- `numero_pncp`: identificador PNCP da licitação/contrato.
- `ano`: ano do edital/contrato.
- `orgao`, `unidade_compradora`.
- `municipio`, `uf`.
- `modalidade`: pregão, concorrência, dispensa etc.
- `tipo_anexo`: `tr`, `etp`, `minuta_contrato`, `outro`.
- `tema_objeto`: rótulo inferido (ex.: “limpeza urbana”, “pneus”, “alimentação escolar”, “TI”).
- `lei_regente`: ex.: `lei_14133` quando detectado.

Com isso, as consultas RAG podem ser filtradas de forma precisa, por exemplo:

- `where={"document_type": "termo_referencia", "fonte": "pncp", "lei_regente": "lei_14133", "uf": "GO"}`.

Isso ajuda a obter exemplos compatíveis com:
- o tipo de documento,
- a lei aplicável,
- e o contexto geográfico/institucional do usuário.

---

#### 6. Pipeline de ingestão em massa (recomendado)

Em vez de reprocessar PDFs on-demand a cada TR/ETP, usar um pipeline assíncrono:

1. **Descoberta (API PNCP)** – `pncp_discovery` (futuro módulo)
   - Usa API para listar editais/contratações que atendam aos filtros desejados.
   - Armazena metadados básicos e URLs de anexos.

2. **Download de anexos** – `pncp_downloader`
   - Baixa anexos selecionados (TR, ETP, minutas) e salva em pasta estruturada.

3. **Extração de texto** – `pncp_text_extractor`
   - Converte PDF/DOCX em texto bruto (pode reutilizar pipeline já usado para outros documentos no projeto).

4. **Chunking e ingestão** – `pncp_ingest`
   - Divide texto em chunks (ex.: 500–1500 caracteres).
   - Enrich com metadados (ver seção 5).
   - Chama `ingest_text(...)` do RAG, informando `collection_name` e `metadata`.

5. **Reprocessamento/atualização periódica**
   - Jobs agendados para:
     - detectar novos editais relevantes;
     - baixar e ingerir novos TR/ETP;
     - manter o índice PNCP atualizado.

---

#### 7. Uso em tempo real na geração de documentos

Em tempo de geração (ETP, TR, DFD, etc.), a ideia é:

1. **Consultar RAG sobre os chunks já ingeridos**
   - Exemplo:
     - `retrieve(query=user_prompt, where={"document_type": "termo_referencia", "fonte": "pncp", "lei_regente": "lei_14133", "uf": "GO"})`.
   - Injetar trechos relevantes nos prompts de:
     - `document_generator` (TR/ETP completos);
     - `tr_slots_llm` (slots de TR);
     - futuros fluxos (DFD, contratos, ARP).

2. **Consultar API PNCP para dados estruturados frescos**
   - Usar `get_similar_contracts_for_request(...)` para:
     - recuperar contratações similares recentes;
     - obter valores/quantidades/órgãos/modalidades;
     - gerar um bloco textual “Referências de contratações similares no PNCP” para o prompt.

3. **Casos on-demand (exceção)**
   - Se o usuário indicar um edital específico (ex.: número PNCP):
     - fluxo rápido para baixar anexos, extrair, chunnar e ingerir imediatamente antes do RAG.

---

#### 8. Benefícios esperados

- **Textos mais formais e técnicos**:
  - TR/ETP/DFD passam a ser gerados em cima de exemplos reais do PNCP, não só de leis abstratas.

- **Melhor aderência à Lei 14.133/2021**:
  - Documentos reais do PNCP já trazem a lei aplicada na prática, o que guia a LLM a:
    - citar artigos/incisos de forma mais coerente;
    - evitar uso indevido de dispositivos.

- **Melhor qualidade de objeto, justificativa e riscos**:
  - Cláusulas de objeto deixam de ser genéricas/curtas.
  - Justificativas e análises de risco ganham vocabulário e estrutura típicos da Administração.

- **Escalabilidade e desempenho**:
  - A ingestão em massa e offline evita reprocessar PDFs a cada solicitação.
  - Em tempo real, o sistema apenas consulta o índice RAG e, se necessário, faz uma chamada leve à API PNCP.

