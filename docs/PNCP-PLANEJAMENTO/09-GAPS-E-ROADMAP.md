# Gaps e roadmap

## 1. Lacunas vs objetivo "PNCP completo"

| Gap | Impacto | Complexidade fix |
|-----|---------|------------------|
| Janela só **365 dias rolling** | Contratos >1 ano nunca descobertos se não indexados antes | Alta — multi-janela histórica |
| **5 modalidades** default | Buracos por tipo de licitação | Baixa — env `PNCP_MODALIDADES_DEFAULT` |
| **Throughput** limitado por 429 | Fila demora dias/semanas | Média — tunagem + infra |
| **GET /itens** sem fornecedor em massa | Índice bruto sem razão social | Média — ingestão resultados (caro) |
| **SQLite single-writer** | Contention ingest + coverage + busca | Alta — read replicas ou Postgres |
| **Sem alertas** automáticos | Operador descobre tarde | Baixa — cron/Grafana |
| **Histórico multi-ano** não no planner | Não espelha PNCP nacional | Alta |

---

## 2. Prioridades recomendadas

### Fase A — Estabilidade (jun/2026)

- [x] Purge dead + self-heal sem crash
- [x] Starve/topup itens vs catálogo
- [x] Timeouts task/batch
- [x] Defaults throughput maiores
- [x] `ingest_backpressure` + stall de itens (`items_stall=600s`)
- [x] Heartbeat `items_ok_1h` + doc [10-SLA-ALIMENTACAO.md](./10-SLA-ALIMENTACAO.md)
- [ ] Validar 48h DESKTOP: `items_ok_1h > 0`, `dead=0`, índice sobe
- [ ] Deploy backend fornecedor PDF

### Fase B — Alimentação previsível (1–2 semanas)

- [ ] Métricas simples: itens/hora, done/hora (script cron)
- [ ] Alerta se `items_ok_1h=0` por 2h ou sem batch > 30 min
- [ ] Documentar tunagem 429 vs throughput
- [ ] Opcional: stall recovery durante batch (watchdog async)

### Fase C — Cobertura ampliada (1–2 meses)

- [ ] Planner com **janelas históricas** rotativas (2024, 2023…)
- [ ] Expandir modalidades após validação PNCP
- [ ] `PNCP_INGEST_ITEMS_REFRESH_DAYS=0` em janela controlada para backfill fornecedor?

### Fase D — Escala (futuro)

- [ ] Migrar índice para Postgres + pgvector ou manter SQLite com réplica read-only
- [ ] Worker horizontal (múltiplos consumers — cuidado SQLite)
- [ ] Ingestão resultados/fornecedor em pipeline C separado

---

## 3. Decisões de produto pendentes

1. **Meta de volume:** 1,5M itens suficiente para cotações ou exigir 5M+?
2. **Histórico:** necessário buscar preços de 2022–2023 ou só último ano?
3. **Modalidades:** lista fechada 6–10 ou todas?
4. **Fornecedor na ingestão:** aceitar enriquecimento só na busca (atual) ou investir em pipeline `/resultados` em massa?
5. **SLA operacional:** ver [10-SLA-ALIMENTACAO.md](./10-SLA-ALIMENTACAO.md) — anti-trava, não cobertura PNCP completa

---

## 4. Estimativas realistas de tempo de fila

Ordem de grandeza com ~1300 catalog pending, 6 páginas/batch, ~5 min/batch efetivo:

```
1300 / 6 ≈ 217 batches × 5 min ≈ 18 horas só catálogo
```

Com mix itens + catálogo e topup, **dias** para esvaziar filas grandes é normal.

**Não interpretar** fila grande como travamento se logs mostram batches regulares.

---

## 5. Trabalho técnico sugerido (próxima análise fina)

| Tema | Perguntas a responder |
|------|----------------------|
| Balanceamento fila | `catalog_heavy` threshold 300 OK? items_stall 600s OK? |
| Planner | Enfileirar catálogo enquanto items pending > 0? |
| Watermark | Comportamento ao fim de catálogo + rolling window |
| PNCP 429 | Telemetria: contagem 429/hora nos logs |
| Coverage API | Endpoint leve só fila (sem COUNT itens) |
| Testes integração | Smoke DESKTOP automatizado pós-deploy |
| Fornecedor | % cobertura real em amostra de 1000 homologados |

---

## 6. Referência de estado DESKTOP (jun/2026)

| Métrica | Valor observado |
|---------|-----------------|
| `total_itens` | ~1,54M |
| DB size | ~5 GB |
| `pending` catálogo | ~1300 (após queda de 3700+) |
| `dead` | 0 (pós fix) |
| `contract_items` pending | 0 (problema — starve fix) |
| Batch típico | catalog_ok=3, items_ok=0 (pré-fix) → pós-fix espera `items_ok>0` ou `catalog_heavy` |

Usar como baseline para medir melhoria pós-deploy throughput + starve.

---

## 7. Documentos a manter sincronizados

Ao implementar mudanças, atualizar:

1. Este diretório `docs/PNCP-PLANEJAMENTO/`
2. `docs/PNCP-DECLARATIVO.md`
3. `docs/deploy/PNCP-COMANDOS-OPERACAO.txt`
4. Defaults em `docker-compose.pncp.yml` e `config.py`
