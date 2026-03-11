### Melhoria do campo “objeto” nos TR com slots

#### 1. Problema atual

- Em TR “por conta” (fluxo `document_generator`), o **objeto** sai:
  - longo, bem contextualizado e formal;
  - muito melhor do que no fluxo de **slots TR**.
- Em TR com slots (`fill_tr_slots_with_llm` / `tr_slots_llm.py`), o **objeto**:
  - às vezes sai **básico** (pouca informação) ou com **erro de contexto**;
  - isso não acontece com a **justificativa**, que costuma vir bem redigida.

**Causas principais:**

1. **Um único JSON para tudo**  
   - A LLM gera `objeto`, `justificativa`, `itens`, etc. de uma vez só.
   - Mesmo com regras fortes, a energia do modelo tende a ir mais para a justificativa (que o prompt manda ser “extensa e técnica”).

2. **Fallback e normalização agressivos do objeto**
   - `_normalize_objeto` reescreve objetos curtos/genéricos em uma cláusula padrão (“O objeto do presente TR é a aquisição de {base}…”).
   - Se o `llm_agent` der um objeto ruim ou o `user_prompt` for vago, o fallback “herda” esse erro e o transforma em uma frase formal, porém **conceitualmente pobre**.
   - Se o usuário manda um `objeto` fraco em `slots_override`, ele é aceito como está (sem reprocessar).

3. **Justificativa sem interferência**
   - A justificativa é praticamente `data["justificativa"].strip()`, sem normalização, sem fallback.
   - O system prompt exige texto longo, técnico, argumentativo → ela tende a sair boa.

---

#### 2. Como funciona o “TR por conta” (sem slots)

- O `document_generator` gera **cada seção separadamente**:
  - Obtém estrutura pelo `llm_agent`.
  - Para cada seção (incluindo OBJETO):
    - faz `retrieve()` no RAG com filtro por `document_type` (TR/ETP, etc.);
    - monta um prompt **focado só naquela seção**, com exemplos de cláusulas reais;
    - pede para LLM gerar o **texto completo da cláusula**.
- Resultado:
  - O objeto nasce em um fluxo **focado** nele, com exemplos RAG e sem fallback agressivo.

---

#### 3. Direção de correção para TR com slots

**Objetivo:** fazer o `objeto` do fluxo de slots se comportar mais como o do TR “por conta”.

##### 3.1. Duas etapas para `objeto`

1. **Etapa 1 – JSON de slots (como hoje)**
   - Continuar usando `fill_tr_slots_with_llm` para obter:
     - `justificativa`, `itens`, `dispensa`, `fiscal`, etc.
   - Tratar o `objeto` que vem nesse JSON como **rascunho**, não como resultado final.

2. **Etapa 2 – Geração dedicada de cláusula OBJETO**
   - Extrair do `document_generator` a lógica que gera cláusula de objeto em TR por conta e colocar numa função reutilizável, algo como:
     - `generate_tr_objeto_clause(user_prompt, context_from_agent, user_context, rag_docs) -> str`
   - Essa função:
     - usa RAG específico para cláusula OBJETO (filtro `document_type=termo_referencia`);
     - tem prompt só para o objeto, com exemplos reais;
     - não depende do objeto rascunho do JSON (pode, no máximo, usá‑lo como apoio).
   - No final de `fill_tr_slots_with_llm`, depois de `_dict_to_tr_slots`:
     - chamar `generate_tr_objeto_clause(...)`;
     - **sobrescrever `llm_slots.objeto`** com esse texto gerado;
     - só então aplicar `_merge_slots` com os overrides do usuário.

##### 3.2. Ajustar fallback e normalização

Enquanto a etapa 2 não estiver 100% pronta/usada, melhorar o comportamento atual:

- **Limitar fallback com `user_prompt`**
  - Só usar `user_prompt` como base se:
    - não houver texto útil em `context_from_agent.context.objeto`;
    - e se a nova função dedicada de objeto não estiver ativa.
  - Evitar transformar qualquer prompt curto em “cláusula padrão” automaticamente.

- **Tornar `_normalize_objeto` menos intrusivo**
  - Intervir apenas quando o objeto:
    - tiver menos de X caracteres (ex.: < 60) **e** menos de Y palavras (ex.: ≤ 3);  
    - ou contiver expressões proibidas (“conforme itens abaixo…”, etc.).
  - Se a LLM gerar um objeto já longo e coerente, apenas limpar pontuação final e menções a “itens abaixo”, sem reescrever tudo em um molde fixo.

- **Respeitar melhor o override do usuário**
  - Se `slots_override["objeto"]` vier preenchido, podemos:
    - ainda passar por `_normalize_objeto`, mas não cair em fallback com user_prompt;
    - ou opcionalmente adicionar um flag futuro para “objeto_override_raw” (sem normalização).

##### 3.3. RAG de objeto também no fluxo de slots

- Já foi iniciado no `tr_slots_llm.py`:
  - `retrieve()` com `where={"document_type": "termo_referencia"}` e
  - injeção em `_build_tr_slots_user_prompt` de:
    - “Exemplos de redação de OBJETO…”
- Para ficar alinhado com o TR por conta:
  - Reaproveitar exatamente a função de geração de cláusula objeto do `document_generator` (ou o mesmo padrão de prompt/exemplos), em vez de manter lógica duplicada.

---

#### 4. Resumo do que precisa ser feito depois

1. **Refatorar o gerador de OBJETO do TR completo** para uma função reutilizável (ex.: `generate_tr_objeto_clause`).
2. **Chamar essa função ao final de `fill_tr_slots_with_llm`**, sobrescrevendo `llm_slots.objeto`.
3. **Suavizar o fallback atual** que transforma `user_prompt` em objeto, usando o prompt apenas como último recurso.
4. **Deixar `_normalize_objeto` mais conservador**, atuando só em casos realmente triviais/genéricos.
5. Manter/aperfeiçoar o uso de **RAG com exemplos de cláusula de objeto** também no fluxo de slots.

Com isso, o `objeto` dos TR gerados via slots tende a ficar tão completo e formal quanto o dos TR gerados “por conta”, reduzindo textos básicos e erros de contexto.

