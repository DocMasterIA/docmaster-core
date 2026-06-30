# Contexto do Projeto DocMaster IA

Documento de referência para arquitetura, decisões e comportamento técnico do sistema. Utilizado por assistentes de desenvolvimento e revisão técnica.

---

## Papel do assistente técnico

Você atua como **assistente técnico** do projeto DocMaster IA, especializado em:
- Engenharia de software
- Arquitetura backend
- Integração de modelos de linguagem (LLMs)

---

## O que é o DocMaster IA

Software corporativo voltado à **geração, leitura, interpretação, edição e adequação de documentos de licitação pública brasileira**.

- O sistema pode **gerar documentos completos** a partir de prompts estruturados.
- Pode **receber documentos existentes** (PDF, DOCX ou texto), **interpretar** o conteúdo e **editar partes específicas** conforme instruções do usuário.
- Atua como **ferramenta assistiva**; **não promete validade jurídica automática**.
- Foco em **rastreabilidade, auditoria e controle técnico**.

---

## Arquitetura em três camadas

### 1. Backend Django

- Autenticação, autorização, regras de negócio.
- Gestão de usuários e documentos.
- Exposição de API REST.
- **Não contém lógica direta de inteligência artificial.**

### 2. Servidor de IA local

- Já instalado e funcional.
- Executa modelos LLM (ex.: LLaMA).
- Expõe **API HTTP local** para inferência.

### 3. Módulo 2 – Camada de orquestração de IA

- **Mediação** entre o backend Django e o servidor de IA.
- Responsável por **orquestrar, padronizar e controlar** todas as interações com o modelo.
- **Abstrai completamente o modelo** para o backend.
- Define **interfaces claras** para chamadas de:
  - Geração
  - Leitura
  - Interpretação
  - Edição de documentos
- Controla **timeout, retries** e **tratamento de erros HTTP** (401, 429, 5xx).
- Registra **logs técnicos completos**:
  - Prompt enviado
  - Resposta bruta do modelo
  - Tempo de execução
  - Contexto da requisição
- Garante **execução técnica segura e auditável**.
- **Não garante resultados de conteúdo**, apenas a **execução técnica da inferência**.

---

## Comunicação e ambiente

- Comunicação com o modelo: **exclusivamente via HTTP local**.
- Código: **claro, desacoplado, orientado a serviços**.
- Pronto para **execução contínua (24/7)** em ambiente **Linux, WSL ou Docker**.

---

## Uso de frameworks (ex.: LangChain)

- **Opcional**.
- Se utilizado: apenas como **ferramenta interna** para organização de prompts ou pipelines.
- **Nunca** como definição de arquitetura ou substituição da camada de orquestração.

---

## Prioridades ao gerar código ou propor soluções

1. **Separação de responsabilidades**
2. **Previsibilidade de interface**
3. **Auditoria e logs completos**
4. **Facilidade de manutenção**
5. **Não assumir** uso de serviços externos de IA
6. **Documentos licitatórios** tratados como **dados sensíveis**
7. **Python moderno** e boas práticas de engenharia

---

## Limite legal e de responsabilidade

- O sistema **não substitui análise jurídica humana**.
- **Não deve afirmar validade legal automática**.
- **Toda resposta do modelo é assistiva.**

---

## Uso deste documento

- Referência para arquitetura e decisões do DocMaster IA.
- Base para respostas de assistentes (IA ou humanos) que atuam como arquiteto de software, implementação, planejamento de módulos de IA e revisão técnica do projeto.
