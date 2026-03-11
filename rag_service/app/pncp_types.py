from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Optional


@dataclass
class PNCPContractRef:
    """
    Representa uma contratação/aviso retornado pelo PNCP em formato simplificado.

    Esta estrutura é pensada para consumo interno do DocMaster (RAG/LLM),
    não necessariamente espelha 1:1 o schema oficial da API PNCP.
    """

    # Identificadores principais
    numero_pncp: str  # número de controle PNCP, quando disponível
    id_licitacao: Optional[str] = None
    id_aviso: Optional[str] = None

    # Dados institucionais
    orgao: Optional[str] = None
    unidade_compradora: Optional[str] = None
    municipio: Optional[str] = None
    uf: Optional[str] = None

    # Informações da contratação
    modalidade: Optional[str] = None
    objeto_resumido: Optional[str] = None
    valor_global: Optional[float] = None
    data_publicacao: Optional[date] = None
    situacao: Optional[str] = None

    # Metadados auxiliares
    fonte: str = "pncp"
    # Tema inferido do objeto (ex.: "material_limpeza", "ti_infraestrutura", etc.).
    tema_objeto: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None  # payload bruto da API, se for útil para debug


def pncp_contract_to_text(ref: PNCPContractRef) -> str:
    """
    Converte um PNCPContractRef em texto curto para ser injetado no prompt da LLM.

    Não é uma renderização final de cláusula; serve como "exemplo de contexto"
    de contratações semelhantes.
    """
    partes = []

    if ref.objeto_resumido:
        partes.append(f"Objeto: {ref.objeto_resumido}.")

    if ref.orgao or ref.unidade_compradora:
        orgao_txt = ref.unidade_compradora or ref.orgao
        partes.append(f"Órgão/Unidade: {orgao_txt}.")

    if ref.municipio or ref.uf:
        loc = ", ".join(p for p in [ref.municipio, ref.uf] if p)
        if loc:
            partes.append(f"Localidade: {loc}.")

    if ref.modalidade:
        partes.append(f"Modalidade: {ref.modalidade}.")

    if ref.valor_global is not None:
        partes.append(f"Valor global aproximado: R$ {ref.valor_global:,.2f}.")

    if ref.data_publicacao:
        partes.append(f"Data de publicação: {ref.data_publicacao.isoformat()}.")

    if ref.numero_pncp:
        partes.append(f"Número PNCP: {ref.numero_pncp}.")

    if ref.situacao:
        partes.append(f"Situação: {ref.situacao}.")

    return " ".join(partes)


def infer_tema_objeto(text: str) -> Optional[str]:
    """
    Inferência simples de tema do objeto a partir de palavras‑chave.

    Esta função é propositalmente heurística e leve; pode ser substituída
    por algo mais sofisticado (inclusive via LLM) no futuro.
    """
    if not text:
        return None
    t = text.lower()

    # Material/serviço de limpeza
    if any(k in t for k in ("material de limpeza", "materiais de limpeza", "desinfecção", "desinfeccao", "detergente", "sabão", "sabao", "desinfetante")):
        return "material_limpeza"
    if any(k in t for k in ("serviços de limpeza", "servico de limpeza", "limpeza predial", "limpeza urbana", "varrição", "varricao", "coleta de lixo", "coleta de resíduos", "coleta de residuos")):
        return "servicos_limpeza"

    # TI – infraestrutura e serviços
    if any(k in t for k in ("rede cabeada", "cabeamento estruturado", "switch", "roteador", "servidor", "datacenter", "firewall")):
        return "ti_infraestrutura"
    if any(k in t for k in ("licença de software", "licenca de software", "sistema de gestão", "sistema de gestao", "software de gestão", "software de gestao", "sistema informatizado")):
        return "ti_software"
    if any(k in t for k in ("serviços de ti", "servico de ti", "suporte técnico", "suporte tecnico", "manutenção de computadores", "manutencao de computadores")):
        return "ti_servicos"

    # Saúde – medicamentos e serviços
    if any(k in t for k in ("medicamento", "medicamentos", "fármaco", "farmaco", "fármaco", "hospitalar", "insumo hospitalar")):
        return "saude_medicamentos_insumos"
    if any(k in t for k in ("serviços médicos", "servico medico", "serviços de saúde", "servicos de saude", "exames laboratoriais", "exames de imagem")):
        return "saude_servicos"

    # Obras e engenharia
    if any(k in t for k in ("obra", "obras", "pavimentação", "pavimentacao", "reforma", "construção", "construcao", "engenharia", "manutenção predial", "manutencao predial")):
        return "obras_engenharia"

    # Veículos e pneus
    if any(k in t for k in ("aquisição de pneus", "aquisicao de pneus", "pneus", "câmaras de ar", "camaras de ar", "protetores de pneus", "frota de veículos", "frota de veiculos")):
        return "frota_pneus"

    # Educação – material didático
    if any(k in t for k in ("material didático", "material didatico", "livros didáticos", "livros didaticos", "kit escolar", "material escolar")):
        return "educacao_material"

    # Serviços gerais (fallback genérico, ainda assim com alguma categorização)
    if any(k in t for k in ("serviços continuados", "servicos continuados", "terceirização", "terceirizacao", "mão de obra", "mao de obra")):
        return "servicos_gerais"

    return None

