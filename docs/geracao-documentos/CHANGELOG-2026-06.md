# Changelog — geração de documentos (jun/2026)

Registro das alterações feitas na sessão de correções TR/DFD/Ofício (Dispensa Art. 75, II e pacotes `lei_14133`). Todas as correções abaixo foram **aplicadas no repositório**, **testadas localmente** e **validadas em produção** pelo usuário (assinatura) após rebuild do `rag_service`.

---

## 1. `(DFD_SETOR_REQUISITANTE)` com valor errado

### Problema

O placeholder `(DFD_SETOR_REQUISITANTE)` no DFD recebia o valor do campo **«Qual setor/secretaria será atendido?»** (`objetoSetor`), usado no prompt de cláusulas IA — e não o **Setor requisitante** dos **Dados fixos** (`fixoSetor`).

### Solução aplicada

| Camada | O que mudou |
|--------|-------------|
| **Frontend** | `dfd_setor_requisitante` preenchido **somente** via `applyDfdSetorRequisitanteToSlotsOverride()` → `dadosFixos.fixoSetor`. Removido de `buildSlotsOverrideForGerarClausulas()` no formulário normal. |
| **Dispensa rápida** | Removido campo «Qual setor/secretaria…»; validação exige `fixoSetor` no drawer; prompt IA usa `fixoSetor`. |
| **Backend RAG** | `sanitize_dfd_setor_requisitante()` em `dfd_slot_sanitize.py` descarta rótulos de formulário ou texto espúrio; usado em `dfd_template.py` e `tr_slots_llm.py`. |
| **Shared JS** | `dispensaArt75iiShared.js` centraliza `dfdSetorRequisitanteFromDadosFixos` e `applyDfdSetorRequisitanteToSlotsOverride`. |

### Status

**Corrigido e em uso.** Ver [02-dfd-setor-requisitante.md](./02-dfd-setor-requisitante.md).

---

## 2. Justificativa «fantasma» (texto à esquerda indevido)

### Problema

Após geração, parágrafos de justificativa longa ficavam alinhados à **esquerda** em vez de **justificado**. A heurística `paragraph_should_remain_left_aligned()` em `docx_typography.py` tratava blocos longos que continham «Manutenção preventiva» + «corretiva» como lista romana.

### Solução aplicada

- `apply_default_justify_to_document()` **não sobrescreve** parágrafos já com alinhamento explícito (justificado, centro, direita).
- Heurísticas de lista romana mais restritas (linhas curtas, padrão `I –` no início).
- Bloco **§15.1** (instrumento de contrato) permanece à esquerda mesmo em parágrafo longo do modelo.
- Testes em `rag_service/tests/test_docx_typography.py`.

### Status

**Corrigido.** Justificativas longas permanecem justificadas; §15.1 e itens romanos curtos à esquerda.

---

## 3. Espaçamento da assinatura (5 linhas em vez de 3)

### Problema

Entre a linha **cidade/data** e o **nome do assinante** (`TR_NOME_ASSINANTE_TERMO`, `DFD_NOME_ASSINATURA`, `SOL_OFICIO_RESPONSAVEL_NOME`) apareciam **5 linhas vazias** em vez de **3**.

Causas identificadas:

1. O modelo `TR_modelo_base.docx` (compras) já tinha **5** parágrafos vazios entre o marcador do nome e a cidade.
2. Com data **«datado e assinado digitalmente»**, a detecção da linha cidade/data falhava (exigia ano com 4 dígitos) e `ensure_signature_nome_blank_lines()` **não executava** a normalização.

### Solução aplicada

Função `ensure_signature_nome_blank_lines()` em `docx_typography.py`, chamada ao **final** do render em:

- `tr_template.py`
- `dfd_template.py`
- `oficio_template.py`

Comportamento:

1. Localiza parágrafo do **nome** (marcador ou estrutura cidade → vazios → nome).
2. Âncora = último parágrafo com texto antes do bloco de vazios (cidade/data).
3. Remove **todos** os parágrafos vazios entre âncora e nome.
4. Insere **exatamente 3** parágrafos vazios antes do nome.
5. Zera `space_before` / `space_after` nos vazios do gap (evita «linhas fantasma» no Word).

Detecção cidade/data estendida para:

- «datado e assinado digitalmente»
- Padrão `Cidade - UF, …` sem ano obrigatório

Testes: `rag_service/tests/test_signature_nome_spacing.py` (6 casos, incluindo render TR completo com data digital).

### Esclarecimento de layout

O modelo TR mantém **2 linhas vazias** entre o §25.1 e a cidade/data — isso é **separado** da regra dos 3 vazios **entre cidade e nome**. O usuário pode ver 2+3=5 linhas no total visual antes do nome; o bug era ter 5 **entre** cidade e nome.

### Status

**Corrigido e confirmado em produção** após rebuild do `rag_service`.

---

## 4. Deploy de templates e código na VPS

### Problema

`git pull` + `docker compose up --force-recreate` **sem** `build` mantinha DOCX antigos na imagem (templates copiados no `Dockerfile` do `rag_service`).

### Procedimento validado

```bash
cd ~/docmaster-core && git pull
cd ~
docker compose build rag_service frontend-vue   # frontend se houve mudança Vue
docker compose up -d --force-recreate rag_service frontend-vue
```

Verificação rápida no container:

```bash
docker exec rag_service sh -c 'PYTHONPATH=/app python -c "from rag_service.app.docx_typography import ensure_signature_nome_blank_lines; print(\"ok\")"'
```

### Status

**Documentado** em [04-deploy-templates-docx.md](./04-deploy-templates-docx.md).

---

## Resumo de arquivos alterados

| Arquivo | Alteração |
|---------|-----------|
| `rag_service/app/docx_typography.py` | Justificação + assinatura |
| `rag_service/app/dfd_slot_sanitize.py` | Novo — sanitização setor |
| `rag_service/app/dfd_template.py` | Sanitize + assinatura |
| `rag_service/app/tr_template.py` | Assinatura no final |
| `rag_service/app/oficio_template.py` | Assinatura no final |
| `rag_service/app/tr_slots_llm.py` | Sanitize setor no merge |
| `frontend-vue/.../DispensaArt75IINormalForm.vue` | Setor só de dados fixos |
| `frontend-vue/.../DispensaArt75IIRapidaForm.vue` | Idem + remoção campo setor IA |
| `frontend-vue/.../dispensaArt75iiShared.js` | Helpers centralizados |
| `rag_service/tests/test_*.py` | Cobertura tipografia, assinatura, sanitize |

---

*Última atualização: 22/jun/2026.*
