# Integração Django ↔ LLM (DocMaster)

Arquitetura de integração entre o backend Django e o serviço de geração de documentos (rag_service + llm_agent).

---

## 1. Visão geral

| Componente | Tecnologia | Papel |
|------------|------------|-------|
| **Django** | Backend web, auth, modelos (User, Prefeitura, Template) | Orquestra a requisição, monta o contexto do usuário, chama o LLM |
| **rag_service** | FastAPI, ChromaDB | RAG, geração de texto via LLM, pós-processamento, DOCX |
| **llm_agent** | Orquestração LLM | Estrutura do documento (structure-from-prompt) |

**Fluxo atual (sem integração completa):**
- Django: `generate_document_with_values_api` → template + values → render DOCX (sem LLM)
- rag_service: `generate-document` → user_prompt → LLM gera estrutura + textos → DOCX

**Fluxo desejado:**
- Django: usuário logado + template selecionado + prompt → monta contexto → chama rag_service → LLM usa contexto (nome, secretaria, prefeitura) → retorna DOCX

---

## 2. Contrato de dados

### 2.1 O que o Django envia ao rag_service

Payload estendido para `POST /api/rag/generate-document`:

```json
{
  "user_prompt": "Gerar ETP para coleta seletiva de resíduos",
  "collection": null,
  "top_k_per_section": 5,

  "context": {
    "usuario": {
      "nome_completo": "João da Silva",
      "secretaria": "Secretaria de Meio Ambiente",
      "prefeitura": "Prefeitura de São Bernardo do Campo",
      "orgao": "Prefeitura Municipal de São Bernardo do Campo"
    },
    "template_id": "uuid-do-template-clicado",
    "document_type_hint": "etp"
  }
}
```

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `user_prompt` | string | sim | Pedido livre do usuário |
| `context` | object | não | Contexto do usuário e do documento |
| `context.usuario` | object | não | Dados do usuário logado |
| `context.usuario.nome_completo` | string | não | Nome completo |
| `context.usuario.secretaria` | string | não | Nome da secretaria/gabinete |
| `context.usuario.prefeitura` | string | não | Nome curto (ex.: São Bernardo do Campo) |
| `context.usuario.orgao` | string | não | Órgão completo (ex.: Prefeitura Municipal de X) |
| `context.template_id` | string | não | ID do template selecionado (uso futuro: base para estrutura) |
| `context.document_type_hint` | string | não | Sugestão: etp, dfd, termo_referencia |

### 2.2 Como o rag_service usa o contexto

- `context.usuario` → injetado no `ctx` passado ao `_generate_clause_text` e `_generate_list_content`
- O prompt de cada seção inclui: "Órgão: {orgao}", "Usuário: {nome_completo}", "Secretaria: {secretaria}" quando disponível
- `context.template_id` → reservado para uso futuro (estrutura base do documento a partir do template)
- `context.document_type_hint` → pode sobrescrever ou reforçar o `document_type` retornado pelo llm_agent

---

## 3. API do rag_service (alterações)

### 3.1 Schema `GenerateDocumentRequest` (estendido)

```python
class GenerateDocumentRequest(BaseModel):
    user_prompt: str = Field(...)
    collection: Optional[str] = None
    top_k_per_section: int = 5
    context: Optional[Dict[str, Any]] = None  # NOVO
```

### 3.2 Função `generate_full_document` (assinatura estendida)

```python
async def generate_full_document(
    user_prompt: str,
    collection_name: Optional[str] = None,
    top_k_per_section: int = 5,
    context_override: Optional[Dict[str, Any]] = None,  # NOVO
) -> Dict[str, Any]:
```

- Se `context_override` for passado, mesclar com o `ctx` retornado pelo llm_agent (override tem prioridade)
- Campos esperados em `context_override`: `usuario`, `template_id`, `orgao`, `objeto`, etc.

---

## 4. Django: construção do contexto

### 4.1 Serviço/classe para montar o contexto

```python
# backend/app/services/llm_context.py (ou similar)

def build_llm_context_from_request(request) -> dict:
    """Monta o dicionário context para envio ao rag_service."""
    user = request.user
    if not user.is_authenticated:
        return {}
    ctx = {}
    # Usuário
    nome = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
    ctx["usuario"] = {
        "nome_completo": nome,
        "secretaria": str(user.secretaria) if getattr(user, "secretaria", None) else None,
        "prefeitura": user.prefeitura.nome_municipio if getattr(user, "prefeitura", None) else None,
        "orgao": f"Prefeitura Municipal de {user.prefeitura.nome_municipio}" if getattr(user, "prefeitura", None) else None,
    }
    return ctx
```

### 4.2 Nova API Django: geração via LLM ✅ Implementado

Endpoint que chama o rag_service em vez de apenas preencher template:

```
POST /api/documentos/gerar-via-llm
```

**Request (JSON):**
```json
{
  "user_prompt": "Gerar ETP para coleta seletiva",
  "template_id": "uuid-opcional",
  "document_type_hint": "etp",
  "output": "docx"
}
```

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| `user_prompt` | sim | Pedido livre do usuário |
| `template_id` | não | ID do template (uso futuro) |
| `document_type_hint` | não | etp, dfd, termo_referencia |
| `output` | não | `docx` (default) ou `json` |

**Resposta:** `output=docx` retorna o arquivo DOCX; `output=json` retorna metadados.

**Fluxo:**
1. Django autentica o usuário
2. Monta `context` com `build_llm_context_from_request(request)` + `template_id` do body
3. Faz POST para `{RAG_SERVICE_URL}/api/rag/generate-document`
4. Body: `{ "user_prompt": ..., "context": context }`
5. Se `output=docx`, repassa `output_docx=true` como query param
6. Retorna o DOCX ao usuário ou salva em DocumentInstance

### 4.3 Configuração: URL do rag_service

```python
# settings.py
RAG_SERVICE_URL = os.environ.get("RAG_SERVICE_URL", "http://localhost:8004")
```

---

## 5. Uso do template_id (futuro)

Quando implementado:

- Django envia `template_id` do template clicado
- rag_service pode:
  - (Opção A) Extrair estrutura (root_sections) do DOCX do template e usar como base em vez de structure-from-prompt
  - (Opção B) Usar o template apenas como referência de estilo/estrutura para o llm_agent
  - (Opção C) Passar o conteúdo do template como contexto adicional ao RAG

Por ora, `template_id` é armazenado no context e pode ser usado em logs ou metadados. A implementação da "base a partir do template" fica para fase posterior.

---

## 6. Diagrama de sequência (fluxo integrado)

```
[Usuário] → [Django] → [rag_service] → [llm_agent]
                |            |                |
                |  POST /generate-document    |
                |  { user_prompt, context }   |
                |            |                |
                |            |  structure-from-prompt (user_prompt)
                |            |  ← structure, context, especificacoes
                |            |
                |            |  merge context + context_override
                |            |
                |            |  para cada seção:
                |            |    retrieve RAG
                |            |    _generate_clause_text(ctx com usuario, orgao, etc.)
                |            |
                |  ← structure, section_texts, table_data
                |
                |  json_to_docx_and_pdf()
                |
[Usuário] ← DOCX/PDF
```

---

## 7. Checklist de implementação

### Fase 1 – Contrato e contexto ✅

- [x] Estender `GenerateDocumentRequest` com `context: Optional[dict]`
- [x] Estender `generate_full_document` com `context_override`
- [x] Mesclar `context_override` no `ctx` usado nas chamadas de geração
- [x] Injetar `usuario.nome_completo`, `usuario.secretaria`, `usuario.prefeitura`, `usuario.orgao` nos prompts (quando presentes)

### Fase 2 – Django chama LLM ✅

- [x] Criar `build_llm_context_from_request(request)` em `backend/app/services/llm_context.py`
- [x] Criar endpoint `POST /api/documentos/gerar-via-llm` em `backend/app/api.py`
- [x] Registrar rota em `backend/app/urls.py`

### Fase 3 – Frontend Vue ✅

- [x] Adicionar modo "Criar do zero (ETP, DFD, TR)" no `DocumentGenerator.vue`
- [x] Chamar `POST /api/documentos/gerar-via-llm` quando esse modo estiver ativo
- [x] Tratar resposta DOCX e exibir botão de download

### Fase 4 – Template como base (depois)

- [ ] Definir como extrair estrutura do template DOCX
- [ ] Passar estrutura ou conteúdo do template para o rag_service quando `template_id` for enviado
- [ ] Ajustar fluxo para usar estrutura do template em vez de structure-from-prompt quando aplicável

---

## 8. Arquivos a modificar

| Arquivo | Alteração |
|---------|-----------|
| `rag_service/app/api.py` | `GenerateDocumentRequest.context`; passar para `generate_full_document` |
| `rag_service/app/document_generator.py` | `generate_full_document(context_override)`; merge de context; usar usuario/orgao nos prompts |
| `backend/app/services/llm_context.py` | Novo: `build_llm_context_from_request` |
| `backend/app/api.py` | Novo endpoint `gerar_via_llm_api` ou similar |
| `backend/mdlicitatech/settings.py` | `RAG_SERVICE_URL` |
| `backend/app/urls.py` | Rota para o novo endpoint |
