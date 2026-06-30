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
    # Cada linha digitada vira parágrafo Word (ou bloco separado por linha em branco).
    fabrizia_paras = [p for p in doc.paragraphs if "Fabrizia" in (p.text or "")]
    assert len(fabrizia_paras) == 1
    assert "Secretaria da Saúde" not in (fabrizia_paras[0].text or "")
    assert any("Secretaria da Saúde" in (p.text or "") for p in doc.paragraphs)
    # Linha em branco entre blocos: parágrafo vazio entre Fabrizia/Secretaria e João.
    fab_idx = next(i for i, p in enumerate(doc.paragraphs) if "Fabrizia" in (p.text or ""))
    joao_idx = next(i for i, p in enumerate(doc.paragraphs) if "João Carlos" in (p.text or ""))
    assert joao_idx > fab_idx + 1


def _assert_multiline_signature_block(doc: Document) -> None:
    fabrizia_paras = [p for p in doc.paragraphs if "Fabrizia" in (p.text or "")]
    assert fabrizia_paras, "Nome Fabrizia não encontrado"
    assert len(fabrizia_paras) == 1
    assert any("Secretaria da Saúde" in (p.text or "") for p in doc.paragraphs)
    assert any("João Carlos" in (p.text or "") for p in doc.paragraphs)
    assert any("Secretaria da Educação" in (p.text or "") for p in doc.paragraphs)
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
