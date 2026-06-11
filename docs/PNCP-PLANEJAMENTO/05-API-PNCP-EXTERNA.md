# API PNCP externa

## 1. Bases URL

| Variável | Default | Uso |
|----------|---------|-----|
| `PNCP_BASE_URL` | `https://pncp.gov.br/api/consulta` | Catálogo / publicação |
| `PNCP_PNCP_API_BASE_URL` | `https://pncp.gov.br/pncp-api` | Itens, resultados, contratos |

Cliente: `pncp_researcher_service/app/pncp_client.py`

---

## 2. Endpoints usados

### Catálogo (ingestão + busca ao vivo)

```
GET /v1/contratacoes/publicacao
```

Parâmetros principais:
- `dataInicial`, `dataFinal` — formato **AAAAMMDD**
- `codigoModalidadeContratacao` — inteiro
- `uf` — sigla
- `pagina`, `tamanhoPagina` — paginação (10–50)

**Limite crítico:** intervalo **máximo 365 dias** por request. Acima → HTTP 422.

Implementação: `ingest_dates.resolve_backfill_window()` cap em 365 dias.

### Itens de contratação

```
GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens
```

Retorna tabela de itens (descrição, quantidade, valores). **Não** garante razão social do fornecedor vencedor em cada linha.

### Resultados / homologação (fornecedor)

Cadeia em `get_contract_supplier_snapshot()`:

1. `/itens/{numeroItem}/resultados`
2. `/resultados` (nível compra)
3. Dados em `/contratos/contratacao`
4. Fallback inline no catálogo

### BrasilAPI (cadastro CNPJ)

Quando PNCP tem CNPJ mas nome inútil → `fetch_brasilapi_fornecedor_por_cnpj`.

---

## 3. Modalidades default

```python
PNCP_MODALIDADES_DEFAULT = [8, 6, 7, 9, 10]
```

| Código | Uso típico DocMaster |
|--------|---------------------|
| 8 | Dispensa de licitação |
| 6 | Pregão |
| 7 | Dispensa (variante) |
| 9 | Inexigibilidade |
| 10 | Manifestação de interesse / outros |

**Outras modalidades** existem no PNCP e **não** entram no índice até configurar `PNCP_MODALIDADES_DEFAULT`.

---

## 4. UFs

27 UFs em `PNCP_UFS_DEFAULT` (AC … TO). Cobertura nacional dentro da janela temporal.

---

## 5. Throttle e retry

| Mecanismo | Default |
|-----------|---------|
| `PNCP_THROTTLE_MODE` | `bucket` |
| `PNCP_BUCKET_CAPACITY` | 16 tokens burst |
| `PNCP_BUCKET_REFILL_PER_SEC` | 24 req/s sustentado |
| `PNCP_MAX_RETRIES` | 4 |
| `PNCP_RATE_LIMIT_EXTRA_ATTEMPTS` | 6 (429/5xx) |
| `PNCP_TIMEOUT` | 120s (código); compose pode usar 60s |

Comportamento em 429:
- Retry com backoff (cap 90s)
- Ingestão: `_mark_ingest_error` → scope **pausado** 180s × 2^streak (max 1800s)

---

## 6. Erros comuns PNCP

| HTTP / sintoma | Classificação ingest | Ação |
|----------------|---------------------|------|
| 429 | rate_limit | Autopause scope |
| 502/503/504 | waf_or_gateway | Autopause |
| JSON inválido no body | json_invalid | Pause 120s, 3 retries no client |
| 422 | janela > 365d | Bug config — não deve ocorrer |
| Timeout | timeout | Task failed + retry |
| 404 itens | — | `get_contract_items` retorna `[]` silencioso |

---

## 7. Particionamento de datas (busca ao vivo)

`service._pn_date_windows()` divide períodos > 365d em janelas consecutivas para `market_search`.

**Ingestão 24/7 NÃO usa** multi-janela histórica — só janela rolling 365d. Ver roadmap.

---

## 8. O que o PNCP tem vs o que indexamos

| Dimensão | PNCP nacional (ordem de grandeza) | Índice DocMaster |
|----------|-----------------------------------|------------------|
| Itens | Dezenas de milhões | ~1,5M+ |
| Anos | Desde implantação PNCP | Últimos 365 dias |
| Modalidades | Todas | 5 default |
| Atualização | Contínua | Worker + refresh 7d |

**Conclusão:** o índice é uma **amostra operacional profunda recente**, não espelho completo.
