# Documentação dos Módulos e Serviços – DocMaster Core

Índice da documentação técnica do sistema. Cada módulo/serviço possui um arquivo `.md` dedicado com URLs, payloads, prompts de teste, contextos, funcionalidades, o que faz e não faz e possíveis melhorias.

---

## Estrutura do projeto

| Diretório | Descrição |
|-----------|-----------|
| **backend/** | Django (mdlicitatech): app principal, APIs de templates, geração via LLM, autenticação, multi-tenant por prefeitura |
| **rag_service/** | FastAPI: ingestão, retrieval (ChromaDB), geração de documento completo, análise de conformidade, DOCX/PDF |
| **llm_agent/** | FastAPI: interpretação de prompt livre, geração de estrutura (seções), estrutura de cláusulas, registro de seções |
| **llm_api/** | FastAPI: orquestração LLM (Ollama), endpoints planner/section/analysis/generate, auditoria |

---

## Documentos disponíveis

| Arquivo | Conteúdo |
|---------|----------|
| [README_DOCUMENTACAO.md](README_DOCUMENTACAO.md) | Este índice |
| [DOC_BACKEND.md](DOC_BACKEND.md) | Backend Django: URLs, views, APIs, serviços, contexto LLM, faz/não faz, melhorias |
| [DOC_RAG_SERVICE.md](DOC_RAG_SERVICE.md) | RAG Service: endpoints, schemas, prompts, ingestão, geração, análise, testes, melhorias |
| [DOC_LLM_AGENT.md](DOC_LLM_AGENT.md) | LLM Agent: endpoints, prompts, schemas, interpretador, estrutura, clause-structure, melhorias |
| [DOC_LLM_API.md](DOC_LLM_API.md) | LLM API (orchestration): endpoints, adapter, Ollama, auditoria, testes, melhorias |
| [DOC_CONFIG_AMBIENTE.md](DOC_CONFIG_AMBIENTE.md) | Configuração e ambiente: variáveis de ambiente, URLs entre serviços, feature flags |

---

## Ordem de execução típica (geração de documento)

1. **Frontend** → POST `api/documentos/gerar-via-llm` (Django), com `user_prompt` e opcionalmente `template_id`, `document_type_hint`, `output`.
2. **Django** → monta contexto do usuário (`build_llm_context_from_request`), chama **RAG Service** `POST /api/rag/generate-document`.
3. **RAG Service** → chama **LLM Agent** `POST /api/agent/structure-from-prompt` para obter estrutura + context + especificações.
4. **RAG Service** → para cada seção: retrieval no ChromaDB, geração de texto via **LLM API** `POST /api/llm/generate`.
5. **RAG Service** → monta DOCX/PDF (docx_generator) e retorna JSON ou arquivo ao Django.
6. **Django** → retorna JSON ou FileResponse (DOCX) ao frontend.

---

## Portas padrão (desenvolvimento)

| Serviço | Porta | Comando típico |
|---------|-------|----------------|
| Django | 8000 | `python manage.py runserver` |
| LLM API | 8002 | `uvicorn app.main:app --port 8002` (em llm_api/) |
| LLM Agent | 8003 | `uvicorn llm_agent.app.main:app --port 8003` (em raiz) |
| RAG Service | 8004 | `uvicorn rag_service.app.main:app --port 8004` (em raiz) |
| ChromaDB | 8000 (ou 11434) | Servidor ChromaDB separado |

---

*Última atualização: fev/2025.*
