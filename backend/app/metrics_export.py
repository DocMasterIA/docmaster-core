"""Exportação /metrics com agregação multiprocess (Gunicorn)."""
from __future__ import annotations

import os

import prometheus_client
from django.http import HttpResponse
from prometheus_client import CollectorRegistry, multiprocess


def export_metrics_view(request) -> HttpResponse:
    """
    Substitui django_prometheus.exports.ExportToDjangoView.

    Cria o registry por request (recomendado pelo client_python em modo multiprocess)
    e inclui séries sem amostras ainda (support_collectors_without_names).
    """
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR") or os.environ.get("prometheus_multiproc_dir"):
        registry = CollectorRegistry(support_collectors_without_names=True)
        multiprocess.MultiProcessCollector(registry)
    else:
        registry = prometheus_client.REGISTRY

    metrics_page = prometheus_client.generate_latest(registry)
    return HttpResponse(
        metrics_page,
        content_type=prometheus_client.CONTENT_TYPE_LATEST,
    )
