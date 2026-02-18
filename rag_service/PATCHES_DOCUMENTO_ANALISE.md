# Análise de Patches para Geração de Documentos

Documento gerado em: 2025-02-10  
Objetivo: Eliminar erros recorrentes identificados nos ETPs gerados.

---

## 1. Citações legais puras no texto narrativo

### Problema
Trechos de transcrição literal de artigos de lei aparecem como parágrafos de cláusula:
- "O contrato será regido pelas regras previstas na Lei 14.133/2021"
- "A Administração poderá optar por licitar de acordo com as leis citadas no inciso II do caput do artigo 193"
- "As hipóteses de cancelamento da ata de registro de preços..."
- "A contratação posterior de item específico constante de grupo de itens exigirá prévia pesquisa de mercado..."
- "O descumprimento das determinações constantes no presente artigo ensejará a apuração de responsabilidade"

### Patches necessários

#### 1.1 RAG: Expandir `_mark_pure_legal_citations_in_rag`
**Arquivo:** `document_generator.py`  
**Função:** `_mark_pure_legal_citations_in_rag`  
**Ação:** Incluir mais frases em `legal_phrases`:
```python
legal_phrases = (
    "vedada a aplicação combinada",
    "será regido pelas regras",
    "inciso II do caput",
    "indicadas expressamente no edital",
    # Novos:
    "hipóteses de cancelamento da ata",
    "contratação posterior de item específico",
    "prévia pesquisa de mercado",
    "descumprimento das determinações",
    "presente artigo ensejará",
    "ata de registro de preços",
)
```
**E:** Relaxar condição – marcar também trechos que contenham 2+ dessas frases mesmo sem começar com "Art." (chunks podem vir truncados).

#### 1.2 Pós-processamento: Remover parágrafos de citação legal pura
**Arquivo:** `document_generator.py`  
**Função:** `_postprocess_clause_text`  
**Ação:** Novo bloco que remove parágrafos inteiros que são claramente citação legal:
- Padrões: frases que começam com "O contrato será regido...", "As hipóteses de cancelamento...", "A contratação posterior de item específico...", "O descumprimento das determinações constantes no presente artigo..."
- Regex por frase ou lista de padrões iniciais; remover o parágrafo completo.

---

## 2. "Art. X." e "presente artigo" em ETP/estudos

### Problema
- "Art. 123. A Administração considerará..." – ETP não tem artigos; é linguagem de lei/contrato
- "presente artigo" em texto de estudo técnico

### Patches necessários

#### 2.1 Pós-processamento: Remover "Art. N. " no início de parágrafo
**Arquivo:** `document_generator.py`  
**Função:** `_postprocess_clause_text`  
**Ação:**
```python
# Remove "Art. 123. " no início de parágrafo (ETP/estudo não usa artigos)
t = re.sub(r"^Art\.?\s*\d+\.\s+", "", t, flags=re.MULTILINE)
# OU converter em "Conforme art. X da Lei 14.133/2021," quando fizer sentido
# Política: em ETP, remover; o texto continua sem o "Art. X."
```

#### 2.2 Pós-processamento: Substituir "presente artigo"
**Ação:** Substituir "no presente artigo" / "do presente artigo" por "nesta seção" ou "neste documento" quando o contexto for estudo/ETP. Ou aplicar sempre (é mais seguro para ETP).

#### 2.3 Instrução por seção: Conclusão
**Função:** `_get_section_specific_instructions`  
**Ação:** Adicionar bloco para `conclusao` / `conclusão`:
```python
if "conclus" in key:
    return "\nINSTRUÇÕES: ETP/estudo NÃO usa numeração de artigos (Art. 123). Redija em prosa. NUNCA use 'presente artigo' ou 'neste artigo' – use 'nesta seção' ou 'neste documento'.\n"
```

---

## 3. Tabelas embutidas em prosa

### Problema
- Linhas como "1. Fornecimento de equipamentos – 10 – R$ 1.000,00 – R$ 10.000,00" em meio a texto
- "1. Item 2. Quantidade 3. Valor Unitário 4. Total" – cabeçalhos de tabela como lista numerada

### Patches necessários

#### 3.1 Prompt: Reforçar proibição de tabela em prosa
**Arquivo:** `document_generator.py`  
**Constante:** `CLAUSE_COMPOSITION_SYSTEM_PROMPT`  
**Ação:** Reforçar regra 9:
```
9. NUNCA insira linhas de tabela (Item – Quantidade – Valor – Total) em texto de cláusula. 
   Tabelas são seções separadas. Para mencionar estimativa de custos, diga apenas "conforme tabela na seção correspondente" ou "conforme tabela de estimativa de custos anexa". 
   NUNCA liste colunas (Item, Quantidade, Valor Unitário, Total) como itens numerados.
```

#### 3.2 Pós-processamento: Detectar e remover linhas-tabela
**Função:** `_postprocess_clause_text`  
**Ação:** Detectar linhas que parecem linha de tabela:
- Padrão: `N. Texto – número – R$ X – R$ Y` (ex.: "1. Caminhões – 2 – R$ 50.000,00 – R$ 100.000,00")
- Padrão: "1. Item 2. Quantidade 3. Valor Unitário 4. Total" – remover ou substituir por "Conforme tabela na seção correspondente."
- Política: se a linha contiver 2+ valores em R$ e estrutura " – número – R$ – R$", tratar como tabela inline e remover, deixando nota "A estimativa de custos consta na tabela da seção correspondente." (uma vez por seção)

---

## 4. Typos (correção automática)

### Problema
- "acatuladoras" → "acautelatórias"

### Patch
**Arquivo:** `document_generator.py`  
**Função:** `_postprocess_clause_text`  
**Ação:** Incluir em `fixes`:
```python
(r"\bacatuladoras\b", "acautelatórias"),
(r"\bacatulador\b", "acautelatório"),
```

---

## 5. Remoção de parágrafos de citação legal (lista de padrões)

### Patch consolidado
**Função:** `_postprocess_clause_text`  
**Ação:** Criar lista de padrões de parágrafos a remover (citação legal pura):

```python
LEGAL_BOILERPLATE_PARAGRAPHS = [
    r"^O contrato (?:será|será) regido pelas regras (?:previstas|da) (?:na )?Lei[^.]*\.?\s*",
    r"^A Administração poderá optar por licitar de acordo com as leis citadas[^.]*\.?\s*",
    r"^As hipóteses de cancelamento da ata de registro de preços[^.]*\.?\s*",
    r"^A contratação posterior de item específico constante de grupo[^.]*\.?\s*",
    r"^O descumprimento das determinações constantes no presente artigo[^.]*\.?\s*",
    r"^É vedada a aplicação combinada desta Lei[^.]*\.?\s*",
]
# Para cada padrão: remover o parágrafo (até o ponto final)
```

Implementação: percorrer parágrafos (split por `\n\n`), para cada um verificar se matches algum padrão; se sim, remover.

---

## 6. Instruções por seção – complementos

### 6.1 Conclusão
Adicionar instruções para não usar Art., presente artigo, e evitar transcrição de lei.

### 6.2 Objeto / Estimativa
Reforçar: "NÃO inclua linhas de tabela (Item, Quantidade, Valor, Total) no texto. A tabela será em seção própria."

### 6.3 Conformidade
Adicionar: "NÃO liste 'Item, Quantidade, Valor Unitário, Total' como itens numerados – isso é estrutura de tabela, não de lista."

### 6.4 Solução Proposta
Adicionar: "NÃO inclua linhas de tabela de custos no texto. Mencione apenas 'conforme tabela na seção correspondente'."

---

## 7. Sanitização LLM – expandir escopo

### Problema
O `LLM_SANITIZE_PROMPT` atual remove intros e meta-comentários. Pode ser expandido para também pedir remoção de:
- Parágrafos que são transcrição literal de artigos de lei
- Frases que começam com "Art. N. "

### Patch
**Constante:** `LLM_SANITIZE_PROMPT`  
**Ação:** Adicionar ao texto do prompt:
```
Remova também: parágrafos que são transcrição literal de artigos de lei (ex.: "O contrato será regido pelas regras...", "As hipóteses de cancelamento da ata..."); e o prefixo "Art. 123. " no início de parágrafos (o documento não usa numeração de artigos).
```

---

## 8. Resumo da ordem de implementação

| # | Patch | Prioridade | Complexidade |
|---|-------|------------|--------------|
| 1 | Typos (acatuladoras) | Alta | Baixa |
| 2 | Remover "Art. N. " no início de parágrafo | Alta | Baixa |
| 3 | Expandir legal_phrases em _mark_pure_legal_citations_in_rag | Alta | Baixa |
| 4 | Remover parágrafos de citação legal no pós-processamento | Alta | Média |
| 5 | Instruções Conclusão, Objeto, Conformidade, Solução | Alta | Baixa |
| 6 | Reforçar prompt contra tabelas inline | Alta | Baixa |
| 7 | Pós-processamento: remover linhas-tabela inline | Média | Média |
| 8 | Expandir LLM_SANITIZE_PROMPT | Média | Baixa |
| 9 | Substituir "presente artigo" por "nesta seção" | Média | Baixa |

---

## 9. Arquivos afetados

- `rag_service/app/document_generator.py` (único arquivo a modificar)

## 10. Testes sugeridos

Após aplicar patches:
1. Gerar ETP para "coleta seletiva" e verificar ausência de: Art. 123, "presente artigo", citações legais puras, tabelas inline, "acatuladoras".
2. Gerar ETP para outro objeto e validar que a Conclusão não começa com "Art.".
3. Verificar que a seção Conformidade não contém "1. Item 2. Quantidade 3. Valor Unitário 4. Total".
