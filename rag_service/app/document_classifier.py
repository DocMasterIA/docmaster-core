"""
Classificador automático de documentos e extrator de cláusulas.

Detecta tipo de documento (TR, ETP, DFD) e extrai seções/cláusulas
com ou sem numeração.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


class DocumentType(str, Enum):
    """Tipos de documento reconhecidos."""
    TERMO_REFERENCIA = "termo_referencia"
    ETP = "etp"
    DFD = "dfd"
    OUTRO = "outro"


@dataclass
class ExtractedSection:
    """Seção extraída de um documento."""
    key: str                    # identificador normalizado (snake_case)
    title: str                  # título original
    content: str                # conteúdo completo da seção
    number: Optional[str]       # numeração, se houver (ex: "1", "2.1")
    start_pos: int              # posição inicial no texto
    end_pos: int                # posição final no texto


# Padrões para detectar tipo de documento (busca no início do texto)
# IMPORTANTE: A ordem importa! DFD vem primeiro porque DFDs frequentemente
# mencionam "Termo de Referência" no conteúdo como documento relacionado.
DOCUMENT_TYPE_PATTERNS = [
    # Documento de Formalização da Demanda (verificar PRIMEIRO)
    (DocumentType.DFD, [
        # Com "DOCUMENTO DE" na frente
        r"DOCUMENTO\s+DE\s+FORMALIZA[CÇ][AÃ]O\s+(DA\s+|DE\s+)?DEMANDA",
        # Apenas "FORMALIZAÇÃO DE/DA DEMANDA" (sem "DOCUMENTO DE")
        r"FORMALIZA[CÇ][AÃ]O\s+(DA\s+|DE\s+)DEMANDA",
        # Variante "FORMULAÇÃO" (typo comum em alguns docs)
        r"FORMULA[CÇ][AÃ]O\s+(DA\s+|DE\s+)DEMANDA",
        # Sigla
        r"\bDFD\b",
    ]),
    # Estudo Técnico Preliminar
    (DocumentType.ETP, [
        r"ESTUDO\s+T[EÉ]CNICO\s+PRELIMINAR",
        r"\bETP\b",
    ]),
    # Termo de Referência (por último)
    (DocumentType.TERMO_REFERENCIA, [
        r"TERMO\s+DE\s+REFER[EÊ]NCIA",
        r"TERMO\s+REFERENCIA",
    ]),
]


# Seções comuns e suas variações (para normalização de key)
KNOWN_SECTIONS = {
    "objeto": ["OBJETO", "OBJETO DA CONTRATA", "DO OBJETO"],
    "justificativa": ["JUSTIFICATIVA", "DA JUSTIFICATIVA", "JUSTIFICAÇÃO"],
    "fundamentacao_legal": ["FUNDAMENTAÇÃO", "FUNDAMENTA", "BASE LEGAL", "FUNDAMENTO"],
    "especificacoes": ["ESPECIFICA", "REQUISITOS T[EÉ]CNICOS"],
    "condicoes_fornecimento": ["CONDI[CÇ][OÕ]ES DE FORNECIMENTO", "CONDI[CÇ][OÕ]ES DE EXECU"],
    "forma_pagamento": ["FORMA DE PAGAMENTO", "PAGAMENTO", "CONDI[CÇ][OÕ]ES DE PAGAMENTO"],
    "fiscalizacao": ["FISCALIZA", "ACOMPANHAMENTO E FISCALIZA"],
    "obrigacoes_contratada": ["OBRIGA[CÇ][OÕ]ES DA CONTRATADA", "DEVERES DA CONTRATADA"],
    "obrigacoes_contratante": ["OBRIGA[CÇ][OÕ]ES DO CONTRATANTE", "DEVERES DO CONTRATANTE"],
    "prazo": ["PRAZO", "VIG[EÊ]NCIA", "PRAZO DE EXECU", "PRAZO DE VIG"],
    "penalidades": ["PENALIDADE", "SAN[CÇ][OÕ]ES", "MULTA"],
    "garantia": ["GARANTIA"],
    "descricao_necessidade": ["DESCRI[CÇ][AÃ]O DA NECESSIDADE", "NECESSIDADE"],
    "requisitos_contratacao": ["REQUISITOS DA CONTRATA"],
    "estimativa_quantidade": ["ESTIMATIVA", "QUANTIDADE"],
    "levantamento_mercado": ["LEVANTAMENTO DE MERCADO", "PESQUISA DE MERCADO"],
    "solucao": ["SOLU[CÇ][AÃ]O", "DESCRI[CÇ][AÃ]O DA SOLU"],
    "identificacao_demandante": ["IDENTIFICA[CÇ][AÃ]O", "UNIDADE DEMANDANTE"],
    "dotacao_orcamentaria": ["DOTA[CÇ][AÃ]O", "OR[CÇ]AMENT[AÁ]RIA", "CLASSIFICA[CÇ][AÃ]O OR[CÇ]AMENT"],
    "criterios_selecao": ["CRIT[EÉ]RIOS", "SELE[CÇ][AÃ]O DO FORNECEDOR"],
    "local_entrega": ["LOCAL DE ENTREGA", "LOCAL DA PRESTA"],
    "valor_estimado": ["VALOR ESTIMADO", "VALOR TOTAL", "CUSTO ESTIMADO"],
}


def _normalize_text(text: str) -> str:
    """Remove acentos e normaliza para comparação."""
    return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode().upper()


def _to_snake_case(text: str) -> str:
    """Converte texto para snake_case."""
    normalized = _normalize_text(text)
    return re.sub(r'[^a-z0-9]+', '_', normalized.lower()).strip('_')


def detect_document_type(text: str, search_limit: int = 1500) -> Tuple[DocumentType, Optional[str]]:
    """
    Detecta o tipo de documento com base no conteúdo.
    
    Args:
        text: Texto completo do documento.
        search_limit: Limite de caracteres para busca (início do documento).
    
    Returns:
        Tupla (tipo, match encontrado).
    """
    search_text = _normalize_text(text[:search_limit])
    
    for doc_type, patterns in DOCUMENT_TYPE_PATTERNS:
        for pattern in patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                return doc_type, match.group(0)
    
    return DocumentType.OUTRO, None


def _match_known_section(title: str) -> str:
    """
    Tenta mapear o título para uma seção conhecida.
    
    Returns:
        Key normalizada da seção conhecida ou snake_case do título.
    """
    normalized_title = _normalize_text(title)
    
    for key, patterns in KNOWN_SECTIONS.items():
        for pattern in patterns:
            if re.search(pattern, normalized_title, re.IGNORECASE):
                return key
    
    # Fallback: snake_case do título original
    return _to_snake_case(title)


def extract_sections(text: str) -> List[ExtractedSection]:
    """
    Extrai seções de um documento de licitação.
    
    Reconhece padrões:
    - "1. TÍTULO" ou "1 - TÍTULO" ou "1 TÍTULO" (numerado)
    - "TÍTULO" em linha isolada em maiúsculas (sem número)
    - "1.1 SUBTÍTULO" (subnumeração)
    
    Args:
        text: Texto completo do documento.
    
    Returns:
        Lista de ExtractedSection ordenada por posição.
    """
    sections = []
    
    # Padrão para seções numeradas: "1. TÍTULO", "1 - TÍTULO", "2.1 TÍTULO"
    # Captura: número, separador opcional, título em maiúsculas
    numbered_pattern = r'''
        (?:^|\n)\s*                           # início de linha
        (\d+(?:\.\d+)*)                        # grupo 1: número (1, 2.1, 3.1.2)
        \s*[.\-–—]?\s*                         # separador opcional (., -, –)
        ([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇ\s]+?)  # grupo 2: título em caps
        (?=\n|$)                               # lookahead: fim de linha
    '''
    
    # Padrão para seções sem número: linha com texto em maiúsculas
    # Mais restritivo: linha com poucas palavras, todas em caps
    unnumbered_pattern = r'''
        (?:^|\n)\s*                            # início de linha
        ([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇ\s]{2,50})  # título (3-50 chars, caps)
        \s*(?=\n|$)                            # fim de linha
    '''
    
    # Primeiro, encontra todas as seções numeradas
    for match in re.finditer(numbered_pattern, text, re.MULTILINE | re.VERBOSE):
        number = match.group(1).strip()
        title = match.group(2).strip()
        
        # Filtra títulos muito curtos ou que parecem ser outra coisa
        if len(title) < 3 or title.isdigit():
            continue
        
        # Ignora se parece ser item de lista (a), b), I., II.)
        if re.match(r'^[a-zA-Z]\)|^[IVX]+\.', title):
            continue
        
        key = _match_known_section(title)
        
        sections.append(ExtractedSection(
            key=key,
            title=title,
            content="",  # será preenchido depois
            number=number,
            start_pos=match.start(),
            end_pos=match.end(),
        ))
    
    # Se não encontrou seções numeradas, tenta sem número
    if not sections:
        for match in re.finditer(unnumbered_pattern, text, re.MULTILINE | re.VERBOSE):
            title = match.group(1).strip()
            
            # Filtra: muito curto, parece cabeçalho de página, etc.
            if len(title) < 4 or len(title.split()) > 6:
                continue
            
            # Ignora se parece ser assinatura ou rodapé
            if any(skip in title.upper() for skip in ['ASSINADO', 'PÁGINA', 'PAGE', 'DATA:', 'FONE:']):
                continue
            
            key = _match_known_section(title)
            
            sections.append(ExtractedSection(
                key=key,
                title=title,
                content="",
                number=None,
                start_pos=match.start(),
                end_pos=match.end(),
            ))
    
    # Ordena por posição e preenche conteúdo
    sections.sort(key=lambda s: s.start_pos)
    
    for i, section in enumerate(sections):
        # Conteúdo vai do início da seção até o início da próxima (ou fim do texto)
        content_start = section.start_pos
        content_end = sections[i + 1].start_pos if i + 1 < len(sections) else len(text)
        section.content = text[content_start:content_end].strip()
    
    return sections


def classify_and_extract(text: str) -> Tuple[DocumentType, str, List[ExtractedSection]]:
    """
    Classifica documento e extrai seções em uma única chamada.
    
    Args:
        text: Texto completo do documento.
    
    Returns:
        Tupla (tipo_documento, match_tipo, lista_de_seções).
    """
    doc_type, type_match = detect_document_type(text)
    sections = extract_sections(text)
    return doc_type, type_match or "", sections
