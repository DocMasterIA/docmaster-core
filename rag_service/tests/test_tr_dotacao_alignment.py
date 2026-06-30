"""TR: dotação opcional inserida pelo usuário permanece alinhada à esquerda."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from app.tr_template import TRTemplateSlots, render_tr_from_slots

TEMPLATE_ROOT = Path(__file__).resolve().parents[2] / "template_packages" / "lei_14133"

DOTACAO = (
    "Órgão: 02\n"
    "Unidade: 05\n"
    "Projeto/Atividade: 2.045\n"
    "Fonte: 1.500"
)


def _dotacao_paragraphs(doc: Document) -> list:
    out = []
    for p in doc.paragraphs:
        t = p.text or ""
        if "Órgão: 02" in t or "Unidade: 05" in t or "Fonte: 1.500" in t:
            out.append(p)
    return out


def test_dotacao_left_aligned_dispensa_75_ii_compras():
    slots = TRTemplateSlots(
        dotacao=DOTACAO,
        objeto="Objeto de teste.",
        justificativa="Justificativa de teste com texto suficiente.",
        cidade="Cidade",
        codigo_uf="GO",
    )
    out = render_tr_from_slots(
        slots,
        template_path=TEMPLATE_ROOT / "dispensa_75_ii_compras" / "TR_modelo_base.docx",
    )
    paras = _dotacao_paragraphs(Document(out))
    assert paras, "Dotação não encontrada no TR gerado"
    for p in paras:
        assert p.alignment == WD_ALIGN_PARAGRAPH.LEFT


def test_dotacao_left_aligned_manutencao_veiculos_template_sem_align_explicito():
    """Modelo sem alinhamento explícito no placeholder não pode virar justificado."""
    slots = TRTemplateSlots(
        dotacao=DOTACAO,
        objeto="Objeto de teste.",
        justificativa="Justificativa de teste com texto suficiente.",
        cidade="Cidade",
        codigo_uf="GO",
    )
    out = render_tr_from_slots(
        slots,
        template_path=TEMPLATE_ROOT / "dispensa_75_i_manutencao_veiculos" / "TR_modelo_base.docx",
    )
    paras = _dotacao_paragraphs(Document(out))
    assert paras, "Dotação não encontrada no TR gerado"
    for p in paras:
        assert p.alignment == WD_ALIGN_PARAGRAPH.LEFT


def test_sem_dotacao_nao_forca_left_no_bloco_21():
    """Sem dotação informada, não altera alinhamento do placeholder vazio."""
    slots = TRTemplateSlots(
        dotacao="",
        objeto="Objeto de teste.",
        justificativa="Justificativa de teste com texto suficiente.",
        cidade="Cidade",
        codigo_uf="GO",
    )
    out = render_tr_from_slots(
        slots,
        template_path=TEMPLATE_ROOT / "dispensa_75_i_manutencao_veiculos" / "TR_modelo_base.docx",
    )
    doc = Document(out)
    for p in doc.paragraphs:
        if "seguinte dotação orçamentária" in (p.text or "").lower():
            assert p.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY
            break
