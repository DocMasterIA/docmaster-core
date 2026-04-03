from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any

from .config import settings

logger = logging.getLogger(__name__)


def _log_dir() -> str:
    d = settings.qwen_audit_log_dir or os.path.join(os.getcwd(), "logs")
    os.makedirs(d, exist_ok=True)
    return d


def log_event(event: dict[str, Any]) -> None:
    """Append uma linha JSONL (auditoria local)."""
    try:
        path = os.path.join(_log_dir(), f"qwen_gateway_{time.strftime('%Y-%m-%d')}.jsonl")
        event.setdefault("ts", time.time())
        event.setdefault("id", str(uuid.uuid4()))
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("audit write failed: %s", e)
