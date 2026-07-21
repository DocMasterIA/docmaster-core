# Documentação DocMaster Core

Índice central da documentação técnica. A pasta `docs/` está organizada por domínio.

> **Documento mestre (jul/2026):** [DOCMASTER-SISTEMA-COMPLETO-JUL2026.md](./DOCMASTER-SISTEMA-COMPLETO-JUL2026.md) — visão extensa de funcionalidades, stacks, LLMs, microsserviços, APIs e fluxos até o estado atual (inclui TCE-RS / pesquisa federada).  
> **Documento mestre (jun/2026):** [SISTEMA-DOCMASTER-VISAO-COMPLETA.md](./SISTEMA-DOCMASTER-VISAO-COMPLETA.md) — visão transversal anterior.

---

## Estrutura

```
docs/
├── README.md                    ← este arquivo
├── geracao-documentos/          TR, DFD, Ofício, slots, tipografia DOCX
├── servicos/                    Backend, RAG, LLM API, LLM Agent
├── integracao/                  API, auth, Docker, Qwen
├── projeto/                     Contexto, ativos, debug
├── pncp/                        Pesquisador PNCP, ingestão, busca IA
└── deploy/                      Operação em produção (VPS, boot, PNCP 24/7)
```

---

## Por onde começar

| Objetivo | Documento |
|----------|-----------|
| **Visão completa atualizada (jul/2026)** | [DOCMASTER-SISTEMA-COMPLETO-JUL2026.md](./DOCMASTER-SISTEMA-COMPLETO-JUL2026.md) |
| **Visão completa (jun/2026)** | [SISTEMA-DOCMASTER-VISAO-COMPLETA.md](./SISTEMA-DOCMASTER-VISAO-COMPLETA.md) |
| **Correções recentes TR/DFD (jun/2026)** | [geracao-documentos/CHANGELOG-2026-06.md](./geracao-documentos/CHANGELOG-2026-06.md) |
| Slots e placeholders TR/DFD/Ofício | [geracao-documentos/01-slots-tr-dfd-oficio.md](./geracao-documentos/01-slots-tr-dfd-oficio.md) |
| Deploy na VPS | [deploy/README.md](./deploy/README.md) |
| Arquitetura geral do projeto | [projeto/CONTEXTO_PROJETO_DOCMASTER_IA.md](./projeto/CONTEXTO_PROJETO_DOCMASTER_IA.md) |
| PNCP — visão geral | [pncp/00-INDICE.md](./pncp/00-INDICE.md) |

---

## Geração de documentos (TR / DFD / Ofício)

| Arquivo | Conteúdo |
|---------|----------|
| [geracao-documentos/00-INDICE.md](./geracao-documentos/00-INDICE.md) | Índice da pasta |
| [geracao-documentos/CHANGELOG-2026-06.md](./geracao-documentos/CHANGELOG-2026-06.md) | Changelog: setor DFD, tipografia, assinatura, deploy |
| [geracao-documentos/02-dfd-setor-requisitante.md](./geracao-documentos/02-dfd-setor-requisitante.md) | Correção `(DFD_SETOR_REQUISITANTE)` |
| [geracao-documentos/03-docx-tipografia-e-assinatura.md](./geracao-documentos/03-docx-tipografia-e-assinatura.md) | Justificação + 3 linhas antes do nome |
| [geracao-documentos/04-deploy-templates-docx.md](./geracao-documentos/04-deploy-templates-docx.md) | Build `rag_service` e templates na VPS |

---

## Serviços

| Arquivo | Conteúdo |
|---------|----------|
| [servicos/DOC_BACKEND.md](./servicos/DOC_BACKEND.md) | Django: APIs, views, multi-tenant |
| [servicos/DOC_RAG_SERVICE.md](./servicos/DOC_RAG_SERVICE.md) | RAG: ingestão, geração, análise |
| [servicos/DOC_LLM_API.md](./servicos/DOC_LLM_API.md) | Orquestração LLM (Ollama) |
| [servicos/DOC_LLM_AGENT.md](./servicos/DOC_LLM_AGENT.md) | Agente: estrutura, cláusulas |
| [servicos/DOC_CONFIG_AMBIENTE.md](./servicos/DOC_CONFIG_AMBIENTE.md) | Variáveis de ambiente |
| [servicos/ANALISE_DETALHADA_RAG_SERVICE.md](./servicos/ANALISE_DETALHADA_RAG_SERVICE.md) | Análise aprofundada do RAG |
| [servicos/MODULO_ANALISE_DOCUMENTOS.md](./servicos/MODULO_ANALISE_DOCUMENTOS.md) | Módulo de análise de conformidade |

---

## Integração

| Arquivo | Conteúdo |
|---------|----------|
| [integracao/API_FRONTEND_BACKEND.md](./integracao/API_FRONTEND_BACKEND.md) | Contratos API frontend ↔ Django |
| [integracao/AUTENTICACAO_DJANGO.md](./integracao/AUTENTICACAO_DJANGO.md) | Auth e sessões |
| [integracao/INTEGRACAO_DJANGO_LLM.md](./integracao/INTEGRACAO_DJANGO_LLM.md) | Fluxo Django → LLM/RAG |
| [integracao/DOCKER.md](./integracao/DOCKER.md) | Docker Compose local |
| [integracao/QWEN-INTEGRACAO-DOCMASTER.md](./integracao/QWEN-INTEGRACAO-DOCMASTER.md) | Qwen no DocMaster |

---

## Deploy e operação

Ver [deploy/README.md](./deploy/README.md).

---

## Fluxo típico de geração de documento

1. **Frontend** → `POST api/documentos/gerar-via-llm` (Django)
2. **Django** → `POST /api/rag/generate-document` (RAG)
3. **RAG** → LLM Agent (estrutura) + LLM API (texto) + ChromaDB (retrieval)
4. **RAG** → `tr_template` / `dfd_template` / `oficio_template` → DOCX
5. **Django** → FileResponse ao frontend

---

## Portas (desenvolvimento)

| Serviço | Porta |
|---------|-------|
| Django | 8000 |
| LLM API | 8002 |
| LLM Agent | 8003 |
| RAG Service | 8004 |

---

*Última atualização: jun/2026.*
