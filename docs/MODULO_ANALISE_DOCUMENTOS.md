# Módulo de Análise de Documentos – Lei 14.133

Design do analisador de documentos licitatórios (DOCX/PDF) contra a Lei 14.133/2021. Análise direta, sem enrolação, com foco em conformidade e pontos críticos.

---

## 1. Objetivo

Analisar documentos (ETP, DFD, TR, contratos, editais) e retornar:

- **Pontos importantes** do documento
- **Análise de conformidade** com a Lei 14.133/2021
- **O que está certo** e **o que está errado** (objetivo, direto)
- Suporte a documentos gerados pelo LLM e documentos externos

**Princípios:**

- Sem fluff, sem meta-comentários, sem “slop”
- Apenas análise direta
- Sem OCR (apenas documentos com texto nativo)

---

## 2. Fluxo

```
[Upload DOCX/PDF] → [Extração de texto] → [Seções/chunks] → para cada chunk:
  [RAG: busca Lei 14.133] → [LLM analisa chunk] → [agrega resultados]
→ [Resposta estruturada]
```

1. **Entrada**: Arquivo DOCX ou PDF (caminho ou upload)
2. **Extração**: `load_document_text()` (pypdf para PDF, docx2txt para DOCX)
3. **Chunking**: documento é dividido em seções (ou chunks de ~2,8k chars se sem seções)
4. **Por chunk**: RAG recupera Lei 14.133; LLM analisa; resultado parseado
5. **Agregação**: merge de pontos_importantes, acertos, erros (com deduplicação)
6. **Saída**: JSON com pontos importantes, conformidade, acertos, erros

Documentos grandes são analisados inteiramente, sem truncar.

---

## 3. Contrato da API

### Request

```
POST /api/rag/analyze-document
Content-Type: multipart/form-data ou application/json (com path)
```

| Campo      | Tipo   | Obrigatório | Descrição                          |
|-----------|--------|-------------|------------------------------------|
| file      | File   | sim*        | DOCX ou PDF                        |
| path      | string | sim*        | Caminho do arquivo (alternativa)   |
| top_k     | int    | não         | Trechos da lei a recuperar (default: 8) |

*Um de `file` ou `path` obrigatório.

### Response

```json
{
  "ok": true,
  "document_type": "etp",
  "sections_detected": ["objeto", "justificativa", "prazo", ...],
  "pontos_importantes": [
    "Objeto: coleta seletiva em 3 bairros",
    "Valor estimado: R$ 150.000",
    "Prazo: 12 meses"
  ],
  "conformidade_geral": false,
  "acertos": [
    "Objeto descrito claramente",
    "Prazo dentro do limite da Lei 14.133 (art. X)"
  ],
  "erros": [
    "Vigência de 24 meses excede limite para serviços (art. 98, § 2º)",
    "Garantia de proposta não mencionada"
  ],
  "observacoes": "Documento parcialmente em conformidade."
}
```

| Campo              | Tipo     | Descrição                                |
|--------------------|----------|------------------------------------------|
| document_type      | string   | etp, dfd, termo_referencia, contrato, outro |
| sections_detected  | list     | Seções identificadas no documento        |
| pontos_importantes | list     | Resumo objetivo (bullets)                |
| conformidade_geral | bool     | true = em conformidade, false = não      |
| acertos            | list     | O que está correto                       |
| erros              | list     | O que está incorreto/viola a lei         |
| observacoes        | string   | Comentário breve (opcional)              |

---

## 4. Prompt do analisador (estritamente enxuto)

```
ANALISE o documento abaixo em relação à Lei 14.133/2021 (Lei de Licitações e Contratos).

TRECHOS RELEVANTES DA LEI:
{context}

DOCUMENTO:
{document}

REGRAS:
- Responda APENAS em JSON válido. Sem intro, sem "Aqui está...", sem meta-comentários.
- pontos_importantes: até 8 bullets objetivos (o que o doc trata).
- acertos: lista do que está CORRETO conforme a lei (cite art. quando possível).
- erros: lista do que está ERRADO ou viola a lei (cite art. sempre).
- conformidade_geral: true SE não houver erros; false SE houver qualquer erro.
- observacoes: uma frase curta ou vazio.
- Nada mais. Sem fluff.
```

Formato esperado (JSON):

```json
{
  "pontos_importantes": ["...", "..."],
  "acertos": ["...", "..."],
  "erros": ["...", "..."],
  "conformidade_geral": false,
  "observacoes": "..."
}
```

---

## 5. Dependências

| Componente | Uso |
|------------|-----|
| `loaders.load_document_text` | Extração de texto DOCX/PDF |
| `document_classifier.extract_sections` | Detecção de seções (opcional para enriquecer) |
| `retrieval.retrieve` | Busca RAG Lei 14.133 |
| `retrieval.generate_answer` / LLM direto | Análise |

**Pré-requisito**: Lei 14.133 ingerida em `/data/treinamento/LEI_14_133/` com `document_type=lei`.

---

## 6. Arquivos

| Arquivo | Função |
|---------|--------|
| `rag_service/app/document_analyzer.py` | Lógica principal: extrair, recuperar, analisar |
| `rag_service/app/api.py` | Endpoint `POST /analyze-document` |
| `rag_service/app/schemas.py` | `AnalyzeDocumentRequest`, `AnalyzeDocumentResponse` |
| `docs/MODULO_ANALISE_DOCUMENTOS.md` | Este documento |

---

## 7. Integração com Django (futuro)

- Endpoint Django: `POST /api/documentos/analisar` que recebe upload, repassa ao rag_service e retorna o JSON.
- Frontend: tela de upload, exibição de acertos/erros em lista.

---

## 8. Limites e restrições

- **Sem OCR**: apenas PDFs e DOCX com texto nativo.
- **Tamanho**: limitar documento a ~50.000 caracteres para não estourar contexto LLM.
- **Lei 14.133**: módulo depende da ingestão da lei no RAG.
