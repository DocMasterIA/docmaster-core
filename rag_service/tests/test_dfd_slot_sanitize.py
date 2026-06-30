from rag_service.app.dfd_slot_sanitize import sanitize_dfd_setor_requisitante


def test_sanitize_dfd_setor_requisitante_keeps_valid_setor():
    assert sanitize_dfd_setor_requisitante("Secretaria de Administração") == "Secretaria de Administração"


def test_sanitize_dfd_setor_requisitante_rejects_form_label():
    assert sanitize_dfd_setor_requisitante("Qual setor/secretaria será atendido?") == ""


def test_sanitize_dfd_setor_requisitante_rejects_prompt_prefix():
    assert sanitize_dfd_setor_requisitante("Setor/secretaria atendido: Secretaria X") == ""


def test_sanitize_dfd_setor_requisitante_empty():
    assert sanitize_dfd_setor_requisitante("") == ""
    assert sanitize_dfd_setor_requisitante("   ") == ""
