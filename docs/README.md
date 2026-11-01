# DocMaster Core Documentation

Central index of the technical documentation. The `docs/` folder is organized by domain.

> **Master document (Jul/2026):** [DOCMASTER-SISTEMA-COMPLETO-JUL2026.md](./DOCMASTER-SISTEMA-COMPLETO-JUL2026.md) — extensive overview of features, stacks, LLMs, microservices, APIs, and flows up to the current state (includes TCE-RS / federated search).  
> **Master document (Jun/2026):** [SISTEMA-DOCMASTER-VISAO-COMPLETA.md](./SISTEMA-DOCMASTER-VISAO-COMPLETA.md) — previous cross-cutting overview.

---

## Structure

```
docs/
├── README.md                    ← this file
├── geracao-documentos/          TR, DFD, official letter, slots, DOCX typography
├── servicos/                    Backend, RAG, LLM API, LLM Agent
├── integracao/                  API, auth, Docker, Qwen
├── projeto/                     Context, assets, debug
├── pncp/                        PNCP researcher, ingestion, AI search
└── deploy/                      Production operations (VPS, boot, PNCP 24/7)
```

---

## Where to start

| Goal | Document |
|------|----------|
| **Updated full overview (Jul/2026)** | [DOCMASTER-SISTEMA-COMPLETO-JUL2026.md](./DOCMASTER-SISTEMA-COMPLETO-JUL2026.md) |
| **Full overview (Jun/2026)** | [SISTEMA-DOCMASTER-VISAO-COMPLETA.md](./SISTEMA-DOCMASTER-VISAO-COMPLETA.md) |
| **Recent TR/DFD fixes (Jun/2026)** | [geracao-documentos/CHANGELOG-2026-06.md](./geracao-documentos/CHANGELOG-2026-06.md) |
| TR/DFD/official-letter slots and placeholders | [geracao-documentos/01-slots-tr-dfd-oficio.md](./geracao-documentos/01-slots-tr-dfd-oficio.md) |
| VPS deploy | [deploy/README.md](./deploy/README.md) |
| Overall project architecture | [projeto/CONTEXTO_PROJETO_DOCMASTER_IA.md](./projeto/CONTEXTO_PROJETO_DOCMASTER_IA.md) |
| PNCP — overview | [pncp/00-INDICE.md](./pncp/00-INDICE.md) |

---

## Document generation (TR / DFD / official letter)

| File | Contents |
|------|----------|
| [geracao-documentos/00-INDICE.md](./geracao-documentos/00-INDICE.md) | Folder index |
| [geracao-documentos/CHANGELOG-2026-06.md](./geracao-documentos/CHANGELOG-2026-06.md) | Changelog: DFD department, typography, signature, deploy |
| [geracao-documentos/02-dfd-setor-requisitante.md](./geracao-documentos/02-dfd-setor-requisitante.md) | Fix for `(DFD_SETOR_REQUISITANTE)` |
| [geracao-documentos/03-docx-tipografia-e-assinatura.md](./geracao-documentos/03-docx-tipografia-e-assinatura.md) | Justification + 3 lines before the name |
| [geracao-documentos/04-deploy-templates-docx.md](./geracao-documentos/04-deploy-templates-docx.md) | `rag_service` build and templates on the VPS |

---

## Services

| File | Contents |
|------|----------|
| [servicos/DOC_BACKEND.md](./servicos/DOC_BACKEND.md) | Django: APIs, views, multi-tenant |
| [servicos/DOC_RAG_SERVICE.md](./servicos/DOC_RAG_SERVICE.md) | RAG: ingestion, generation, analysis |
| [servicos/DOC_LLM_API.md](./servicos/DOC_LLM_API.md) | LLM orchestration (Ollama) |
| [servicos/DOC_LLM_AGENT.md](./servicos/DOC_LLM_AGENT.md) | Agent: structure, clauses |
| [servicos/DOC_CONFIG_AMBIENTE.md](./servicos/DOC_CONFIG_AMBIENTE.md) | Environment variables |
| [servicos/ANALISE_DETALHADA_RAG_SERVICE.md](./servicos/ANALISE_DETALHADA_RAG_SERVICE.md) | In-depth RAG analysis |
| [servicos/MODULO_ANALISE_DOCUMENTOS.md](./servicos/MODULO_ANALISE_DOCUMENTOS.md) | Compliance analysis module |

---

## Integration

| File | Contents |
|------|----------|
| [integracao/API_FRONTEND_BACKEND.md](./integracao/API_FRONTEND_BACKEND.md) | Frontend ↔ Django API contracts |
| [integracao/AUTENTICACAO_DJANGO.md](./integracao/AUTENTICACAO_DJANGO.md) | Auth and sessions |
| [integracao/INTEGRACAO_DJANGO_LLM.md](./integracao/INTEGRACAO_DJANGO_LLM.md) | Django → LLM/RAG flow |
| [integracao/DOCKER.md](./integracao/DOCKER.md) | Local Docker Compose |
| [integracao/QWEN-INTEGRACAO-DOCMASTER.md](./integracao/QWEN-INTEGRACAO-DOCMASTER.md) | Qwen in DocMaster |

---

## Deploy and operations

See [deploy/README.md](./deploy/README.md).

---

## Typical document generation flow

1. **Frontend** → `POST api/documentos/gerar-via-llm` (Django)
2. **Django** → `POST /api/rag/generate-document` (RAG)
3. **RAG** → LLM Agent (structure) + LLM API (text) + ChromaDB (retrieval)
4. **RAG** → `tr_template` / `dfd_template` / `oficio_template` → DOCX
5. **Django** → FileResponse to the frontend

---

## Ports (development)

| Service | Port |
|---------|------|
| Django | 8000 |
| LLM API | 8002 |
| LLM Agent | 8003 |
| RAG Service | 8004 |

---

*Last updated: Jun/2026.*
