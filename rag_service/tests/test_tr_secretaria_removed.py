"""TR não deve repetir secretaria/cargo abaixo do responsável pela assinatura."""

from __future__ import annotations

from pathlib import Path

from docx import Document

from rag_service.app.tr_template import DispensaSlots, TRTemplateSlots, render_tr_from_slots

TEMPLATE = (
    Path(__file__).resolve().parents[2]
    / "template_packages"
    / "lei_14133"
    / "inexigibilidade_74_i_manutencao_de_veiculos"
    / "TR_modelo_base.docx"
)


def test_tr_keeps_orgao_in_body_but_not_below_assinante(tmp_path):
    assert TEMPLATE.is_file(), f"Template ausente: {TEMPLATE}"
    orgao = "Secretaria de Assistência Social (Itajá)"
    slots = TRTemplateSlots(
        objeto="Prestação de serviços de manutenção veicular.",
        justificativa="Necessidade administrativa.",
        nome_assinante_termo="João Silva",
        orgao=orgao,
        secretaria_usuario=orgao,
        cargo_assinante_termo="Coordenador",
        cidade="Itajá",
        codigo_uf="GO",
        data_termo="01/01/2026",
        dispensa=DispensaSlots(artigo="74", inciso="I"),
    )

    out = tmp_path / "tr_sem_secretaria_assinatura.docx"
    render_tr_from_slots(slots, template_path=TEMPLATE, output_path=out)

    doc = Document(str(out))
    paras = [p.text.replace("\u00a0", " ").strip() for p in doc.paragraphs]

    assert any(orgao in t for t in paras), "órgão deve permanecer no corpo do TR"
    assert sum(1 for t in paras if orgao in t) == 1, "órgão não deve duplicar na assinatura"

    seen_nome = False
    for t in paras:
        if "João Silva" in t:
            seen_nome = True
            continue
        if seen_nome:
            assert orgao not in t
            assert "Coordenador" not in t
