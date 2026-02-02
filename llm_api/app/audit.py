"""
Registro (log) de respostas brutas do modelo para fins de auditoria.

Grava por requisição: timestamp, request_id, call_type, request_payload,
response_raw e duration_ms. Formato JSON Lines; destino configurável
(LLM_AUDIT_LOG_DIR) ou apenas logger Python.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

from app.config import LLM_AUDIT_LOG_DIR

logger = logging.getLogger("llm.audit")


def _ensure_audit_dir() -> Path | None:
    if not LLM_AUDIT_LOG_DIR:
        return None
    p = Path(LLM_AUDIT_LOG_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _serialize_payload(obj: Any) -> Any:
    """Converte payload para formato serializável (evita bytes em JSON)."""
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if isinstance(obj, dict):
        return {k: _serialize_payload(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize_payload(v) for v in obj]
    return obj


def log_request_response(
    call_type: str,
    request_payload: Any,
    response_raw: Any,
    duration_ms: float,
    request_id: str | None = None,
    status_code: int | None = None,
) -> None:
    """
    Registra uma chamada ao servidor de IA para auditoria.

    - call_type: "planner" ou "section" (ou outro tipo definido).
    - request_payload: payload enviado (será sanitizado para JSON).
    - response_raw: resposta bruta (texto ou dict).
    - duration_ms: duração da requisição em milissegundos.
    - request_id: identificador único da chamada (gerado se não informado).
    - status_code: status HTTP da resposta (opcional).
    """
    request_id = request_id or str(uuid.uuid4())
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"

    record = {
        "timestamp": timestamp,
        "request_id": request_id,
        "call_type": call_type,
        "request_payload": _serialize_payload(request_payload),
        "response_raw": _serialize_payload(response_raw),
        "duration_ms": round(duration_ms, 2),
    }
    if status_code is not None:
        record["status_code"] = status_code

    line = json.dumps(record, ensure_ascii=False) + "\n"
    logger.info("llm_audit %s", line.strip())

    audit_dir = _ensure_audit_dir()
    if audit_dir:
        # Um arquivo por dia: llm_audit_YYYY-MM-DD.jsonl
        date_suffix = time.strftime("%Y-%m-%d", time.gmtime())
        path = audit_dir / f"llm_audit_{date_suffix}.jsonl"
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError as e:
            logger.warning("Falha ao gravar log de auditoria em %s: %s", path, e)
