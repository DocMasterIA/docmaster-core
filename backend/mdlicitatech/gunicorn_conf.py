"""Gunicorn: métricas Prometheus em modo multiprocess (vários workers)."""
import os
import shutil


def on_starting(server):
    multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if multiproc_dir:
        shutil.rmtree(multiproc_dir, ignore_errors=True)
        os.makedirs(multiproc_dir, exist_ok=True)


def post_fork(server, worker):
    # Cada worker Gunicorn precisa carregar métricas no próprio PID (mmap multiprocess).
    import backend.app.metrics  # noqa: F401


def child_exit(server, worker):
    from prometheus_client import multiprocess

    multiprocess.mark_process_dead(worker.pid)
