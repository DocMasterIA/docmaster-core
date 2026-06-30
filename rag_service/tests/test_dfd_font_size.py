"""DFD: assinatura multilinha herda 12 pt do placeholder (não força corpo inteiro)."""

from __future__ import annotations

from pathlib import Path

from docx import Document

from app.dfd_template import render_dfd_from_tr_slots
from app.tr_template import TRTemplateSlots

TEMPLATE_PKG = (
    Path(__file__).resolve().parents[2]
    / "template_packages"
    / "lei_14133"
    / "dispensa_75_ii_compras"
)

MULTILINE_ASSINATURA = (
    "Ariane do Nascimento Martins\n"
    "Fiscal de Contratos\n"
    "\n"
    "Abc123123123123\n"
    "Fiscal de Contratosxyz"
)

# Placeholder (DFD_NOME_ASSINATURA) no modelo vem em 12 pt.
TEMPLATE_ASSINATURA_SIZE_PT = 12.0


def _run_size_pt(run) -> float | None:
    if run.font.size is None:
        return None
    return round(run.font.size / 12700, 1)


def test_dfd_multiline_assinatura_todas_linhas_mesmo_tamanho_do_placeholder():
    slots = TRTemplateSlots(
        dfd_assinatura_nome=MULTILINE_ASSINATURA,
        dfd_responsavel_demanda="Servidor Teste",
        objeto="Objeto de teste para DFD.",
        justificativa="Justificativa de teste para DFD.",
        cidade="Cidade Teste",
    )
    out = render_dfd_from_tr_slots(slots, template_path=TEMPLATE_PKG / "DFD_modelo_base.docx")
    doc = Document(out)

    assinatura_runs = []
    for p in doc.paragraphs:
        t = p.text or ""
        if any(
            marker in t
            for marker in (
                "Ariane do Nascimento Martins",
                "Fiscal de Contratos",
                "Abc123123123123",
                "Fiscal de Contratosxyz",
            )
        ):
            assinatura_runs.extend(r for r in p.runs if (r.text or "").strip())

    assert assinatura_runs, "Nenhum run da assinatura multilinha encontrado"
    for run in assinatura_runs:
        assert _run_size_pt(run) == TEMPLATE_ASSINATURA_SIZE_PT, (
            f"Run {run.text!r} com tamanho {_run_size_pt(run)} pt, "
            f"esperado {TEMPLATE_ASSINATURA_SIZE_PT} pt (placeholder do modelo)"
        )

    # Corpo do formulário (tabela) permanece 11 pt — não alterar tipografia geral do DFD.
    body_11pt = False
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    if "Servidor Teste" in (p.text or ""):
                        for run in p.runs:
                            if (run.text or "").strip() and _run_size_pt(run) == 11.0:
                                body_11pt = True
    assert body_11pt, "Campo de corpo (responsável demanda) deveria permanecer em 11 pt"
