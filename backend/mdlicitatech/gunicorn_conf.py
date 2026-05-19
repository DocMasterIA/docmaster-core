"""Gunicorn: métricas Prometheus em modo multiprocess (vários workers)."""
import os
import shutil


def on_starting(server):
    multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if multiproc_dir:
        shutil.rmtree(multiproc_dir, ignore_errors=True)
        os.makedirs(multiproc_dir, exist_ok=True)


def post_fork(server, worker):
    # Antes do Django carregar no worker: mmap por PID (docmaster_* + django_*).
    # Ver https://prometheus.github.io/client_python/multiprocess/
    from prometheus_client import values

    values.ValueClass = values.MultiProcessValue(process_identifier=lambda: worker.pid)


def child_exit(server, worker):
    from prometheus_client import multiprocess

    multiprocess.mark_process_dead(worker.pid)
