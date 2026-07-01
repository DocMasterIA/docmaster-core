"""Campos multilinha de responsável (Ofício, DFD, TR) preservam quebras do usuário."""

from __future__ import annotations

from pathlib import Path

from docx import Document

from app.dfd_template import render_dfd_from_tr_slots
from app.oficio_template import render_oficio_from_slots
from app.tr_template import TRTemplateSlots, render_tr_from_slots

TEMPLATE_PKG = (
    Path(__file__).resolve().parents[2]
    / "template_packages"
    / "lei_14133"
    / "dispensa_75_i_manutencao_veiculos"
)

MULTILINE_NOME = (
    "Fabrizia de Oliveira Borges\n"
    "Secretaria da Saúde\n"
    "\n"
    "João Carlos\n"
    "Secretaria da Educação"
)

MULTILINE_NOME_DOUBLE_BLANK = (
    "Fabrizia de Oliveira Borges\n"
    "Secretaria da Saúde\n"
    "\n\n"
    "João Carlos\n"
    "Secretaria da Educação"
)


def _count_empty_paragraphs_between(doc: Document, start_text: str, end_text: str) -> int:
    start_idx = next(i for i, p in enumerate(doc.paragraphs) if start_text in (p.text or ""))
    end_idx = next(i for i, p in enumerate(doc.paragraphs) if end_text in (p.text or ""))
    return sum(
        1
        for i in range(start_idx + 1, end_idx)
        if not (doc.paragraphs[i].text or "").strip()
    )


def test_oficio_responsavel_preserves_double_blank_between_blocks():
    slots = TRTemplateSlots(
        sol_oficio_responsavel_nome=MULTILINE_NOME_DOUBLE_BLANK,
        objeto="Objeto de teste para ofício.",
        justificativa="Justificativa de teste para ofício.",
        cidade="Cidade Teste",
    )
    out = render_oficio_from_slots(slots, template_path=TEMPLATE_PKG / "OFICIO_modelo_base.docx")
    doc = Document(out)
    empty_count = _count_empty_paragraphs_between(doc, "Secretaria da Saúde", "João Carlos")
    assert empty_count >= 2, f"Esperadas ≥2 linhas vazias entre blocos, obteve {empty_count}"
    joao_para = next(p for p in doc.paragraphs if "João Carlos" in (p.text or ""))
    assert "Secretaria da Educação" in (joao_para.text or "")
    assert _line_break_count(joao_para) >= 1


def _line_break_count(paragraph) -> int:
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    return sum(len(r._element.findall(f".//{ns}br")) for r in paragraph.runs)


def _paragraphs_with(text: str, doc: Document) -> list:
    return [p for p in doc.paragraphs if text in (p.text or "")]


def test_oficio_responsavel_multiline_not_collapsed_to_single_line():
    slots = TRTemplateSlots(
        sol_oficio_responsavel_nome=MULTILINE_NOME,
        objeto="Objeto de teste para ofício.",
        justificativa="Justificativa de teste para ofício.",
        cidade="Cidade Teste",
    )
    out = render_oficio_from_slots(slots, template_path=TEMPLATE_PKG / "OFICIO_modelo_base.docx")
    doc = Document(out)
    paras = _paragraphs_with("Fabrizia", doc)
    assert paras, "Nome do responsável não apareceu no Ofício"
    full = "\n".join(p.text for p in doc.paragraphs if (p.text or "").strip())
    assert "Fabrizia de Oliveira Borges" in full
    assert "Secretaria da Saúde" in full
    assert "João Carlos" in full
    assert "Secretaria da Educação" in full
    # Nome + secretaria no mesmo parágrafo (w:br); blocos separados por linha em branco.
    fabrizia_paras = [p for p in doc.paragraphs if "Fabrizia" in (p.text or "")]
    assert len(fabrizia_paras) == 1
    fabrizia_para = fabrizia_paras[0]
    assert "Secretaria da Saúde" in (fabrizia_para.text or "")
    assert _line_break_count(fabrizia_para) >= 1
    joao_paras = [p for p in doc.paragraphs if "João Carlos" in (p.text or "")]
    assert len(joao_paras) == 1
    joao_para = joao_paras[0]
    assert "Secretaria da Educação" in (joao_para.text or "")
    assert _line_break_count(joao_para) >= 1
    # Linha em branco entre blocos: parágrafo vazio entre Fabrizia/Secretaria e João.
    fab_idx = next(i for i, p in enumerate(doc.paragraphs) if "Fabrizia" in (p.text or ""))
    joao_idx = next(i for i, p in enumerate(doc.paragraphs) if "João Carlos" in (p.text or ""))
    assert joao_idx > fab_idx + 1


def _assert_multiline_signature_block(doc: Document) -> None:
    fabrizia_paras = [p for p in doc.paragraphs if "Fabrizia" in (p.text or "")]
    assert fabrizia_paras, "Nome Fabrizia não encontrado"
    assert len(fabrizia_paras) == 1
    fabrizia_para = fabrizia_paras[0]
    assert "Secretaria da Saúde" in (fabrizia_para.text or "")
    assert _line_break_count(fabrizia_para) >= 1
    joao_paras = [p for p in doc.paragraphs if "João Carlos" in (p.text or "")]
    assert len(joao_paras) == 1
    joao_para = joao_paras[0]
    assert "Secretaria da Educação" in (joao_para.text or "")
    assert _line_break_count(joao_para) >= 1
    fab_idx = next(i for i, p in enumerate(doc.paragraphs) if "Fabrizia" in (p.text or ""))
    joao_idx = next(i for i, p in enumerate(doc.paragraphs) if "João Carlos" in (p.text or ""))
    assert joao_idx > fab_idx


def test_dfd_assinatura_multiline_preserved():
    slots = TRTemplateSlots(
        dfd_assinatura_nome=MULTILINE_NOME,
        objeto="Objeto de teste para DFD.",
        justificativa="Justificativa de teste para DFD.",
        cidade="Cidade Teste",
    )
    out = render_dfd_from_tr_slots(slots, template_path=TEMPLATE_PKG / "DFD_modelo_base_v2.docx")
    doc = Document(out)
    _assert_multiline_signature_block(doc)


def test_tr_nome_assinante_multiline_preserved():
    slots = TRTemplateSlots(
        nome_assinante_termo=MULTILINE_NOME,
        objeto="Objeto de teste para TR.",
        justificativa="Justificativa de teste para TR com texto suficiente.",
        cidade="Cidade Teste",
        codigo_uf="GO",
    )
    out = render_tr_from_slots(slots, template_path=TEMPLATE_PKG / "TR_modelo_base.docx")
    doc = Document(out)
    _assert_multiline_signature_block(doc)
