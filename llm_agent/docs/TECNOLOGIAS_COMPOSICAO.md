# Tecnologias para composição mais potente e robusta (llm_agent)

Sugestões de tecnologias e práticas que podem ser adicionadas ao **llm_agent** para tornar a geração de estruturas documentais mais potente, estável e auditável. Organizadas por objetivo.

---

## 1. Qualidade e confiabilidade da saída do LLM

| Tecnologia / prática | Benefício | Como usar no llm_agent |
|----------------------|-----------|-------------------------|
| **JSON mode / structured output** (Ollama, OpenAI, etc.) | O modelo devolve só JSON válido, reduzindo parse errors e retries. | Configurar no **llm_api** (ou no cliente do agente) para que a chamada ao modelo use `format: json` ou equivalente; alinhar o prompt ao schema esperado. |
| **JSON Schema no prompt** | O modelo recebe o schema exato da resposta (ex.: `section_keys` + `matches`); alguns modelos seguem melhor. | Em **prompts.py**, incluir o JSON Schema (ou um exemplo rígido) no system prompt; opcionalmente enviar via API se o backend suportar. |
| **Validação com Pydantic + retry com feedback** | Se a resposta falhar na validação, reenviar ao modelo com a mensagem de erro (“campo X obrigatório”) em vez de só retentar o mesmo prompt. | Em **agent.py**, em caso de `ValidationError`, construir um user follow-up com o erro e fazer uma segunda chamada (uma “rodada” de correção) antes do fallback. |
| **Modelos maiores ou especializados** | Melhor aderência a instruções e matching semântico (section_matches, intenção). | No **llm_api** ou no Ollama: usar um modelo com melhor instruction-following; ou rota por tipo de tarefa (interpretador vs. seleção). |

---

## 2. Cache e desempenho

| Tecnologia / prática | Benefício | Como usar no llm_agent |
|----------------------|-----------|-------------------------|
| **Redis (ou in-memory)** | Cache de estrutura para o mesmo `(document_type, context hash)` evita nova chamada ao LLM. | Antes de `call_generate`, checar cache por chave (ex.: hash de document_type + context); em hit retornar `StructureResponse`; em miss chamar LLM e gravar no cache com TTL. |
| **TTL e invalidação** | Cache não fica obsoleto quando o registro de seções muda. | Ao atualizar o registro (`POST /registry`), invalidar cache (por prefixo ou global). TTL curto (ex.: 5–15 min) para equilibrar frescor e carga. |

---

## 3. Matching semântico (intenção ↔ seções)

| Tecnologia / prática | Benefício | Como usar no llm_agent |
|----------------------|-----------|-------------------------|
| **Embeddings (sentence-transformers, OpenAI, Ollama)** | Similaridade entre o pedido do usuário e `title`/`description` das seções; ranquear candidatas antes ou depois do LLM. | Opcional: pré-filtrar ou pós-validar **section_matches**. Gerar embedding do `user_prompt` e dos (title + description) das elegíveis; ranquear por similaridade; usar como hint no prompt ou para preencher/validar `section_matches`. |
| **RAG (vector store)** | Seções ou descrições indexadas; busca por similaridade para “qual seção cadastrada corresponde a este pedido?”. | Em fluxos futuros: índice de seções (key, title, description, categories); query = user_prompt; retornar top-k para o prompt ou para decisão híbrida (LLM + scores). |

---

## 4. Observabilidade e auditoria

| Tecnologia / prática | Benefício | Como usar no llm_agent |
|----------------------|-----------|-------------------------|
| **OpenTelemetry (tracing)** | Traces por request (interpretador → filtro → LLM → montagem); diagnóstico de latência e falhas. | Instrumentar **agent.py** e **client.py** com spans (ex.: `interpret_user_prompt`, `call_generate`, `filter_eligible_sections`); exportar para Jaeger, Tempo ou backend compatível. |
| **Log estruturado (structlog, loguru)** | Logs em JSON com contexto (request_id, document_type, retries, cache hit/miss). | Substituir ou envolver `print`/logging por structlog; incluir campos úteis para debug e auditoria (sem logar texto completo do usuário se houver PII). |
| **Métricas (Prometheus)** | Contadores e histogramas (requisições, latência, retries, fallbacks, cache hit rate). | Expor endpoint `/metrics` com métricas Prometheus (ex.: `llm_agent_requests_total`, `llm_agent_llm_latency_seconds`, `llm_agent_fallback_total`). |
| **Auditoria de prompt/response** | Rastreabilidade: qual prompt foi enviado e qual resposta bruta veio do LLM. | Já existe em **llm_api**; no llm_agent pode-se gravar em arquivo ou DB (com hash ou truncamento) o par (prompt_hash, response_hash, document_type, timestamp) para reprodução e análise. |

---

## 5. Resiliência e escala

| Tecnologia / prática | Benefício | Como usar no llm_agent |
|----------------------|-----------|-------------------------|
| **Circuit breaker (ex.: pybreaker)** | Se o llm_api estiver falhando muito, parar de chamar por um tempo e retornar fallback imediato. | Envolver `call_generate` em um circuit breaker; em “open” retornar estrutura mínima sem chamar o LLM. |
| **Timeout e retry com backoff** | Reduz impacto de picos de latência ou falhas transitórias. | **client.py** já tem timeout; adicionar retry com backoff exponencial (ex.: 2 tentativas com 1s e 2s) antes de subir `OrchestrationError`. |
| **Fila assíncrona (Celery, RQ, ou tarefas em background)** | Requisições pesadas não bloqueiam a API; usuário recebe um job_id e consulta o resultado depois. | Para fluxos opcionais “estrutura em background”: enfileirar job (document_type, context, user_prompt); worker chama `generate_structure`; endpoint de status/resultado retorna quando pronto. |

---

## 6. Registro e versionamento de seções

| Tecnologia / prática | Benefício | Como usar no llm_agent |
|----------------------|-----------|-------------------------|
| **Banco de dados (PostgreSQL + SQLAlchemy)** | Registro de seções versionado, consultas por tipo/categoria/escopo, sem depender de um único JSON. | Substituir ou complementar **sections_registry.json** por tabelas (catalog, section_entry, version); o agente carrega do DB (ou de um serviço que lê do DB) em vez de arquivo. |
| **API de catálogo** | Backend (ex.: Django) dono do cadastro; llm_agent consome catálogo via HTTP. | Endpoint externo `GET /api/catalog/sections?document_type=...&categoria=...`; llm_agent chama esse endpoint quando não recebe `sections_catalog` no body e não tem registro em arquivo (ou usa como fonte principal). |

---

## 7. Testes e regressão

| Tecnologia / prática | Benefício | Como usar no llm_agent |
|----------------------|-----------|-------------------------|
| **Testes de contrato (golden files)** | Garantir que, para um dado (document_type, context) e um registro fixo, a estrutura gerada contém seções esperadas (ex.: declaracao_viabilidade quando tipo_objeto=obra). | Testes pytest com payloads fixos e mock do `call_generate`; ou testes de integração com LLM real e “golden” JSON (atualizado quando a intenção mudar). |
| **Property-based (Hypothesis)** | Gerar muitos contextos e validar que a resposta sempre é DocumentStructure válida e que keys vêm do catálogo. | Hypothesis gera `StructureRequest` aleatórios (dentro de regras); para cada um, chamar `filter_eligible_sections` ou o fluxo completo (mock LLM) e verificar invariantes (keys no catálogo, sem keys inventadas). |

---

## 8. Orquestração de fluxo (multi-step)

| Tecnologia / prática | Benefício | Como usar no llm_agent |
|----------------------|-----------|-------------------------|
| **Fluxo em etapas (classificar → filtrar → selecionar)** | Separar “qual tipo de documento e qual categoria?” da “quais seções incluir?” pode melhorar precisão. | Primeiro chamada ao LLM: só classificar (document_type + categoria + tipo_objeto). Segunda: com elegíveis já filtradas, só ordenar/selecionar. Reduz carga no único prompt e permite regras determinísticas no meio. |
| **LangChain / LlamaIndex (opcional)** | Chains pré-definidas e integração com ferramentas (RAG, calculadora). | Se o projeto já usar: modelar “interpretador” e “seleção de seções” como links de uma chain; o llm_agent pode permanecer “manual” e só inspirar-se na lógica (interpretar → filtrar → pedir keys). |

---

## Priorização sugerida (curto → médio prazo)

1. **Curto prazo (alto impacto, pouco acoplamento)**  
   - JSON mode / structured output no llm_api.  
   - Retry com feedback de validação (uma rodada de correção).  
   - Cache (Redis ou in-memory) com TTL e invalidação no `POST /registry`.  
   - Log estruturado + métricas básicas (contagem de requests, fallbacks, latência).

2. **Médio prazo**  
   - Embeddings para enriquecer ou validar **section_matches**.  
   - Circuit breaker e retry com backoff no client.  
   - Testes de contrato e property-based para filtro e montagem da estrutura.  
   - Catálogo via API ou DB em vez de só JSON em arquivo.

3. **Quando houver RAG e composição de cláusulas**  
   - RAG para “qual seção corresponde a este pedido?”.  
   - Auditoria de prompt/response e tracing ponta a ponta.  
   - Fila assíncrona para geração pesada ou em lote.

Essas tecnologias podem ser adotadas de forma incremental sem reescrever o núcleo do llm_agent; a maioria integra ao redor do fluxo atual (interpretador → catálogo/registro → filtro → LLM seleção → montagem da estrutura).
