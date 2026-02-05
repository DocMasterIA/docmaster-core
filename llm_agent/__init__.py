"""
Módulo llm_agent: agente especializado em gerar **estrutura lógica**
para documentos de licitação pública.

Responsabilidades:
- Receber tipo de documento + contexto mínimo.
- Chamar o modelo de IA (via módulo de orquestração / llm_api).
- Retornar **apenas a estrutura** (seções, tópicos, subseções) em formato
  de dados (JSON), sem texto jurídico.

Este módulo é interno e não cuida de autenticação, persistência ou
exposição pública direta.
"""

