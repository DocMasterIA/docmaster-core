# Grafana Explore — queries prontas (Prometheus)

Use datasource **Prometheus** (não "Mixed"). Cole **uma linha** por vez e Run query.

`$__range` só funciona no dashboard; no Explore use intervalo fixo, ex. `[6h]` ou `[24h]`.

## Servidor (node_exporter)

```promql
100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))
```

```promql
100 * (1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])))
```

```promql
node_load1
```

```promql
node_filesystem_avail_bytes{mountpoint="/"}
```

```promql
up{job="node"}
```

## DocMaster (API)

```promql
up{job="backend"}
```

```promql
docmaster_metrics_active
```

```promql
sum(increase(docmaster_document_operations_total{operation="gerar_tr_e_dfd",result="success"}[24h]))
```

```promql
sum by (tipo_geracao) (increase(docmaster_document_operations_total{result="success"}[24h]))
```
