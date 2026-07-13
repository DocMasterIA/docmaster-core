from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api_feed import feed_router, legacy_feed_router
from .api_researcher import researcher_router
from .config import PNCP_INGEST_WORKER_ENABLED
from .ingest_runtime import configure_service_logging
from .ingest_worker import ingest_worker_loop
from .service_mode import (
    SERVICE_MODE,
    is_feed_mode,
    is_researcher_mode,
    pncp_ingest_worker_allowed,
    service_title,
)


def create_app() -> FastAPI:
    configure_service_logging()

    async def _supervised_ingest_worker() -> None:
        import logging

        sup_log = logging.getLogger("pncp_researcher_service.app.ingest_worker")
        # Worker PNCP só no feed PNCP — feeds TCE/outras plataformas não dependem dele.
        if not PNCP_INGEST_WORKER_ENABLED or not pncp_ingest_worker_allowed():
            return
        while True:
            try:
                await ingest_worker_loop()
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                sup_log.error(
                    "ingest worker falha: %s: %s — reinício em 5s",
                    type(exc).__name__,
                    exc,
                )
                sup_log.exception("ingest worker traceback")
                await asyncio.sleep(5.0)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        worker_task: asyncio.Task | None = None
        if PNCP_INGEST_WORKER_ENABLED and pncp_ingest_worker_allowed():
            worker_task = asyncio.create_task(_supervised_ingest_worker())
        yield
        if worker_task is not None:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass

    app = FastAPI(title=service_title(), version="1.3.0", lifespan=lifespan)

    if is_feed_mode():
        app.include_router(feed_router, prefix="/api")
        if SERVICE_MODE == "feed":
            app.include_router(legacy_feed_router, prefix="/api")

    if is_researcher_mode():
        app.include_router(researcher_router, prefix="/api")

    return app
