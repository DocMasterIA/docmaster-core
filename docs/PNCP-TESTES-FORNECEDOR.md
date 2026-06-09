# PNCP — testes de itens com fornecedor (homologados + CNPJ)

**Para quem:** validação manual/operacional no DESKTOP ou staging.  
**Contexto:** [`PNCP-CONTEXTO-IA.md`](PNCP-CONTEXTO-IA.md) · [`PLANO-MODULO-COBERTURA-FORNECEDOR-PNCP.md`](PLANO-MODULO-COBERTURA-FORNECEDOR-PNCP.md)

**Meta de produto:** homologados/adjudicados na cotação com **razão social + CNPJ** quando o PNCP publicar vencedor (alvo **70–90%**, ideal 100% no subconjunto homologado).

**Não confundir:** `cobertura_cnpj_pct` no índice total (~1,5M linhas) — KPI errado sem Fase B.

---

## 0. Pré-requisitos

```bash
# Researcher no ar + código fornecedor/skip
docker ps --filter name=pncp_researcher_service
docker exec pncp_researcher_service python -c "
from pncp_researcher_service.app.local_index import contract_needs_items_refresh
print('skip_fn ok')
"
docker exec pncp_researcher_service env | grep -E 'SEARCH_ONLY|ENRICH_HOMOLOG|REFRESH_DAYS'

# Backend no ar
docker ps --filter name=backend
```

Escolher **1–2 cotações reais** com fontes PNCP (anotar IDs). Ex.: `--cotacao-id 6`.

---

## 1. Testes automatizados (repo — sem PNCP ao vivo)

```bash
cd ~/docmaster-core
source .venv/bin/activate  # ou venv do projeto

# Researcher — resolver fornecedor offline (fixtures JSON)
PYTHONPATH=pncp_researcher_service pytest pncp_researcher_service/tests/test_supplier_resolver.py -v

# Researcher — skip refresh ingest
PYTHONPATH=. pytest pncp_researcher_service/tests/test_ingest_refresh.py -v

# Backend — enrich sem HTTP
pytest backend/app/tests/test_pncp_supplier_enrichment.py -v
```

**Passou:** lógica de parse homolog/CNPJ e enrich payload OK.

---

## 2. Índice SQLite — cobertura bruta (referência, não KPI)

```bash
docker exec pncp_researcher_service python -c "
import urllib.request, json
d=json.loads(urllib.request.urlopen(
  'http://127.0.0.1:8012/api/pncp-research/local-index/stats', timeout=120).read())
f=d.get('fornecedor',{})
print('total_itens', d['total_itens'])
print('com_cnpj', f.get('itens_com_cnpj_fornecedor'))
print('elegiveis', f.get('itens_elegiveis'))
print('elegiveis_cnpj+nome', f.get('itens_elegiveis_com_cnpj_e_nome'))
print('cobertura_elegivel_pct', f.get('cobertura_elegivel_pct'))
"
```

| Resultado | Interpretação |
|-----------|----------------|
| `cobertura_elegivel_pct` baixo (<10%) | **Esperado** sem backfill `/resultados` |
| Sobe após Fase B | Ingest grava vencedor no índice |

---

## 3. Busca local — homologados + enrich (API)

Termo com resultados conhecidos (ex.: `papel`, `toner`, `cadeira`):

```bash
docker exec pncp_researcher_service python -c "
import urllib.request, json
body=json.dumps({
  'termo_busca':'papel',
  'max_paginas':5,
  'tamanho_pagina':50,
  'somente_homologados': True
}).encode()
req=urllib.request.Request(
  'http://127.0.0.1:8012/api/pncp-research/local-index/search-items',
  data=body, headers={'Content-Type':'application/json'})
r=json.loads(urllib.request.urlopen(req,timeout=120).read())
s=r.get('stats',{})
itens=r.get('itens',[])
print('total', s.get('total_registros'))
print('filtrados_nao_homolog', s.get('filtrados_nao_homologados'))
print('com_cnpj', s.get('itens_com_cnpj_fornecedor'))
print('enriquecidos_pncp', s.get('enriquecidos_pncp_na_busca'))
for i,it in enumerate(itens[:5]):
  print('---', i+1)
  print('  homolog', it.get('item_homologado'))
  print('  cnpj', it.get('cnpj_fornecedor') or '-')
  print('  fornecedor', (it.get('fornecedor') or '-')[:60])
  print('  situacao', it.get('situacao_item_exibicao') or it.get('situacaoCompraItemNome') or '-')
"
```

### Checklist busca

- [ ] `somente_homologados` respeitado — nenhum item «Em andamento» óbvio na lista
- [ ] `filtrados_nao_homologados` > 0 se termo amplo (filtro ativo)
- [ ] Alguns itens com `cnpj_fornecedor` (índice ou enrich)
- [ ] `enriquecidos_pncp_na_busca` ≤ 16

**Teste negativo:** repetir com termo impossível → `total` 0, sem erro 500.

---

## 4. UI — busca manual e busca inteligente

### 4.1 Busca manual (`BuscaManualCotacoes`)

1. Abrir cotação → busca manual PNCP.
2. Termo + UF opcional → buscar.

| Verificar | OK se |
|-----------|--------|
| Lista só homologados/adjudicados | Sem «Em andamento» dominando |
| Coluna/card fornecedor ou CNPJ | Visível onde PNCP tem vencedor |
| Adicionar fonte à cotação | Item entra na tabela de fontes |

### 4.2 Busca inteligente (`BuscaInteligenteCotacoes`)

Mesmos critérios; confirmar que payload envia `somente_homologados: true`.

### 4.3 Detalhe cotação (`CotacaoDetalhe`)

| Verificar | OK se |
|-----------|--------|
| Fontes PNCP listadas | `numero_pncp`, item, preço |
| Fornecedor / CNPJ na linha | Preenchido ou vazio explicável |
| Editar / remover fonte | Sem regressão |

---

## 5. Adicionar fonte — enrich no backend

1. Na cotação, adicionar **3–5 fontes** homologadas (mix: com e sem CNPJ na busca).
2. Recarregar detalhe da cotação.

```bash
# Ver source JSON de uma fonte (substituir ID fonte)
docker exec backend python manage.py shell -c "
from backend.app.models import PncpCotacaoItemCotacao
r=PncpCotacaoItemCotacao.objects.get(id=FONT_ID)
print('cnpj', (r.source or {}).get('cnpj_fornecedor'))
print('fornecedor', (r.source or {}).get('fornecedor'))
print('homolog', (r.source or {}).get('item_homologado'))
"
```

| Verificar | OK se |
|-----------|--------|
| Homologado sem CNPJ na busca | Após add, `cnpj_fornecedor` preenchido **ou** gap 204 |
| Não homologado | **Não** entra (ou rejeitado) com `PNCP_ADD_SOURCE_ONLY_HOMOLOGATED=1` |
| `source` persistido | Sobrevive reload |

---

## 6. Auditoria — métrica principal (cotação)

### 6.1 Homologados (KPI produto)

```bash
docker exec backend python manage.py audit_pncp_homologados_coverage --cotacao-id <ID>
```

Anotar:
- `Homologadas com CNPJ no source: X/Y`
- `Cobertura homologados (source): Z%`
- Bloco `gap_reason`

| Meta | Ação se falhar |
|------|----------------|
| ≥ 70% | OK para produção |
| 50–70% | Investigar gaps dominantes |
| < 50% | Priorizar R1/R2; amostrar linhas pendentes |

### 6.2 Todas as fontes + JSON

```bash
docker exec backend python manage.py audit_pncp_supplier_coverage --cotacao-id <ID>
docker exec backend python manage.py audit_pncp_supplier_coverage --cotacao-id <ID> --only-missing
docker exec backend python manage.py audit_pncp_supplier_coverage --cotacao-id <ID> --json > ~/audit-cotacao-<ID>.json
```

### 6.3 Significado dos `gap_reason`

| gap_reason | Significado | Ação |
|------------|-------------|------|
| `ok_ja_no_source` | CNPJ já no source | OK |
| `ok_fornecedor_resolvido` | Probe PNCP resolveu | OK |
| `pncp_resultados_204` | PNCP sem vencedor publicado | Limite API — R5 no PDF |
| `pncp_resultados_200_sem_cnpj` | Resultado sem CNPJ | Bug ou dado incompleto |
| `pncp_catalogo_sem_fornecedor` | Só catálogo | Esperado sem Fase B |
| `pncp_http_error` | Timeout/429 | Retry / pausar ingest |
| `missing_pncp_keys` | Falta ano/seq/item | Dado corrompido na fonte |

---

## 7. PDF — enrich antes do relatório

1. Cotação com **≥10 fontes** homologadas (mix CNPJ sim/não).
2. Gerar **Relatório de Pesquisa de Preços** (PDF).

| Verificar | OK se |
|-----------|--------|
| Linhas homologadas | Fornecedor + CNPJ onde audit deu `ok_*` |
| Linhas 204 | Sem CNPJ mas preço/ref PNCP presente (até R5: texto explícito) |
| Tempo geração | < 2–3 min (96 lookups PNCP) |
| Sem timeout 502 | Backend aguenta enrich |

**Desligar enrich (teste controle):** `PNCP_RELATORIO_PDF_SKIP_ENRICH=1` → PDF sem chamadas PNCP (só o que já estava no source).

---

## 8. Regressão homologados

```bash
# Busca com homolog OFF (só teste API — produto usa ON)
docker exec pncp_researcher_service python -c "
import urllib.request, json
body=json.dumps({'termo_busca':'papel','max_paginas':3,'tamanho_pagina':30,'somente_homologados': False}).encode()
req=urllib.request.Request('http://127.0.0.1:8012/api/pncp-research/local-index/search-items',
  data=body, headers={'Content-Type':'application/json'})
r=json.loads(urllib.request.urlopen(req,timeout=120).read())
print('total', r['stats']['total_registros'], 'filtrados', r['stats'].get('filtrados_nao_homologados'))
"
```

| Verificar | OK se |
|-----------|--------|
| `somente_homologados: false` | `total` ≥ default true (mais linhas) |
| Default prod (`SEARCH_ONLY=1`) | UI ainda só homologados |

---

## 9. Propagação CNPJ na cotação

1. Adicionar **2 fontes** do **mesmo fornecedor** (mesmo CNPJ, itens diferentes).
2. Uma com nome vazio, outra com nome preenchido.

| Verificar | OK se |
|-----------|--------|
| PDF / detalhe | Nome propagado para linha que só tinha CNPJ |

---

## 10. Cadastro manual (`PncpFornecedorCadastro`)

1. Fonte sem CNPJ no PNCP → cadastrar fornecedor manual na cotação.
2. Regenerar PDF.

| Verificar | OK se |
|-----------|--------|
| Linha usa cadastro manual | Nome/CNPJ do cadastro usuário |

---

## 11. Matriz resumida — o que testar quando

| Mudança no código | Testes mínimos |
|-------------------|----------------|
| `supplier_resolver.py` | pytest resolver + audit cotação |
| `pncp_supplier_enrichment.py` | pytest backend + add fonte + PDF |
| `local_item_search` / homolog | Teste §3 + UI §4 |
| `pncp_relatorio_*` | PDF §7 |
| Só ingest worker | **Não** exige reteste fornecedor (salvo Fase B) |
| Fase B `/resultados` ingest | §2 índice + §3 busca + audit |

---

## 12. Template de registro (copiar por sessão)

```
Data:
Cotação ID:
Deploy: researcher [ ] backend [ ] frontend [ ]

audit_pncp_homologados_coverage: ___% (___/___ homolog com CNPJ)
Gap dominante:
Busca manual (termo ___): total ___ | com CNPJ ___
PDF: OK [ ] | linhas sem fornecedor: ___
Notas:
```

---

## 13. Comandos rápidos (copiar/colar)

```bash
CID=6  # ajustar

docker exec backend python manage.py audit_pncp_homologados_coverage --cotacao-id $CID
docker exec backend python manage.py audit_pncp_supplier_coverage --cotacao-id $CID --only-missing

docker exec pncp_researcher_service python -c "
import urllib.request, json
d=json.loads(urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/local-index/stats',timeout=120).read())
print(json.dumps(d.get('fornecedor'), indent=2))
"
```

---

*Atualizar este ficheiro quando novos gaps (R4 UI, R5 PDF) forem implementados.*
