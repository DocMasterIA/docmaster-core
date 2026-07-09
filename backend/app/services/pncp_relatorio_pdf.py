"""
Relatório PDF de cotações PNCP — esquema inicial (WeasyPrint).

Objetivo do módulo (especificação institucional):
- Gerar relatórios estruturados em PDF a partir das cotações, com consolidação
  organizada e padronizada para uso institucional.
- Estrutura clara: título personalizado (definido na geração), data da pesquisa,
  itens consolidados, CNPJs extraídos das fontes quando disponíveis.
- QR Code com URL pública para baixar a cópia de verificação do mesmo PDF (módulo ``app.qr``).
- Padronização visual base (tipografia, margens, tabela de itens) — evolução
  futura: templates institucionais, assinatura digital, versionamento.

Dependências: weasyprint (projeto), qrcode (requirements).
"""
from __future__ import annotations

import base64
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from django.conf import settings
from django.utils import timezone
from jinja2 import Environment, BaseLoader, select_autoescape
from weasyprint import HTML

from backend.app.qr import qr_png_data_url
from backend.app.services.pncp_relatorio_itens import (
    EMAIL_INDISPONIVEL_RF,
    FORMULA_LABELS,
    _formatar_moeda_br,
    agrupar_cotacoes_por_item_relatorio_pesquisa_precos,
    agrupar_itens_relatorio_pesquisa_precos,
    nome_fornecedor_e_util_para_exibicao,
    texto_orgao_exibicao_relatorio_pesquisa_precos,
    total_item_de_media_unitaria_exibida,
)
from backend.app.services.pncp_supplier_enrichment import (
    pdf_receitaws_max_http_lookups,
    receitaws_email_fallback_enabled,
)
from backend.app.services.pncp_relatorio_pdf_layout import (
    PDF_CAPA_RESPONSAVEL_MAX,
    PDF_CAPA_TITULO_COTACAO_MAX,
    PDF_TERMO_PNCP_MAX,
    sanear_grupos_relatorio_para_pdf,
    sanear_texto_capa_pdf,
    truncar_texto_pdf,
)

DOCUMENTO_TECNICO_LEAD = (
    "Documento técnico consolidado com metodologia, análise técnica, rastreabilidade das cotações e "
    "conclusão para suporte à contratação."
)

_FORMULA_SHORT_LABELS: Dict[str, str] = {
    "media_aritmetica_precos_obtidos": "Média Aritmética",
    "mediana_precos_obtidos": "Mediana",
    "menor_preco": "Menor preço",
    "media_saneada": "Média saneada",
    "media_ponderada": "Média ponderada",
    "media_relativa_25_50": "Média relativa 25%–50%",
}


def _formula_label_short(formula_id: str) -> str:
    if formula_id in _FORMULA_SHORT_LABELS:
        return _FORMULA_SHORT_LABELS[formula_id]
    lab = FORMULA_LABELS.get(formula_id, "") or ""
    if len(lab) <= 28:
        return lab or _FORMULA_SHORT_LABELS["media_aritmetica_precos_obtidos"]
    return lab[:25].rstrip() + "…"


def _cnpj_digits_key(raw: str) -> str:
    return re.sub(r"\D", "", raw or "")


def _fornecedores_capa_from_grupos(grupos: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    by_key: Dict[str, Dict[str, str]] = {}
    order: List[str] = []
    for g in grupos or []:
        for f in g.get("fontes") or []:
            if not isinstance(f, dict):
                continue
            raw_cnpj = str(f.get("cnpj") or "").strip()
            key = _cnpj_digits_key(raw_cnpj)
            if len(key) != 14:
                continue
            cnpj_fmt = _normalize_cnpj(raw_cnpj)
            nv = (str(f.get("fornecedor") or "").strip() or "")[:400]
            if key not in by_key:
                capa_nome = nv if nome_fornecedor_e_util_para_exibicao(nv) else ("Não informado" if nv else "—")
                if not nv or nv == "—":
                    capa_nome = "—"
                by_key[key] = {
                    "fornecedor": capa_nome[:400],
                    "cnpj": cnpj_fmt,
                    "telefone": str(f.get("telefone") or "").strip()[:64],
                    "email": str(f.get("email") or "").strip()[:255],
                    "endereco": str(f.get("endereco") or "").strip()[:400],
                }
                order.append(key)
                continue
            ex = by_key[key]
            if nv and nome_fornecedor_e_util_para_exibicao(nv):
                ex_fn = ex["fornecedor"]
                if (
                    not ex_fn
                    or ex_fn in {"—", "Não informado"}
                    or not nome_fornecedor_e_util_para_exibicao(ex_fn)
                ):
                    ex["fornecedor"] = nv
            for fld, mx in (("telefone", 64), ("email", 255), ("endereco", 400)):
                v2 = str(f.get(fld) or "").strip()[:mx]
                if v2 and not ex.get(fld, ""):
                    ex[fld] = v2

    def _ni(v: str, *, field: str = "") -> str:
        if v:
            return v
        if field == "email":
            return EMAIL_INDISPONIVEL_RF
        return "Não informado"

    return [
        {
            "fornecedor": by_key[k]["fornecedor"],
            "cnpj": by_key[k]["cnpj"],
            "telefone": _ni(by_key[k].get("telefone", "")),
            "email": _ni(by_key[k].get("email", ""), field="email"),
            "endereco": _ni(by_key[k].get("endereco", "")),
        }
        for k in order
    ]


_SERVICES_DIR = Path(__file__).resolve().parent


def _repo_root_from_pdf_module() -> Optional[Path]:
    """Raiz do monorepo (pasta que contém `backend/` e `frontend-vue/`)."""
    try:
        return Path(__file__).resolve().parents[3]
    except IndexError:
        return None


def _dedupe_paths(paths: List[Path]) -> List[Path]:
    seen: Set[str] = set()
    out: List[Path] = []
    for p in paths:
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out

# ---------------------------------------------------------------------------
# Extração de CNPJ em textos / JSON de `source` dos itens
# ---------------------------------------------------------------------------
_CNPJ_LOOSE = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}")


def _normalize_cnpj(raw: str) -> str:
    d = re.sub(r"\D", "", raw)
    if len(d) != 14:
        return raw.strip()
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"


def _walk_cnpjs(obj: Any, acc: Set[str]) -> None:
    if isinstance(obj, dict):
        for v in obj.values():
            _walk_cnpjs(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _walk_cnpjs(v, acc)
    elif isinstance(obj, str):
        for m in _CNPJ_LOOSE.finditer(obj):
            acc.add(_normalize_cnpj(m.group()))


def extrair_cnpjs_dos_itens(itens: List[Any]) -> List[str]:
    acc: Set[str] = set()
    for it in itens:
        src = getattr(it, "source", None)
        if isinstance(src, dict):
            _walk_cnpjs(src, acc)
    return sorted(acc)


def extrair_cnpjs_das_fontes_grupos(grupos: List[Dict[str, Any]]) -> List[str]:
    acc: Set[str] = set()
    for g in grupos or []:
        fontes = g.get("fontes") or []
        if not isinstance(fontes, list):
            continue
        for f in fontes:
            if not isinstance(f, dict):
                continue
            raw = str(f.get("cnpj") or "").strip()
            digits = re.sub(r"\D", "", raw)
            if len(digits) == 14:
                acc.add(_normalize_cnpj(digits))
    return sorted(acc)


def _png_bytes_for_pdf_header(raw: bytes) -> bytes:
    """Evita HTML gigante (base64) com logos PNG muito grandes — timeout em proxy/browser."""
    try:
        from PIL import Image
    except ImportError:
        return raw
    try:
        im = Image.open(io.BytesIO(raw))
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA")
        w, h = im.size
        max_side = 400
        if max(w, h) <= max_side and len(raw) < 50_000:
            return raw
        ratio = max_side / max(w, h)
        nw, nh = max(1, int(w * ratio)), max(1, int(h * ratio))
        im = im.resize((nw, nh), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        im.save(out, format="PNG", optimize=True, compress_level=9)
        return out.getvalue()
    except Exception:
        return raw


def _logo_png_data_url() -> str:
    """PNG do sistema em data URL para o cabeçalho do PDF (WeasyPrint).

    Ordem (após ``PNCP_RELATORIO_LOGO_PATH`` se definido no settings):

    1. ``frontend-vue/src/assets/fonte_de_preços.png`` (nome atual; lido em dev direto do repo).
    2. ``fonte_de_preço.png`` / ``fonte_de_preços.png`` em ``backend/app/services/`` (deploy sem frontend).
    3. Logos legadas / genéricas.

    Mantém ``fonte_de_preço.png`` (singular) nos caminhos do frontend como compatibilidade.
    """
    override = (getattr(settings, "PNCP_RELATORIO_LOGO_PATH", None) or "").strip()
    base = Path(getattr(settings, "BASE_DIR", "") or ".").resolve()

    candidates: List[Path] = []
    if override:
        candidates.append(Path(override).expanduser())

    # Nome canónico atual no frontend (plural: preços).
    _names_primary = ("fonte_de_preços.png",)
    _names_compat = ("fonte_de_preço.png",)

    def _append_assets_dir(assets_dir: Path) -> None:
        for name in _names_primary + _names_compat:
            candidates.append(assets_dir / name)

    root = _repo_root_from_pdf_module()
    if root is not None:
        _append_assets_dir(root / "frontend-vue" / "src" / "assets")

    # BASE_DIR típico = …/backend → assets ao lado
    _append_assets_dir(base.parent / "frontend-vue" / "src" / "assets")
    # BASE_DIR = raiz do repositório (alguns arranques)
    _append_assets_dir(base / "frontend-vue" / "src" / "assets")

    for name in _names_primary + _names_compat:
        candidates.append(_SERVICES_DIR / name)

    candidates.append(_SERVICES_DIR / "docmaster_logo_relatorio.png")
    candidates.extend(
        [
            base.parent / "frontend-vue" / "src" / "assets" / "logo_branca.png",
            base.parent / "frontend-vue" / "src" / "assets" / "logo_brancad.png",
            base / "frontend-vue" / "src" / "assets" / "logo_branca.png",
            base / "frontend-vue" / "src" / "assets" / "logo_brancad.png",
        ]
    )
    candidates.append(_SERVICES_DIR / "logo_branca.png")

    for p in _dedupe_paths(candidates):
        try:
            if p.is_file():
                raw = _png_bytes_for_pdf_header(p.read_bytes())
                b64 = base64.b64encode(raw).decode("ascii")
                return f"data:image/png;base64,{b64}"
        except Exception:
            continue
    return ""


def nome_sistema_relatorio() -> str:
    return getattr(settings, "PNCP_RELATORIO_SISTEMA_NOME", "DocMaster — Pesquisador PNCP")


def carregar_css_relatorio_pesquisa_precos() -> str:
    """CSS compartilhado com frontend-vue (`relatorio-pesquisa-precos.css`).

    Densidade do PDF: variáveis em `.rpp-body.rpp--pdf` no CSS e truncamento em
    `pncp_relatorio_pdf_layout` (`sanear_grupos_relatorio_para_pdf`, capa).
    """
    override = (getattr(settings, "PNCP_RELATORIO_CSS_PATH", None) or "").strip()
    if override:
        p = Path(override).expanduser()
        if p.is_file():
            return p.read_text(encoding="utf-8")
    here = Path(__file__).resolve().parent / "relatorio-pesquisa-precos.css"
    if here.is_file():
        return here.read_text(encoding="utf-8")
    monorepo = Path(settings.BASE_DIR).resolve().parent / "frontend-vue" / "src" / "assets" / "relatorio-pesquisa-precos.css"
    if monorepo.is_file():
        return monorepo.read_text(encoding="utf-8")
    raise FileNotFoundError(
        "relatorio-pesquisa-precos.css não encontrado. Copie o arquivo do frontend-vue para "
        "backend/app/services/ ou defina PNCP_RELATORIO_CSS_PATH."
    )


@dataclass
class RelatorioCotacaoContext:
    titulo_relatorio: str
    titulo_cotacao: str
    data_pesquisa_exibicao: str
    emitido_em_exibicao: str
    criado_por: str
    criado_por_email: str
    termo_pncp: str
    total_itens: int
    total_linhas_cotacao: int
    grupos: List[Dict[str, Any]]
    cnpjs_fontes: List[str]
    qr_data_url: str
    logo_data_url: str
    marca_agua_texto: str
    anexo_fornecedor_url: str
    formula_calculo_id: str
    formula_calculo_label: str
    formula_calculo_label_short: str
    orgao_exibicao: str
    valor_total_estimado_fmt: str
    fornecedores_capa: List[Dict[str, str]]
    documento_tecnico_lead: str


def _parse_qtd_br(v: Any) -> float:
    s = str(v or "").strip()
    if not s:
        return 0.0
    m = re.search(r"\d[\d\.,]*", s)
    if not m:
        return 0.0
    num = m.group(0)
    if "," in num:
        num = num.replace(".", "").replace(",", ".")
    else:
        num = num.replace(",", "")
    try:
        n = float(num)
        return n if n > 0 else 0.0
    except Exception:
        return 0.0


def _obter_modalidade(tipo: Any) -> str:
    raw = str(tipo or "").strip()
    if not raw:
        return "N/D"
    m = {
        "PNCP": "Pregão Eletrônico",
        "BBMNET": "Dispensa",
        "CMED": "Pregão Eletrônico",
        "Cotação Direta": "Dispensa",
        "ComprasGov": "Pregão",
    }
    return m.get(raw, raw)


def _obter_fonte(tipo: Any) -> str:
    raw = str(tipo or "").strip()
    if not raw:
        return "N/D"
    return "PNCP" if raw in {"Cotação Direta", "BBMNET", "ComprasGov", "CMED"} else raw


def _obter_uf(municipio_uf: Any) -> str:
    raw = str(municipio_uf or "").strip()
    if not raw:
        return "—"
    parts = raw.split("/")
    if len(parts) >= 2:
        return str(parts[-1] or "").strip() or "—"
    return "—"


def montar_contexto_relatorio(
    *,
    cotacao,
    itens_qs,
    titulo_relatorio: str,
    url_verificacao: str,
    anexo_fornecedor_url: str = "",
    formula_id: str = "media_aritmetica_precos_obtidos",
    skip_email_http_prefetch: bool = False,
) -> RelatorioCotacaoContext:
    itens = list(itens_qs.order_by("id"))
    cotacoes_qs = getattr(cotacao, "cotacoes_itens", None)
    cotacoes = list(cotacoes_qs.select_related("item").order_by("item_id", "id")) if cotacoes_qs is not None else []
    pdf_receitaws_email = receitaws_email_fallback_enabled() and not skip_email_http_prefetch
    pdf_email_max = pdf_receitaws_max_http_lookups() if pdf_receitaws_email else 0
    if cotacoes:
        grupos, total_linhas = agrupar_cotacoes_por_item_relatorio_pesquisa_precos(
            itens,
            cotacoes,
            receitaws_email_fallback=pdf_receitaws_email,
            # Job PDF: cache-first, sem sleep 21s entre HTTP (estoura timeout do worker).
            receitaws_allow_wait=False,
            receitaws_unlimited=False,
            receitaws_max_http=pdf_email_max,
        )
    else:
        grupos, total_linhas = agrupar_itens_relatorio_pesquisa_precos(
            itens,
            receitaws_email_fallback=pdf_receitaws_email,
            receitaws_allow_wait=False,
            receitaws_unlimited=False,
            receitaws_max_http=pdf_email_max,
        )
    sanear_grupos_relatorio_para_pdf(grupos)
    # Prioriza CNPJs presentes nas fontes (cotações reais exibidas no relatório).
    cnpjs = extrair_cnpjs_das_fontes_grupos(grupos)
    if not cnpjs:
        cnpjs = extrair_cnpjs_dos_itens(itens)

    tz = timezone.get_current_timezone()
    agora = timezone.now()
    emitido = timezone.localtime(agora, tz)
    criado = timezone.localtime(cotacao.created_at, tz) if cotacao.created_at else emitido

    snap_nome = (getattr(cotacao, "criado_por_nome", None) or "").strip()
    u = cotacao.usuario
    criado_por = snap_nome or (u.get_full_name() or "").strip() or getattr(u, "email", "") or str(u.pk)
    snap_email = (getattr(cotacao, "criado_por_email", None) or "").strip()
    criado_email = snap_email or (getattr(u, "email", None) or "").strip()
    orgao_exibicao = sanear_texto_capa_pdf(
        texto_orgao_exibicao_relatorio_pesquisa_precos(cotacao, u, grupos)
    )
    valor_total_estimado = 0.0
    for g in grupos:
        fontes = g.get("fontes") or []
        for f in fontes:
            if not isinstance(f, dict):
                continue
            f["modalidade_label"] = _obter_modalidade(f.get("tipo"))
            f["fonte_label"] = _obter_fonte(f.get("tipo"))
            f["uf_label"] = _obter_uf(f.get("municipio_uf"))
        try:
            total_item = float(g.get("valor_total_item")) if g.get("valor_total_item") is not None else None
        except (TypeError, ValueError):
            total_item = None
        if total_item is None:
            qtd = _parse_qtd_br(g.get("quantidade_fmt"))
            try:
                media = float(g.get("media_valor")) if g.get("media_valor") is not None else None
            except (TypeError, ValueError):
                media = None
            total_item = total_item_de_media_unitaria_exibida(media, qtd) or 0.0
        g["valor_total_item"] = total_item
        g["valor_total_item_fmt"] = f"R$ {_formatar_moeda_br(total_item)}"
        valor_total_estimado += total_item

    return RelatorioCotacaoContext(
        titulo_relatorio=(titulo_relatorio or "").strip()[:500],
        titulo_cotacao=truncar_texto_pdf(cotacao.titulo or "—", PDF_CAPA_TITULO_COTACAO_MAX),
        data_pesquisa_exibicao=criado.strftime("%d/%m/%Y às %H:%M"),
        emitido_em_exibicao=emitido.strftime("%d/%m/%Y às %H:%M"),
        criado_por=truncar_texto_pdf(criado_por, PDF_CAPA_RESPONSAVEL_MAX),
        criado_por_email=criado_email,
        termo_pncp=truncar_texto_pdf(cotacao.termo_busca or "—", PDF_TERMO_PNCP_MAX),
        total_itens=len(grupos),
        total_linhas_cotacao=total_linhas,
        grupos=grupos,
        cnpjs_fontes=cnpjs,
        qr_data_url=qr_png_data_url(url_verificacao),
        logo_data_url=_logo_png_data_url(),
        marca_agua_texto=nome_sistema_relatorio(),
        anexo_fornecedor_url=(anexo_fornecedor_url or "").strip(),
        formula_calculo_id=formula_id,
        formula_calculo_label=FORMULA_LABELS.get(formula_id, FORMULA_LABELS["media_aritmetica_precos_obtidos"]),
        formula_calculo_label_short=_formula_label_short(formula_id),
        orgao_exibicao=orgao_exibicao,
        valor_total_estimado_fmt=f"R$ {_formatar_moeda_br(valor_total_estimado)}",
        fornecedores_capa=_fornecedores_capa_from_grupos(grupos),
        documento_tecnico_lead=DOCUMENTO_TECNICO_LEAD,
    )


_ENV = Environment(
    loader=BaseLoader(),
    autoescape=select_autoescape(["html", "xml"]),
)


_HTML_TEMPLATE = _ENV.from_string(
'<!DOCTYPE html>\n<html lang="pt-BR" class="rpp rpp--pdf">\n<head>\n  <meta charset="utf-8" />\n  <style>{{ rpp_css | safe }}</style>\n</head>\n<body class="rpp-body rpp--pdf">\n  <header id="rpp-head-main" class="rpp-head-main rpp-head-main--card-white">\n    <div class="rpp-head-main__grid">\n      <div class="rpp-head-main__spacer" aria-hidden="true"></div>\n      <div class="rpp-head-main__brand">\n        {% if ctx.logo_data_url %}\n        <img class="rpp-head-main__logo" src="{{ ctx.logo_data_url }}" alt="DocMaster" />\n        {% else %}\n        <span class="rpp-brand-mark">DocMaster</span>\n        {% endif %}\n      </div>\n      <div class="rpp-head-main__qr-wrap">\n        <img class="rpp-head-main__qr" src="{{ ctx.qr_data_url }}" alt="" />\n      </div>\n    </div>\n  </header>\n\n  <div class="rpp-page">\n    <header class="rpp-hero">\n      <h1 class="rpp-hero__title">Relatório de pesquisa de preços</h1>\n      <p class="rpp-hero__lead">{{ ctx.titulo_cotacao }}</p>\n      <p class="rpp-hero__muted">{{ ctx.documento_tecnico_lead }}</p>\n    </header>\n\n    <div class="rpp-info-grid">\n      <div class="rpp-info-card">\n        <div class="rpp-info-card__row">\n          <span class="rpp-emo" aria-hidden="true">🏛️</span>\n          <span class="rpp-info-card__label">Órgão</span>\n        </div>\n        <p class="rpp-info-card__value">{{ ctx.orgao_exibicao }}</p>\n      </div>\n      <div class="rpp-info-card">\n        <div class="rpp-info-card__row">\n          <span class="rpp-emo" aria-hidden="true">👤</span>\n          <span class="rpp-info-card__label">Responsável</span>\n        </div>\n        <p class="rpp-info-card__value">{{ ctx.criado_por }}</p>\n      </div>\n      <div class="rpp-info-card">\n        <div class="rpp-info-card__row">\n          <span class="rpp-emo" aria-hidden="true">📅</span>\n          <span class="rpp-info-card__label">Data da pesquisa</span>\n        </div>\n        <p class="rpp-info-card__value">{{ ctx.data_pesquisa_exibicao }}</p>\n      </div>\n      <div class="rpp-info-card">\n        <div class="rpp-info-card__row">\n          <span class="rpp-emo" aria-hidden="true">Σ</span>\n          <span class="rpp-info-card__label">Método aplicado</span>\n        </div>\n        <p class="rpp-info-card__value">{{ ctx.formula_calculo_label_short }}</p>\n      </div>\n      <div class="rpp-info-card rpp-info-card--strong">\n        <div class="rpp-info-card__row">\n          <span class="rpp-emo" aria-hidden="true">✓</span>\n          <span class="rpp-info-card__label">Valor total estimado</span>\n        </div>\n        <p class="rpp-info-card__value rpp-info-card__value--money">{{ ctx.valor_total_estimado_fmt }}</p>\n      </div>\n    </div>\n\n    <section class="rpp-panel rpp-panel--padded">\n      <div class="rpp-panel__head">\n        <div>\n          <h2 class="rpp-panel__title">Metodologia aplicada</h2>\n          <p class="rpp-panel__subtitle">Base legal, método matemático e critérios técnicos adotados</p>\n        </div>\n        <span class="rpp-chip">IN 65/2021 · Lei 14.133</span>\n      </div>\n      <div class="rpp-prose">\n        <p>A pesquisa foi realizada com base na Lei nº 14.133/2021 e na IN nº 65/2021.</p>\n        <p>\n          As cotações selecionadas foram obtidas por meio de consultas ao Portal Nacional de Contratações Públicas – PNCP,\n          bancos de dados públicos e pesquisa direta de mercado, observando-se a compatibilidade da descrição do objeto,\n          a unidade de medida, a recência das informações, a natureza da contratação e a consistência dos dados utilizados\n          para formação do preço estimado.\n        </p>\n        <p>Os valores estimados mostram-se compatíveis com o mercado e adequados para subsidiar a contratação.</p>\n      </div>\n      <div class="rpp-mini-metrics">\n        <div class="rpp-mini-metric">\n          <div class="rpp-mini-metric__label">Critério</div>\n          <strong class="rpp-mini-metric__value">Compatibilidade</strong>\n        </div>\n        <div class="rpp-mini-metric">\n          <div class="rpp-mini-metric__label">Recência</div>\n          <strong class="rpp-mini-metric__value">Até 12 meses</strong>\n        </div>\n        <div class="rpp-mini-metric">\n          <div class="rpp-mini-metric__label">Rastreabilidade</div>\n          <strong class="rpp-mini-metric__value">CNPJ, fonte e data</strong>\n        </div>\n      </div>\n    </section>\n\n    <section class="rpp-panel rpp-panel--flush">\n      <div class="rpp-panel__bar">\n        <div>\n          <h2 class="rpp-panel__title">Resultado consolidado</h2>\n          <p class="rpp-panel__subtitle">Resumo dos itens com média definida e situação da pesquisa</p>\n        </div>\n      </div>\n      <div class="rpp-table-scroll">\n        <table class="rpp-table rpp-table--consolidado">\n          <thead>\n            <tr>\n              <th class="rpp-th rpp-th--narrow">Item</th>\n              <th class="rpp-th rpp-th--wide">Descrição</th>\n              <th class="rpp-th">Quantidade</th>\n              <th class="rpp-th">Cotações válidas</th>\n              <th class="rpp-th">Média</th>\n              <th class="rpp-th rpp-th--accent">Valor total</th>\n            </tr>\n          </thead>\n          <tbody>\n            {% for g in ctx.grupos %}\n            <tr>\n              <td class="rpp-td rpp-td--num">{{ g.ordem }}</td>\n              <td class="rpp-td"><div class="rpp-td-name">{{ g.nome }}</div></td>\n              <td class="rpp-td">{{ g.quantidade_fmt }} {{ g.unidade }}</td>\n              <td class="rpp-td">{{ g.n_cotacoes }}</td>\n              <td class="rpp-td rpp-td--medium">{{ g.media_fmt }}</td>\n              <td class="rpp-td rpp-td--money">{{ g.valor_total_item_fmt }}</td>\n            </tr>\n            {% else %}\n            <tr>\n              <td colspan="6" class="rpp-cnpj-empty">Nenhum item agrupado nesta cotação.</td>\n            </tr>\n            {% endfor %}\n          </tbody>\n        </table>\n      </div>\n    </section>\n\n    <section class="rpp-panel rpp-panel--flush">\n      <div class="rpp-panel__bar rpp-panel__bar--simple">\n        <div>\n          <h2 class="rpp-panel__title">Detalhamento dos itens</h2>\n          <p class="rpp-panel__subtitle">Ficha técnica do item e fontes utilizadas na composição do preço</p>\n        </div>\n      </div>\n      <div class="rpp-detail-list">\n        {% for g in ctx.grupos %}\n        <article class="rpp-detalhe-item">\n          <div class="rpp-detalhe-item__body">\n          <header class="rpp-detalhe-item__head">\n            <span class="rpp-detalhe-item__kicker">Item {{ g.ordem }}</span>\n            <div class="rpp-detalhe-item__nome">{{ g.nome }}</div>\n          </header>\n          <div class="rpp-fontes-cards">\n            {% for f in g.fontes %}\n            <div class="rpp-fonte-card">\n              <div class="rpp-fonte-card__index">{{ loop.index }}</div>\n              <div class="rpp-fonte-card__content">\n                <div class="rpp-fonte-stack">\n                <div class="rpp-fonte-card__lead">\n                <div class="rpp-fonte-fields">\n                <div class="rpp-fonte-row rpp-fonte-row--1">\n                  <div class="rpp-mini-compact rpp-mini-compact--featured">\n                    <span class="rpp-mini-compact__label">Fornecedor</span>\n                    <span class="rpp-mini-compact__value rpp-mini-compact__value--strong">{{ f.fornecedor }}</span>\n                  </div>\n                </div>\n                <div class="rpp-fonte-row rpp-fonte-row--pair">\n                  <div class="rpp-mini-compact">\n                    <span class="rpp-mini-compact__label">CNPJ</span>\n                    <span class="rpp-mini-compact__value">{{ f.cnpj }}</span>\n                  </div>\n                  <div class="rpp-mini-compact rpp-mini-compact--featured">\n                    <span class="rpp-mini-compact__label">Valor</span>\n                    <span class="rpp-mini-compact__value rpp-mini-compact__value--strong">{{ f.valor }}</span>\n                  </div>\n                </div>\n                <div class="rpp-fonte-row rpp-fonte-row--1">\n                  <div class="rpp-mini-compact">\n                    <span class="rpp-mini-compact__label">Órgão</span>\n                    <span class="rpp-mini-compact__value">{{ f.orgao }}</span>\n                  </div>\n                </div>\n                <div class="rpp-fonte-row rpp-fonte-row--pair">\n                  <div class="rpp-mini-compact">\n                    <span class="rpp-mini-compact__label">Modalidade</span>\n                    <span class="rpp-mini-compact__value">{{ f.modalidade_label }}</span>\n                  </div>\n                  <div class="rpp-mini-compact">\n                    <span class="rpp-mini-compact__label">Data</span>\n                    <span class="rpp-mini-compact__value">{{ f.data }}</span>\n                  </div>\n                </div>\n                </div>\n                <div class="rpp-fonte-processo-line">\n                  <table class="rpp-processo-tbl" role="presentation">\n                    <tr>\n                      <td class="rpp-processo-tbl__k">Link</td>\n                      <td class="rpp-processo-tbl__v">{% if f.link_pncp %}<a href="{{ f.link_pncp }}" class="rpp-processo-link">Link de acesso do processo</a>{% else %}N/D{% endif %}</td>\n                    </tr>\n                  </table>\n                </div>\n                <div class="rpp-fonte-row rpp-fonte-row--4">\n                  <div class="rpp-mini-compact">\n                    <span class="rpp-mini-compact__label">Qtd.</span>\n                    <span class="rpp-mini-compact__value">{{ g.quantidade_fmt }}</span>\n                  </div>\n                  <div class="rpp-mini-compact">\n                    <span class="rpp-mini-compact__label">Unid.</span>\n                    <span class="rpp-mini-compact__value">{{ g.unidade }}</span>\n                  </div>\n                  <div class="rpp-mini-compact">\n                    <span class="rpp-mini-compact__label">Fonte</span>\n                    <span class="rpp-mini-compact__value">{{ f.fonte_label }}</span>\n                  </div>\n                  <div class="rpp-mini-compact">\n                    <span class="rpp-mini-compact__label">UF</span>\n                    <span class="rpp-mini-compact__value">{{ f.uf_label }}</span>\n                  </div>\n                </div>\n                </div>\n                <div class="rpp-fonte-card__tail">\n                <div class="rpp-fonte-row rpp-fonte-row--2">\n                  <div class="rpp-mini-compact rpp-mini-compact--wide">\n                    <span class="rpp-mini-compact__label">Descrição do item</span>\n                    <span class="rpp-mini-compact__value">{{ f.descricao_fonte }}</span>\n                  </div>\n                  <div class="rpp-mini-compact rpp-mini-compact--wide">\n                    <span class="rpp-mini-compact__label">Ajuste</span>\n                    <span class="rpp-mini-compact__value">{{ f.ajuste }}</span>\n                  </div>\n                </div>\n                </div>\n                </div>\n              </div>\n            </div>\n            {% endfor %}\n          </div>\n          </div>\n        </article>\n        {% endfor %}\n      </div>\n    </section>\n\n    <section class="rpp-panel rpp-panel--padded">\n      <div class="rpp-icon-title">\n        <div class="rpp-icon-title__bubble">✓</div>\n        <div>\n          <h2 class="rpp-panel__title">Conclusão técnica</h2>\n          <p class="rpp-panel__subtitle">Síntese conclusiva da pesquisa de preços</p>\n        </div>\n      </div>\n      <div class="rpp-quote">\n        <p>\n          Com base nas cotações obtidas, na metodologia aplicada e na análise técnica dos dados, conclui-se que os valores\n          estimados refletem adequadamente os preços praticados no mercado, estando aptos a subsidiar a contratação pública\n          pretendida, com observância aos princípios da economicidade, razoabilidade e eficiência.\n        </p>\n      </div>\n    </section>\n\n    <section class="rpp-panel rpp-panel--padded">\n      <div class="rpp-icon-title">\n        <div class="rpp-icon-title__bubble rpp-icon-title__bubble--alt">🛡️</div>\n        <div>\n          <h2 class="rpp-panel__title">Responsabilidade sobre as informações</h2>\n          <p class="rpp-panel__subtitle">Esclarecimento quanto ao uso da plataforma</p>\n        </div>\n      </div>\n      <div class="rpp-quote rpp-quote--stack">\n        <p>\n          A plataforma disponibiliza um ambiente digital de apoio à pesquisa de preços, no qual são consolidadas informações\n          oriundas de diferentes origens, tais como bases públicas, sistemas oficiais e registros de mercado, com o objetivo\n          de auxiliar na formação de referência de valores.\n        </p>\n        <p>\n          Compete exclusivamente ao servidor público responsável pela pesquisa a análise crítica, validação, seleção e\n          utilização dos preços, em conformidade com a legislação vigente, especialmente a Lei nº 14.133/2021, normativos\n          aplicáveis e orientações dos órgãos de controle.\n        </p>\n        <p>\n          Dessa forma, a plataforma atua como ferramenta de apoio à tomada de decisão, não substituindo o dever de diligência,\n          responsabilidade técnica e julgamento administrativo do agente público.\n        </p>\n      </div>\n    </section>\n\n    <section class="rpp-panel rpp-panel--padded">\n      <div class="rpp-icon-title">\n        <div class="rpp-icon-title__bubble rpp-icon-title__bubble--alt">🏛️</div>\n        <div>\n          <h2 class="rpp-panel__title">Informações dos fornecedores</h2>\n          <p class="rpp-panel__subtitle">Dados cadastrais e de contato</p>\n        </div>\n      </div>\n      {% if ctx.fornecedores_capa %}\n      <div class="rpp-fornecedores-grid">\n        {% for fo in ctx.fornecedores_capa %}\n        <article class="rpp-fornecedor-card">\n          <div class="rpp-fornecedor-card__name">{{ fo.fornecedor }}</div>\n          <div class="rpp-fornecedor-card__lines">\n            <div><span class="rpp-fornecedor-card__k">CNPJ:</span> {{ fo.cnpj }}</div>\n            <div><span class="rpp-fornecedor-card__k">Telefone:</span> {{ fo.telefone }}</div>\n            <div><span class="rpp-fornecedor-card__k">Email:</span> {{ fo.email }}</div>\n            <div><span class="rpp-fornecedor-card__k">Endereço:</span> {{ fo.endereco }}</div>\n          </div>\n        </article>\n        {% endfor %}\n      </div>\n      {% else %}\n      <p class="rpp-cnpj-empty">Nenhum CNPJ estruturado foi localizado nas fontes desta pesquisa.</p>\n      {% endif %}\n    </section>\n  </div>\n</body>\n</html>\n'
)


def renderizar_html_relatorio(ctx: RelatorioCotacaoContext) -> str:
    return _HTML_TEMPLATE.render(
        ctx=ctx,
        rpp_css=carregar_css_relatorio_pesquisa_precos(),
    )


def gerar_pdf_relatorio_cotacao(
    *,
    cotacao,
    itens_qs,
    titulo_relatorio: str,
    url_verificacao: str,
    anexo_fornecedor_url: str = "",
    formula_id: str = "media_aritmetica_precos_obtidos",
    skip_email_http_prefetch: bool = False,
) -> bytes:
    ctx = montar_contexto_relatorio(
        cotacao=cotacao,
        itens_qs=itens_qs,
        titulo_relatorio=titulo_relatorio,
        url_verificacao=url_verificacao,
        anexo_fornecedor_url=anexo_fornecedor_url,
        formula_id=formula_id,
        skip_email_http_prefetch=skip_email_http_prefetch,
    )
    html = renderizar_html_relatorio(ctx)
    base_url = _SERVICES_DIR.as_uri() + "/"
    return HTML(string=html, base_url=base_url).write_pdf()


def _slug_part(value: str, max_len: int = 40) -> str:
    raw = (value or "").strip().lower()
    raw = re.sub(r"[^\w\s-]", "", raw, flags=re.UNICODE)
    raw = re.sub(r"[-\s]+", "-", raw, flags=re.UNICODE).strip("-")
    if not raw:
        return ""
    return raw[:max_len]


def nome_arquivo_relatorio(
    cotacao_id: int,
    titulo_relatorio: str,
    *,
    sistema_nome: str = "",
    usuario_nome: str = "",
    dt=None,
    ext: str = "pdf",
) -> str:
    now = dt or timezone.now()
    stamp = timezone.localtime(now).strftime("%Y%m%d-%H%M")
    sistema = _slug_part(sistema_nome, max_len=26) or "docmaster-pesquisador-pncp"
    usuario = _slug_part(usuario_nome, max_len=26) or "usuario"
    titulo = _slug_part(titulo_relatorio, max_len=42) or "relatorio"
    suffix = str(ext or "pdf").lstrip(".").lower() or "pdf"
    return f"{sistema}_{usuario}_{stamp}_cotacao-{int(cotacao_id)}_{titulo}.{suffix}"


def usuario_nome_export_cotacao(cotacao) -> str:
    """Nome do responsável para nomenclatura de arquivos exportados (PDF/Excel)."""
    snap = (getattr(cotacao, "criado_por_nome", None) or "").strip()
    if snap:
        return snap
    u = getattr(cotacao, "usuario", None)
    if u is None:
        return "usuario"
    full = ""
    if callable(getattr(u, "get_full_name", None)):
        try:
            full = (u.get_full_name() or "").strip()
        except Exception:
            full = ""
    if not full:
        first = (getattr(u, "first_name", None) or "").strip()
        last = (getattr(u, "last_name", None) or "").strip()
        full = f"{first} {last}".strip()
    return full or (getattr(u, "email", None) or "").strip() or str(getattr(u, "pk", "usuario"))
