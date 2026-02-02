"""
Módulo de Orquestração LLM (FastAPI).

Camada intermediária entre o backend da aplicação e o servidor de IA local:
integração padronizada, segura e auditável, com cliente HTTP, tratamento de
erros (401, 429, 5xx), retries, timeout e registro de respostas brutas.
Interface padronizada para chamadas planner e section.
"""
