# Evolução Futura: Revisor Semântico Controlado por IA

## Objetivo

Adicionar uma camada de revisão semântica e estilística para textos de licitação (ETP, TR, DFD), mantendo:
- fidelidade ao conteúdo original;
- conformidade com linguagem técnico-administrativa;
- proibição de invenção de fatos, números e base legal.


## Problema Atual

O fluxo atual (LanguageTool + regras determinísticas) cobre bem ortografia e gramática local, mas pode deixar passar:
- incoerências semânticas de frases longas;
- combinações formais com regência inadequada;
- estilo institucional inconsistente;
- mistura indevida de conteúdo entre seções.


## Proposta de Arquitetura (Híbrida)

1. **Pré-correção técnica (já existente)**
   - normalize_text
   - LanguageTool (passada 1)
   - dicionário OCR/erro comum
   - LanguageTool (passada 2)
   - post_rules determinísticas

2. **Revisor semântico controlado (novo)**
   - chamada a LLM com prompt estrito de revisão (sem reescrever o documento do zero);
   - modo por tipo: `tr`, `etp`, `dfd`, `generic`;
   - política de segurança: se houver violação, descartar resposta e manter texto anterior.

3. **Validador de segurança pós-LLM (novo)**
   - bloqueia mudanças que:
     - introduzam leis/artigos não presentes no texto de entrada;
     - alterem valores numéricos, datas e quantitativos sem autorização;
     - removam nomes de órgãos, objeto principal ou escopo essencial.

4. **Retorno com rastreabilidade**
   - `revised_text`
   - `change_summary` (resumo das mudanças)
   - flags de conformidade (`safe_revision`, `semantic_review_applied`).


## Prompt Base (Revisor Controlado)

Regras recomendadas para o prompt do revisor:
- Corrigir semântica, coesão, concordância e estilo formal.
- Preservar integralmente o sentido jurídico-administrativo.
- Não inventar fatos, leis, artigos, valores, prazos ou entidades.
- Não remover requisitos essenciais do objeto/justificativa.
- Se não houver melhoria segura, retornar o texto original.


## Guardrails Recomendados

- **Diff gate por risco**:
  - rejeitar revisão com alteração excessiva (ex.: > 25% de tokens alterados).
- **Gate numérico**:
  - rejeitar se números/valores/datas mudarem sem autorização explícita.
- **Gate legal**:
  - rejeitar citação de artigo/inciso não presente na entrada.
- **Gate de seção**:
  - em `solucao_proposta`, bloquear inserção de blocos de `analise_riscos`.


## Endpoints Sugeridos

- `POST /semantic-review`
  - entrada: `text`, `mode`, `strict=true|false`
  - saída: `revised_text`, `applied`, `warnings`, `change_summary`

- `POST /correct` (evolução opcional)
  - adicionar parâmetro `semantic_review=true|false`
  - manter default `false` para rollout progressivo.


## Rollout Seguro

Fase 1 (shadow mode):
- executar revisão semântica em paralelo, sem alterar saída final;
- registrar diff e métricas.

Fase 2 (opt-in):
- habilitar por flag para ETP/TR em ambiente de teste.

Fase 3 (produção gradual):
- ativar por percentual (10% -> 50% -> 100%) com monitoramento.


## Métricas de Qualidade

- taxa de aceitação do revisor semântico;
- taxa de rollback por guardrail;
- redução de erros de regência/coerência reportados por usuários;
- tempo médio adicional por documento;
- taxa de alteração indevida evitada pelos gates.


## Configurações Futuras (ENV)

- `SEMANTIC_REVIEW_ENABLED=0|1`
- `SEMANTIC_REVIEW_STRICT=0|1`
- `SEMANTIC_REVIEW_MAX_TOKEN_DELTA=0.25`
- `SEMANTIC_REVIEW_TIMEOUT=60`
- `SEMANTIC_REVIEW_MODEL=<modelo>`


## Critério de Sucesso

Considerar sucesso quando:
- houver queda perceptível de erros semânticos em ETP/TR/DFD;
- não houver aumento de invenção legal/factual;
- o tempo de geração permanecer aceitável para uso interativo.

