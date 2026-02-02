"""
Cliente HTTP para consumo da API local de IA.

Requisições com timeout, retries e mapeamento de status (401, 429, 5xx)
para exceções. Usado apenas pelo adapter.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.config import OLLAMA_BASE_URL, LLM_MAX_RETRIES, LLM_TIMEOUT
from app.exceptions import (
    LLMClientError,
    LLMRateLimitError,
    LLMServerError,
    LLMTimeoutError,
    LLMUnauthorizedError,
)

logger = logging.getLogger("llm.client")

# Status que disparam retry (transitórios)
RETRY_STATUSES = {429, 500, 502, 503, 504}


def _raise_for_status(response: httpx.Response) -> None:
    """Levanta exceção apropriada conforme status HTTP."""
    if response.status_code == 401:
        raise LLMUnauthorizedError(
            message="Servidor de IA retornou 401 (não autorizado)",
            body=response.text,
        )
    if response.status_code == 429:
        raise LLMRateLimitError(
            message="Servidor de IA retornou 429 (rate limit)",
            body=response.text,
        )
    if 500 <= response.status_code < 600:
        raise LLMServerError(
            message=f"Servidor de IA retornou {response.status_code}",
            status_code=response.status_code,
            body=response.text,
        )
    if response.status_code >= 400:
        raise LLMClientError(
            message=f"Erro HTTP {response.status_code}",
            status_code=response.status_code,
            body=response.text,
        )


async def request(
    method: str,
    path: str,
    json_payload: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> tuple[dict[str, Any] | str, int]:
    """
    Envia requisição ao servidor de IA e retorna (body, status_code).

    - method: "POST" ou "GET".
    - path: path relativo (ex.: /v1/planner), será anexado a OLLAMA_BASE_URL.
    - json_payload: corpo JSON (para POST).
    - timeout: sobrescreve LLM_TIMEOUT se informado.

    Levanta LLMUnauthorizedError, LLMRateLimitError, LLMServerError ou
    LLMTimeoutError em caso de falha.
    """
    url = f"{OLLAMA_BASE_URL}{path}"
    timeout_sec = timeout if timeout is not None else LLM_TIMEOUT
    last_exc: Exception | None = None

    for attempt in range(LLM_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                if method.upper() == "POST":
                    resp = await client.post(url, json=json_payload or {})
                else:
                    resp = await client.get(url)

                _raise_for_status(resp)

                try:
                    body = resp.json()
                except Exception:
                    body = resp.text

                return body, resp.status_code

        except httpx.TimeoutException as e:
            last_exc = LLMTimeoutError("Timeout na requisição ao servidor de IA")
            logger.warning("Tentativa %s/%s timeout: %s", attempt + 1, LLM_MAX_RETRIES, e)
        except LLMUnauthorizedError:
            raise
        except LLMRateLimitError as e:
            last_exc = e
            logger.warning("Tentativa %s/%s rate limit (429)", attempt + 1, LLM_MAX_RETRIES)
        except LLMServerError as e:
            last_exc = e
            if e.status_code in RETRY_STATUSES and attempt < LLM_MAX_RETRIES - 1:
                logger.warning("Tentativa %s/%s erro %s", attempt + 1, LLM_MAX_RETRIES, e.status_code)
            else:
                raise
        except LLMClientError:
            raise

        if attempt < LLM_MAX_RETRIES - 1:
            time.sleep(1.0 * (attempt + 1))  # backoff simples

    if last_exc:
        raise last_exc
    raise LLMClientError("Falha após retries")
