# Prompts para testar o llm_agent

Base URL: **http://localhost:8003** (ajuste se usar outra porta). Requisito: **llm_api** rodando (ex.: porta 8002) e **sections_registry.json** acessível para fluxo com catálogo.

---

## 1. POST /api/agent/structure-from-prompt

Envia um **texto livre**; o agente interpreta (tipo + contexto) e gera a estrutura. Quando há registro, a resposta pode incluir **section_matches** (correspondência pedido ↔ seção com nível de certeza).

### 1.1 Termo de referência (genérico)

```bash
curl -s -X POST http://localhost:8003/api/agent/structure-from-prompt \
  -H "Content-Type: application/json" \
  -d '{"user_prompt": "Preciso de um termo de referência para contratação de serviços de TI para a Secretaria de Educação, pregão eletrônico."}' | jq .
```

**Prompt (texto):**
> Preciso de um termo de referência para contratação de serviços de TI para a Secretaria de Educação, pregão eletrônico.

---

### 1.2 ETP com “cláusula sobre viabilidade” (testa section_matches)

O registro tem a seção **Declaração de Viabilidade** com `description` que inclui “cláusula de viabilidade”. Este prompt deve gerar estrutura ETP e, se o contexto permitir (ex.: obra/serviço continuado), incluir essa seção e preencher **section_matches** com alta confiança.

```bash
curl -s -X POST http://localhost:8003/api/agent/structure-from-prompt \
  -H "Content-Type: application/json" \
  -d '{"user_prompt": "Quero um estudo técnico preliminar para obra de reforma, com cláusula sobre viabilidade da contratação."}' | jq .
```

**Prompt (texto):**
> Quero um estudo técnico preliminar para obra de reforma, com cláusula sobre viabilidade da contratação.

---

### 1.3 ETP – redação diferente (“informação de viabilidade”)

Testa matching por intenção mesmo com outro wording.

```bash
curl -s -X POST http://localhost:8003/api/agent/structure-from-prompt \
  -H "Content-Type: application/json" \
  -d '{"user_prompt": "Estudo técnico preliminar para serviço continuado de manutenção. Preciso da informação de viabilidade e da estimativa de custos."}' | jq .
```

**Prompt (texto):**
> Estudo técnico preliminar para serviço continuado de manutenção. Preciso da informação de viabilidade e da estimativa de custos.

---

### 1.4 Termo de referência – objeto e modalidade

```bash
curl -s -X POST http://localhost:8003/api/agent/structure-from-prompt \
  -H "Content-Type: application/json" \
  -d '{"user_prompt": "Termo de referência para aquisição de medicamentos para a rede municipal de saúde, dispensa de licitação."}' | jq .
```

**Prompt (texto):**
> Termo de referência para aquisição de medicamentos para a rede municipal de saúde, dispensa de licitação.

---

### 1.5 Pedido vago (testa fallback do interpretador)

```bash
curl -s -X POST http://localhost:8003/api/agent/structure-from-prompt \
  -H "Content-Type: application/json" \
  -d '{"user_prompt": "Documento para licitação."}' | jq .
```

Esperado: interpretador tende a devolver algo como termo_referencia com objeto genérico; estrutura mínima ou do catálogo conforme registro.

---

## 2. POST /api/agent/structure

Envia **document_type** e **context** (e opcionalmente **sections_catalog**). Útil para testar filtro por **extras** (tipo_objeto, categoria).

### 2.1 ETP + obra (seção condicional “Declaração de Viabilidade” entra)

O registro só inclui **declaracao_viabilidade** quando `extras.tipo_objeto` é `"obra"` ou `"servico_continuado"`.

```bash
curl -s -X POST http://localhost:8003/api/agent/structure \
  -H "Content-Type: application/json" \
  -d '{
    "document_type": "estudo_tecnico_preliminar",
    "context": {
      "objeto": "Obra de reforma do prédio administrativo",
      "orgao": "Secretaria de Obras",
      "modalidade": "pregão eletrônico",
      "extras": { "tipo_objeto": "obra" }
    }
  }' | jq .
```

**O que conferir:** em `structure.root_sections` deve existir um item com `"key": "declaracao_viabilidade"`.

---

### 2.2 ETP + fornecimento (seção condicional NÃO entra)

```bash
curl -s -X POST http://localhost:8003/api/agent/structure \
  -H "Content-Type: application/json" \
  -d '{
    "document_type": "estudo_tecnico_preliminar",
    "context": {
      "objeto": "Aquisição de material de escritório",
      "orgao": "Secretaria de Administração",
      "modalidade": "dispensa",
      "extras": { "tipo_objeto": "fornecimento" }
    }
  }' | jq .
```

**O que conferir:** não deve haver `"key": "declaracao_viabilidade"` em `structure.root_sections`.

---

### 2.3 Termo de referência (sem catálogo para esse tipo no exemplo)

O registro de exemplo só tem seções para `estudo_tecnico_preliminar`. Para termo_referencia o agente usa fallback (estrutura mínima) ou hints, dependendo da configuração.

```bash
curl -s -X POST http://localhost:8003/api/agent/structure \
  -H "Content-Type: application/json" \
  -d '{
    "document_type": "termo_referencia",
    "context": {
      "objeto": "Contratação de serviços de TI",
      "orgao": "Secretaria de Educação",
      "modalidade": "pregão eletrônico"
    }
  }' | jq .
```

---

### 2.4 ETP com user_prompt (testa section_matches no /structure)

Se o seu cliente enviar **user_prompt** no body de `/structure`, use um schema que aceite esse campo (já existe em **StructureRequest**). Exemplo com `user_prompt` para ver **section_matches** na resposta:

```bash
curl -s -X POST http://localhost:8003/api/agent/structure \
  -H "Content-Type: application/json" \
  -d '{
    "document_type": "estudo_tecnico_preliminar",
    "context": {
      "objeto": "Obra de reforma",
      "extras": { "tipo_objeto": "obra" }
    },
    "user_prompt": "Preciso de um ETP com cláusula sobre viabilidade e estimativa de custos."
  }' | jq .
```

**O que conferir:** `section_matches` pode conter algo como `{ "key": "declaracao_viabilidade", "user_phrase": "cláusula sobre viabilidade", "confidence": "high" }`.

---

## 3. POST /api/agent/registry (atualizar registro)

Uso local: basta enviar o JSON completo no body (sem chave).

```bash
curl -s -X POST http://localhost:8003/api/agent/registry \
  -H "Content-Type: application/json" \
  -d @data/sections_registry.json
```

Ou enviando o JSON inline (exemplo mínimo):

```bash
curl -s -X POST http://localhost:8003/api/agent/registry \
  -H "Content-Type: application/json" \
  -d '{
    "catalog_id": "licitacao-v1",
    "catalog_version": "1.0",
    "entries": [
      {
        "key": "objeto",
        "title": "Do Objeto",
        "document_types": ["estudo_tecnico_preliminar"],
        "content_type": "text",
        "required": true,
        "status": "required",
        "enabled": true,
        "version": "1",
        "parent_key": null
      }
    ]
  }'
```

---

## Resumo rápido

| Objetivo | Endpoint | Destaque |
|----------|----------|----------|
| Interpretar texto livre e gerar estrutura | POST /structure-from-prompt | Testar com os prompts das seções 1.1 a 1.5 |
| Ver seção condicional (Decl. Viabilidade) | POST /structure com ETP + extras.tipo_objeto=obra | 2.1 |
| Ver seção condicional ausente | POST /structure com ETP + tipo_objeto=fornecimento | 2.2 |
| Ver section_matches (certeza pedido ↔ seção) | /structure-from-prompt com “cláusula sobre viabilidade” ou /structure com user_prompt | 1.2, 1.3, 2.4 |
| Atualizar registro | POST /registry (body = JSON) | 3 |

Se **jq** não estiver instalado, remova `| jq .` dos curls para ver o JSON bruto.
