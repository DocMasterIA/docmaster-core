"""
Exceções da camada LLM.

Erros específicos para 401 (não autorizado), 429 (rate limit), 5xx (erro do
servidor de IA) e erros genéricos de cliente, para tratamento centralizado.
"""
from __future__ import annotations


class LLMClientError(Exception):
    """Erro base da camada LLM (cliente/adapter)."""
    def __init__(self, message: str, status_code: int | None = None, body: str | bytes | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.body = body


class LLMUnauthorizedError(LLMClientError):
    """401: não autorizado (token inválido ou ausente)."""
    def __init__(self, message: str = "Não autorizado", body: str | bytes | None = None):
        super().__init__(message, status_code=401, body=body)


class LLMRateLimitError(LLMClientError):
    """429: rate limit excedido."""
    def __init__(self, message: str = "Rate limit excedido", body: str | bytes | None = None):
        super().__init__(message, status_code=429, body=body)


class LLMServerError(LLMClientError):
    """5xx: erro interno do servidor de IA."""
    def __init__(self, message: str, status_code: int = 500, body: str | bytes | None = None):
        super().__init__(message, status_code=status_code, body=body)


class LLMTimeoutError(LLMClientError):
    """Timeout na requisição ao servidor de IA."""
    def __init__(self, message: str = "Timeout na requisição ao servidor de IA"):
        super().__init__(message, status_code=None)
