"""Assinatura do DFD deve usar (DFD_NOME_ASSINATURA), não (DFD_FISCAL_CONTRATOS)."""

from __future__ import annotations

from pathlib import Path

from docx import Document

TEMPLATE_ROOT = Path(__file__).resolve().parents[2] / "template_packages"


def _body_paragraph_texts(doc: Document) -> list[str]:
    return [
        "".join(run.text or "" for run in p.runs).strip()
        for p in doc.paragraphs
        if "".join(run.text or "" for run in p.runs).strip()
    ]


def test_dfd_package_templates_use_nome_assinatura_in_signature_block():
    paths = sorted(TEMPLATE_ROOT.rglob("DFD_modelo_base*.docx"))
    assert paths, "Nenhum DFD_modelo_base*.docx encontrado em template_packages/"
    checked = 0
    for path in paths:
        if path.parent.name == "tr_base":
            continue
        doc = Document(str(path))
        body = _body_paragraph_texts(doc)
        assert "(DFD_NOME_ASSINATURA)" in body, f"Falta (DFD_NOME_ASSINATURA) no corpo de {path}"
        assert "(DFD_FISCAL_CONTRATOS)" not in body, (
            f"(DFD_FISCAL_CONTRATOS) no corpo de {path} — use (DFD_NOME_ASSINATURA) na assinatura"
        )
        checked += 1
    assert checked >= 1
