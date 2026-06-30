# Correção: `(DFD_SETOR_REQUISITANTE)`

O slot `dfd_setor_requisitante` alimenta o placeholder `(DFD_SETOR_REQUISITANTE)` (e legado `(SETOR REQUISITANTE)`) no `DFD_modelo_base.docx`, seção **2.1 — Setor requisitante**.

---

## Sintoma

No DFD gerado, o setor requisitante mostrava o valor de **«Qual setor/secretaria será atendido?»** — campo do bloco de objeto usado apenas no **prompt de cláusulas IA** — em vez do **Setor requisitante** preenchido em **Dados fixos** do drawer.

---

## Causa raiz

Duas fontes competiam pelo mesmo slot:

| Fonte | Campo UI | Chave | Uso correto |
|-------|----------|-------|-------------|
| Dados fixos | Setor requisitante | `fixoSetor` → `dfd_setor_requisitante` | **DFD 2.1** |
| Objeto / cláusulas IA | Qual setor/secretaria será atendido? | `objetoSetor` | **Somente prompt IA** |

O override de geração TR/DFD/Ofício incluía `dfd_setor_requisitante` a partir de `objetoSetor` em alguns fluxos, sobrescrevendo ou preenchendo incorretamente.

---

## Correção (frontend)

### Helper compartilhado

`frontend-vue/src/components/dispensa-art-75-ii/dispensaArt75iiShared.js`:

```javascript
export function dfdSetorRequisitanteFromDadosFixos(dadosFixos) {
  return String(dadosFixos?.fixoSetor || '').trim();
}

export function applyDfdSetorRequisitanteToSlotsOverride(slotsOverride, dadosFixos) {
  const setor = dfdSetorRequisitanteFromDadosFixos(dadosFixos);
  if (setor) slotsOverride.dfd_setor_requisitante = setor;
  return slotsOverride;
}
```

### Formulário normal (`DispensaArt75IINormalForm.vue`)

- `objetoSetor` permanece para montagem do prompt de cláusulas (`Setor/secretaria atendido: …`).
- `dfd_setor_requisitante` **removido** de `buildSlotsOverrideForGerarClausulas()`.
- Aplicado apenas em `buildSlotsOverrideForGerarDocumentos()` via `applyDfdSetorRequisitanteToSlotsOverride(o, dadosFixos)`.

### Formulário rápido (`DispensaArt75IIRapidaForm.vue`)

- Campo «Qual setor/secretaria…» **removido** da UI.
- Validação exige `fixoSetor` nos dados fixos.
- Prompt IA referencia `fixoSetor` diretamente.
- Override de documentos usa o mesmo helper.

### Drawer de dados fixos

`DispensaArt75IIDadosFixosDrawer.vue` — campo **Setor requisitante** (`ctx.fixoSetor`) é a fonte canônica.

---

## Correção (backend RAG)

### Sanitização defensiva

`rag_service/app/dfd_slot_sanitize.py`:

```python
def sanitize_dfd_setor_requisitante(value: str) -> str:
    """Remove valores que parecem rótulo de campo ou texto do prompt de cláusulas."""
```

Rejeita textos que contenham, entre outros:

- `qual setor/secretaria`
- `setor/secretaria atendido`
- `setor requisitante (unidade`

### Onde é aplicado

| Módulo | Momento |
|--------|---------|
| `dfd_template.py` | Substituição `(DFD_SETOR_REQUISITANTE)` e `(SETOR REQUISITANTE)` |
| `tr_slots_llm.py` | Merge final slots IA + override do frontend |

Protege contra valores legados já salvos em presets ou respostas da IA.

---

## Testes

```bash
cd rag_service
pytest tests/test_dfd_slot_sanitize.py -v
```

Casos cobertos: setor válido preservado; rótulo de formulário rejeitado; prefixo de prompt rejeitado; string vazia.

---

## Como validar manualmente

1. Abrir Dispensa Art. 75 II (normal ou rápida).
2. Em **Dados fixos**, preencher **Setor requisitante** (ex.: «Secretaria de Administração»).
3. No bloco objeto (normal), preencher **setor atendido** com valor **diferente** (ex.: «Secretaria de Saúde»).
4. Gerar DFD.
5. Na seção 2.1, deve aparecer **Secretaria de Administração**, não Saúde.

---

## Referências

- [01-slots-tr-dfd-oficio.md](./01-slots-tr-dfd-oficio.md) — mapeamento completo de slots DFD
- [CHANGELOG-2026-06.md](./CHANGELOG-2026-06.md) — resumo da sessão
