# Ingestão do guia ETP/DFD/TR no RAG

Recomendações e instruções para usar o manual de licitações (1034 páginas) como base de conhecimento.

---

## Uso imediato – endpoint de ingestão

```bash
# Por path (arquivo no servidor):
curl -X POST http://localhost:8004/api/rag/ingest-manual -F "path=/data/treinamento/manual_licitacoes.pdf"

# Por upload:
curl -X POST http://localhost:8004/api/rag/ingest-manual -F "file=@manual.pdf"
```

Chunks são marcados com `document_type=guia` e `tipo_documento` (etp, dfd, termo_referencia, geral). O analisador recupera automaticamente trechos do manual como referência ao analisar documentos.

---

## 1. Vale a pena usar?

**Sim.** Um guia extenso sobre ETPs, DFDs e TRs tende a cobrir:

- O que cada documento deve conter
- Estrutura e fluxo de cada tipo
- Exemplos e boas práticas
- Como a lei se aplica na prática

Isso complementa o RAG atual (Lei 14.133 pura) com **orientação funcional**.

---

## 2. Estratégia de ingestão

### 2.1 Formato

- Se o guia for PDF: extrair texto com `pypdf` ou `pdfplumber`.
- Se houver índices ou sumário: aproveitar para gerar metadados (capítulos, seções).

### 2.2 Chunking

Evite chunks aleatórios de 500 caracteres.

- **Preferir:** dividir por seção/capítulo (ex.: "5. ETP – O que deve conter", "6. DFD – Fluxo").
- **Alternativa:** `RecursiveCharacterTextSplitter` com separadores `\n\n##`, `\n\n###`, `\n\n` e tamanho maior (ex.: 800–1200 chars) para manter parágrafos inteiros.

### 2.3 Metadados

Para cada chunk, incluir:

```python
metadata = {
    "document_type": "guia",           # distingue da lei
    "tipo_documento": "etp" | "dfd" | "termo_referencia" | "geral",
    "section": "objeto",               # se for possível inferir (objeto, justificativa, prazo...)
    "source_file": "guia_etp_dfd_tr.pdf",
    "page": 42,
}
```

Assim o RAG pode priorizar: ao analisar um ETP, buscar `where={"tipo_documento": "etp"}` ou `where={"document_type": "guia"}`.

### 2.4 Coleção

- **Opção A:** mesma coleção da lei, diferenciando por `document_type: "guia"` vs `"lei"`.
- **Opção B:** coleção separada `docmaster_guia` e fazer duas buscas (lei + guia) e concatenar o contexto.

---

## 3. Fluxo sugerido

1. Extrair texto do PDF (pypdf ou pdfplumber).
2. Identificar seções por padrões (ex.: "5. ETP", "5.1 Objeto", "6. DFD").
3. Criar chunks por seção com metadados (`tipo_documento`, `section`).
4. Ingerir com `document_type=guia` (ou coleção dedicada).
5. No analisador: recuperar trechos de `lei` **e** de `guia`, priorizando o guia para ETP/DFD/TR.

---

## 4. Alteração no analisador

Após ingerir o guia, ajustar `document_analyzer.py` para:

- Buscar também chunks com `document_type=guia` (ou na coleção do guia).
- Incluir esses trechos no `context` enviado ao LLM.
- O prompt já usa "CONTEXTO (Lei 14.133 e boas práticas)" – o guia passa a alimentar as boas práticas.

---

## 5. Cuidados

- **Atualização:** o guia pode desatualizar; ter uma política de reingestão periódica.
- **Tamanho:** 1034 páginas → muitos chunks. Ajuste `top_k` e filtros para não estourar contexto.
- **Qualidade da extração:** conferir se PDFs escaneados ou com muitas tabelas/figuras não geram texto quebrado.
