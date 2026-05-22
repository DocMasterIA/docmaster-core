from app.tr_deixis import adapt_text_for_dfd_or_oficio, adapt_text_for_tr


def test_dfd_neste_to_no():
    t = "Conforme condições estabelecidas neste Termo de Referência."
    assert "no Termo de Referência" in adapt_text_for_dfd_or_oficio(t)
    assert "neste" not in adapt_text_for_dfd_or_oficio(t).lower()


def test_dfd_keeps_no():
    t = "Conforme condições estabelecidas no termo de referencia."
    assert adapt_text_for_dfd_or_oficio(t) == t


def test_tr_no_to_neste():
    t = "Conforme condições estabelecidas no termo de referencia."
    out = adapt_text_for_tr(t)
    assert "neste termo de referencia" in out.lower()
    assert " no termo " not in out.lower()


def test_tr_keeps_neste():
    t = "Conforme condições estabelecidas neste Termo de Referência."
    assert adapt_text_for_tr(t) == t


def test_roundtrip_independent():
    tr = "Aquisição de material, neste Termo de Referência."
    dfd = adapt_text_for_dfd_or_oficio(tr)
    assert "no Termo de Referência" in dfd
    back = adapt_text_for_tr(dfd)
    assert "neste Termo de Referência" in back
