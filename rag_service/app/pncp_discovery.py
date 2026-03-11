from __future__ import annotations

"""
Módulo de descoberta de contratações no PNCP para futura ingestão.

Usa a API oficial de consultas (search_contracts) para listar contratações
por período, modalidade e filtros geográficos, retornando PNCPContractRef
com tema_objeto já inferido.
"""

from typing import List, Optional

from .pncp_client import search_contracts
from .pncp_types import PNCPContractRef


async def list_contracts_periodo(
    data_inicial: str,
    data_final: str,
    codigo_modalidade: int,
    uf: Optional[str] = None,
    codigo_municipio_ibge: Optional[str] = None,
    limite: int = 100,
) -> List[PNCPContractRef]:
    """
    Lista contratações no PNCP em um período, com filtros simples.

    Args:
        data_inicial: AAAAMMDD (inclusive).
        data_final: AAAAMMDD (inclusive).
        codigo_modalidade: código da modalidade (ver tabela de domínio do manual).
        uf: sigla da unidade federativa (opcional).
        codigo_municipio_ibge: código IBGE do município (opcional).
        limite: número máximo de contratações a retornar (paginação automática).

    Returns:
        Lista de PNCPContractRef, cada um com metadados básicos e tema_objeto inferido.
    """
    resultados: List[PNCPContractRef] = []
    pagina = 1

    while len(resultados) < limite:
        restantes = limite - len(resultados)
        tamanho_pagina = min(restantes, 100)

        refs = await search_contracts(
            data_inicial=data_inicial,
            data_final=data_final,
            codigo_modalidade=codigo_modalidade,
            uf=uf,
            codigo_municipio_ibge=codigo_municipio_ibge,
            pagina=pagina,
            tamanho_pagina=tamanho_pagina,
        )
        if not refs:
            break

        resultados.extend(refs)
        if len(refs) < tamanho_pagina:
            break

        pagina += 1

    return resultados[:limite]

