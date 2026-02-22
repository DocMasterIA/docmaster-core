# Análise e arquitetura: TR modelo como base de geração (só partes entre parênteses)

Documento analisado: `Termo de Referencia modelo IA (1).docx`  
Objetivo: usar o DOCX como **template base** e alterar apenas as partes marcadas entre `( )` via LLM/usuário.

---

## 1. Análise do documento

### 1.1 Estrutura

O TR segue o padrão de Termo de Referência com **~97 parágrafos** e **17 seções** principais:

| # | Seção |
|---|--------|
| 1 | TERMO DE REFERÊNCIA (título) |
| 2 | DO OBJETO |
| 3 | DAS ESPECIFICAÇÕES (tabela: Item, Descrição, Unidade, Quantidade) |
| 4 | DA JUSTIFICATIVA |
| 5 | MODELO DE GESTÃO DO CONTRATO |
| 6 | CLASSIFICAÇÃO DO OBJETO CONTRATUAL |
| 7 | MÉTODO E ESTRATÉGIAS DE SUPRIMENTO |
| 8 | DA GARANTIA |
| 9 | DA AVALIAÇÃO DO CUSTO |
| 10 | DAS OBRIGAÇÕES DA CONTRATADA |
| 11 | DAS OBRIGAÇÕES DA CONTRATANTE |
| 12 | MEDIDAS ACAUTELADORAS |
| 13 | DO ACOMPANHAMENTO E FISCALIZAÇÃO |
| 14 | DA FORMA DE PAGAMENTO |
| 15 | DAS SANÇÕES |
| 16 | DOTAÇÃO ORÇAMENTÁRIA |
| 17 | DOS REQUISITOS NECESSÁRIOS PARA HABILITAÇÃO |
| + | RECEBIMENTOS DAS PROPOSTAS, FORMAS DE SUBMISSÃO, DISPOSIÇÕES FINAIS |

### 1.2 Placeholders identificados (partes a preencher)

**Placeholders “chave”** – instrução explícita para o usuário/IA preencher:

| Placeholder | Seção / contexto | Tipo |
|-------------|-------------------|------|
| `(descrever o objeto solicitado)` | DO OBJETO | texto livre |
| `(descrever o artigo de acordo com objeto)` | Dispensa (art. 75) | texto/inciso |
| `(Descrever o item de acordo com o solicitado)` | Especificações (tabela) | por item |
| `(Inserir unidade de medida ex: caixa, litro, unidade etc)` | Especificações | unidade |
| `(Inserir quantidade solicitada)` | Especificações | número |
| `(Formalizar justificava de acordo com objeto solicitado)` | DA JUSTIFICATIVA | texto livre |
| `(Inserir o inciso de acordo com o objeto solicitado)` | Classificação | inciso |
| `(inserir nome do fiscal)` | Fiscalização | nome |
| `(Inserir Dotação)` / `(Feito direto pelo usuário)` | Dotação orçamentária | dotação |

**Outros** entre parênteses no corpo (ex.: `(trinta)`, `(CNDT)`) são **numeração por extenso** ou siglas, não “campos” a substituir – podem ser tratados como texto fixo ou normalização opcional.

### 1.3 Conclusão da análise

- O documento é um **template estável**: a maior parte é cláusula fixa (Lei 14.133, obrigações, sanções, etc.).
- Apenas **9 placeholders chave** precisam ser preenchidos por objeto/solicitação.
- Há uma **tabela** (Especificações: Item, Descrição, Unidade, Quantidade) com linhas repetíveis e placeholders por linha.
- O cliente quer **só mudar o que está entre ( )**, mantendo o resto do arquivo igual.

---

## 2. Arquitetura proposta: TR modelo como base de geração

### 2.1 Ideia geral

1. **Template base**: o DOCX do modelo é armazenado e tratado como “estrutura + texto fixo”.
2. **Extração de slots**: identificar todos os trechos `( ... )` e classificar em “preencher por IA/usuário” vs “manter/numeração”.
3. **Geração só dos slots**: a LLM (ou formulário) preenche apenas os placeholders chave; o resto do DOCX não é reescrito.
4. **Montagem**: substituir no documento (ou em uma cópia) cada placeholder pelo valor gerado e entregar o DOCX final.

### 2.2 Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│  TR Modelo (DOCX)                                               │
│  - Upload/armazenamento do template                             │
│  - Parse: extrair parágrafos + tabelas + listar (placeholder)   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Módulo de extração de slots                                    │
│  - Regex/parse DOCX: localizar (texto)                          │
│  - Classificar: key_slot (descrever/inserir/formalizar) vs fixo │
│  - Output: lista { slot_id, placeholder_text, section, tipo }   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Entrada do usuário / contexto                                  │
│  - Objeto da contratação (ex.: "aquisição de material de       │
│    escritório")                                                 │
│  - Opcionais: dotação, nome do fiscal, quantitativos          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Geração por slot (LLM)                                         │
│  - Para cada key_slot: prompt com contexto (objeto + seção)     │
│  - Ex.: "Preencha o objeto do TR: (descrever o objeto...)      │
│    Objeto informado: aquisição de material de escritório"      │
│  - Resposta curta, sem repetir o resto do documento             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Montagem do DOCX final                                         │
│  - Copiar template base                                         │
│  - Substituir cada (placeholder) pelo valor gerado              │
│  - Preservar formatação/tabelas (python-docx ou substituição   │
│    em XML/parágrafos)                                           │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Fluxo por etapa

| Etapa | Onde pode ficar | Descrição |
|-------|------------------|-----------|
| 1. Armazenar modelo | Django + storage | Um “TR modelo” (este DOCX) cadastrado como template base. |
| 2. Extrair slots | rag_service ou backend | Script/função que abre o DOCX, percorre parágrafos e tabelas, extrai `( ... )` e classifica (key_slot vs fixo). |
| 3. Listar slots para UI | Backend API | Endpoint que devolve lista de placeholders chave (e opcionalmente seção). Usuário pode preencher manual ou “gerar com IA”. |
| 4. Gerar valores dos slots | LLM (llm_api/rag) | Por slot: prompt com “objeto da contratação” + instrução do placeholder. Uma chamada por slot ou um único prompt estruturado (JSON) com todos os campos. |
| 5. Substituir e gerar DOCX | Backend | Copiar DOCX modelo e substituir cada `(placeholder)` pelo valor (atenção a tabelas: mesma célula pode ter placeholder). Entregar DOCX para download. |

### 2.4 Detalhes importantes

- **Tabela de especificações**: linhas com “Item 01”, “Item 02” e placeholders em Descrição/Unidade/Quantidade. Opções: (a) tratar cada célula com `( ... )` como um slot; (b) LLM gerar “N itens” e o backend preencher N linhas da tabela.
- **Substituição no DOCX**: em DOCX, o mesmo parágrafo pode estar em vários `<w:t>`. É preciso localizar o texto `(descrever...)` no XML e substituir preservando o run, ou usar python-docx substituindo em cada paragraph/cell.
- **Placeholders fixos**: `(trinta)`, `(CNDT)` etc. podem ficar como estão ou ser normalizados por regras (ex.: “(trinta)” → “trinta” se quiser padronizar). Não precisam de LLM.
- **Dotação / nome do fiscal**: podem vir do contexto do usuário (formulário ou perfil) em vez de LLM.

### 2.5 Integração com o fluxo atual

- **Geração “do zero” (structure-from-prompt)**: continua gerando ETP/DFD/TR completos a partir do prompt.
- **Geração “a partir do modelo”**: novo fluxo opcional:
  - Usuário escolhe “TR modelo IA” como base.
  - Informa o objeto (e opcionais).
  - Backend extrai slots do DOCX modelo, chama LLM só para os key_slots, monta o DOCX e devolve.

Assim, o documento analisado vira **base de geração** apenas nas partes entre parênteses, sem alterar o resto do arquivo.

---

## 3. Próximos passos sugeridos

1. **Implementar extrator de slots** no backend ou rag_service: dado um DOCX, retornar lista de `(placeholder)` com seção e classificação (key_slot ou fixo).
2. **Definir contrato da API**: ex. `POST /api/documentos/gerar-tr-do-modelo` com `template_id`, `objeto`, `contexto` e opcionalmente valores parciais por slot.
3. **Implementar geração por slot**: chamada(s) à LLM para preencher só os key_slots.
4. **Implementar montagem**: substituição no DOCX (python-docx ou XML) e retorno do arquivo final.

Se quiser, na próxima etapa podemos detalhar a API e o formato de resposta do extrator de slots (ex. JSON com `slot_id`, `placeholder`, `section`, `suggested_value`).
