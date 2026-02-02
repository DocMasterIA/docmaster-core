"""
Interfaces padronizadas para chamadas ao modelo: planner e section.

Cada módulo define o contrato de entrada/saída e invoca o adapter.
"""
from app.interfaces.planner import call_planner
from app.interfaces.section import call_section

__all__ = ["call_planner", "call_section"]
