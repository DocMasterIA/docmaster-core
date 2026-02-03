"""
Interfaces padronizadas para chamadas ao modelo: planner, section e analysis.

Cada módulo define o contrato de entrada/saída e invoca o adapter.
"""
from app.interfaces.analysis import call_analysis
from app.interfaces.planner import call_planner
from app.interfaces.section import call_section

__all__ = ["call_planner", "call_section", "call_analysis"]
