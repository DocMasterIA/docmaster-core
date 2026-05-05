"""
Relatório PDF de cotações PNCP — esquema inicial (WeasyPrint).

Objetivo do módulo (especificação institucional):
- Gerar relatórios estruturados em PDF a partir das cotações, com consolidação
  organizada e padronizada para uso institucional.
- Estrutura clara: título personalizado (definido na geração), data da pesquisa,
  itens consolidados, CNPJs extraídos das fontes quando disponíveis.
- Marca d’água com identificação do sistema.
- QR Code com URL do SPA para abrir a cotação no sistema (utilizador autenticado).
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

from backend.app.services.pncp_relatorio_itens import (
    FORMULA_LABELS,
    agrupar_cotacoes_por_item_relatorio_pesquisa_precos,
    agrupar_itens_relatorio_pesquisa_precos,
)

_SERVICES_DIR = Path(__file__).resolve().parent

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
            cnpj = _normalize_cnpj(raw)
            if cnpj:
                acc.add(cnpj)
    return sorted(acc)


# ---------------------------------------------------------------------------
# QR Code (PNG em data URL para embutir no HTML)
# ---------------------------------------------------------------------------
def _qr_png_data_url(payload: str) -> str:
    import qrcode

    qr = qrcode.QRCode(version=None, box_size=4, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1f4e79", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def nome_sistema_relatorio() -> str:
    return getattr(settings, "PNCP_RELATORIO_SISTEMA_NOME", "DocMaster — Pesquisador PNCP")


def carregar_css_relatorio_pesquisa_precos() -> str:
    """CSS compartilhado com frontend-vue (`relatorio-pesquisa-precos.css`)."""
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
    marca_agua_texto: str
    anexo_fornecedor_url: str
    formula_calculo_id: str
    formula_calculo_label: str
    orgao_exibicao: str
    valor_total_estimado_fmt: str


def _formatar_moeda_br(v: Any) -> str:
    if v is None:
        return "—"
    try:
        n = float(v)
    except (TypeError, ValueError):
        return "—"
    s = f"{n:.2f}"
    inteiro, frac = s.split(".")
    return f"{inteiro},{frac}"


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


def montar_contexto_relatorio(
    *,
    cotacao,
    itens_qs,
    titulo_relatorio: str,
    url_verificacao: str,
    anexo_fornecedor_url: str = "",
    formula_id: str = "media_aritmetica_precos_obtidos",
) -> RelatorioCotacaoContext:
    itens = list(itens_qs.order_by("id"))
    cotacoes_qs = getattr(cotacao, "cotacoes_itens", None)
    cotacoes = list(cotacoes_qs.select_related("item").order_by("item_id", "id")) if cotacoes_qs is not None else []
    if cotacoes:
        grupos, total_linhas = agrupar_cotacoes_por_item_relatorio_pesquisa_precos(itens, cotacoes, formula_id)
    else:
        grupos, total_linhas = agrupar_itens_relatorio_pesquisa_precos(itens)
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
    orgao_exibicao = "—"
    for g in grupos:
        fontes = g.get("fontes") or []
        if fontes:
            org = str((fontes[0] or {}).get("orgao") or "").strip()
            if org:
                orgao_exibicao = org
                break
    valor_total_estimado = 0.0
    for g in grupos:
        qtd = _parse_qtd_br(g.get("quantidade_fmt"))
        try:
            media = float(g.get("media_valor")) if g.get("media_valor") is not None else 0.0
        except (TypeError, ValueError):
            media = 0.0
        total_item = (qtd * media) if (qtd > 0 and media > 0) else 0.0
        g["valor_total_item"] = total_item
        g["valor_total_item_fmt"] = f"R$ {_formatar_moeda_br(total_item)}"
        valor_total_estimado += total_item

    return RelatorioCotacaoContext(
        titulo_relatorio=(titulo_relatorio or "").strip()[:500],
        titulo_cotacao=cotacao.titulo or "—",
        data_pesquisa_exibicao=criado.strftime("%d/%m/%Y às %H:%M"),
        emitido_em_exibicao=emitido.strftime("%d/%m/%Y às %H:%M"),
        criado_por=criado_por,
        criado_por_email=criado_email,
        termo_pncp=cotacao.termo_busca or "—",
        total_itens=len(grupos),
        total_linhas_cotacao=total_linhas,
        grupos=grupos,
        cnpjs_fontes=cnpjs,
        qr_data_url=_qr_png_data_url(url_verificacao),
        marca_agua_texto=nome_sistema_relatorio(),
        anexo_fornecedor_url=(anexo_fornecedor_url or "").strip(),
        formula_calculo_id=formula_id,
        formula_calculo_label=FORMULA_LABELS.get(formula_id, FORMULA_LABELS["media_aritmetica_precos_obtidos"]),
        orgao_exibicao=orgao_exibicao,
        valor_total_estimado_fmt=f"R$ {_formatar_moeda_br(valor_total_estimado)}",
    )


_ENV = Environment(
    loader=BaseLoader(),
    autoescape=select_autoescape(["html", "xml"]),
)


_HTML_TEMPLATE = _ENV.from_string(
    """
<!DOCTYPE html>
<html lang="pt-BR" class="rpp rpp--pdf">
<head>
  <meta charset="utf-8" />
  <style>{{ rpp_css | safe }}</style>
</head>
<body class="rpp-body rpp--pdf">
  <div class="rpp-page">
    <div class="rpp-watermark">{{ ctx.marca_agua_texto }}</div>

    <header id="rpp-head-main" class="rpp-head-main">
      <div class="rpp-head-main__col rpp-head-main__col--logo">
        <img class="rpp-head-main__logo" src="logo_branca.png" alt="DocMaster" />
      </div>
      <div class="rpp-head-main__col rpp-head-main__col--main">
        <p class="rpp-kicker">Relatório institucional</p>
        <h1 class="rpp-title">{{ ctx.titulo_relatorio }}</h1>
        <p class="rpp-subtitle">Pesquisa de preços (PNCP)</p>
        <p class="rpp-subtitle rpp-subtitle--detail">
          Documento técnico consolidado com metodologia, rastreabilidade das cotações e conclusão para suporte à contratação.
        </p>
      </div>
      <div class="rpp-head-main__col rpp-head-main__col--qr">
        <img class="rpp-head-main__qr" src="{{ ctx.qr_data_url }}" alt="" />
      </div>
    </header>

    <div class="rpp-meta-grid">
      <div class="rpp-card">
        <span class="rpp-card__label">Órgão</span>
        <span class="rpp-card__value">{{ ctx.orgao_exibicao }}</span>
      </div>
      <div class="rpp-card">
        <span class="rpp-card__label">Responsável</span>
        <span class="rpp-card__value">{{ ctx.criado_por }}</span>
      </div>
      <div class="rpp-card">
        <span class="rpp-card__label">Data da pesquisa</span>
        <span class="rpp-card__value">{{ ctx.data_pesquisa_exibicao }}</span>
      </div>
      <div class="rpp-card">
        <span class="rpp-card__label">Método aplicado</span>
        <span class="rpp-card__value">{{ ctx.formula_calculo_label }}</span>
      </div>
      <div class="rpp-card rpp-card--accent">
        <span class="rpp-card__label">Valor total estimado</span>
        <span class="rpp-card__value">{{ ctx.valor_total_estimado_fmt }}</span>
      </div>
    </div>

    <section class="rpp-block">
      <h2 class="rpp-section-title">Metodologia Aplicada</h2>
      <p class="rpp-section-lead">Base legal, método matemático e critérios de seleção das cotações</p>
      <div class="rpp-metodologia">
        <h3 class="rpp-metodologia__title">IN 65/2021 · Lei 14.133</h3>
        <p>
          A presente pesquisa de preços foi materializada com base na Lei nº 14.133/2021 e na Instrução Normativa nº 65/2021,
          adotando como método matemático {{ ctx.formula_calculo_label|lower }}, em conformidade com os parâmetros definidos para esta cotação.
        </p>
        <p>
          Para composição do valor estimado, foram consideradas cotações provenientes de contratação direta, PNCP, CMED,
          ComprasGov e plataformas eletrônicas, observando compatibilidade do objeto, unidade de medida, recência da contratação,
          identificação do fornecedor e consistência dos dados.
        </p>
        <table class="rpp-table rpp-table--metodologia">
          <thead>
            <tr>
              <th>Critério de seleção</th>
              <th>Parâmetro aplicado</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Compatibilidade do objeto</td>
              <td>Descrição, unidade e quantidade equivalentes ao item pesquisado.</td>
            </tr>
            <tr>
              <td>Recência observada</td>
              <td>Até 12 meses.</td>
            </tr>
            <tr>
              <td>Rastreabilidade</td>
              <td>CNPJ, fonte e data.</td>
            </tr>
          </tbody>
        </table>
        <div class="rpp-mini-metrics">
          <div class="rpp-mini-metric">
            <span class="rpp-mini-metric__label">Critério</span>
            <strong class="rpp-mini-metric__value">Compatibilidade</strong>
          </div>
          <div class="rpp-mini-metric">
            <span class="rpp-mini-metric__label">Recência</span>
            <strong class="rpp-mini-metric__value">Até 12 meses</strong>
          </div>
          <div class="rpp-mini-metric">
            <span class="rpp-mini-metric__label">Rastreabilidade</span>
            <strong class="rpp-mini-metric__value">CNPJ, fonte e data</strong>
          </div>
        </div>
      </div>
    </section>

    <section class="rpp-block">
      <h2 class="rpp-section-title">Conclusão Técnica</h2>
      <p class="rpp-conclusao">
        Com base nas cotações obtidas, na metodologia aplicada e na análise técnica dos dados, conclui-se que os valores
        estimados refletem adequadamente os preços praticados no mercado, estando aptos a subsidiar a contratação pública
        pretendida, com observância aos princípios da economicidade, razoabilidade e eficiência.
      </p>
    </section>

    <section class="rpp-block">
      <h2 class="rpp-section-title">Responsabilidade sobre as informações</h2>
      <p class="rpp-conclusao">
        A plataforma disponibiliza um ambiente digital de apoio à pesquisa de preços, consolidando informações
        de bases públicas e registros de mercado para auxiliar a formação de referência.
      </p>
      <p class="rpp-conclusao">
        Compete exclusivamente ao servidor público responsável a análise crítica, validação, seleção e utilização
        dos preços, em conformidade com a Lei nº 14.133/2021 e normativos aplicáveis.
      </p>
      <p class="rpp-conclusao">
        Assim, a plataforma atua como ferramenta de apoio à decisão, não substituindo o dever de diligência e
        responsabilidade técnica do agente público.
      </p>
    </section>

    <section class="rpp-block">
      <h2 class="rpp-section-title">Resultado consolidado</h2>
      <p class="rpp-section-lead">Resumo dos itens com média definida e situação da pesquisa.</p>
      <div class="rpp-table-wrap">
        <table class="rpp-table rpp-table--consolidado">
          <thead>
            <tr>
              <th>Item</th>
              <th>Descrição</th>
              <th>Quantidade</th>
              <th>Cotações válidas</th>
              <th>Média</th>
              <th>Valor total</th>
            </tr>
          </thead>
          <tbody>
            {% for g in ctx.grupos %}
            <tr>
              <td>{{ g.ordem }}</td>
              <td>{{ g.nome }}</td>
              <td>{{ g.quantidade_fmt }} {{ g.unidade }}</td>
              <td>{{ g.n_cotacoes }}</td>
              <td>{{ g.media_fmt }}</td>
              <td>{{ g.valor_total_item_fmt }}</td>
            </tr>
            {% else %}
            <tr>
              <td colspan="6" class="rpp-cnpj-empty">Nenhum item agrupado nesta cotação.</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </section>

    <section class="rpp-block">
      <h2 class="rpp-section-title">Detalhamento dos itens</h2>
      <p class="rpp-section-lead">Ficha técnica do item e fontes utilizadas na composição do preço (cada linha importada é uma fonte; o mesmo produto agrupa 3 ou mais cotações).</p>
      {% for g in ctx.grupos %}
      <div class="rpp-detalhe-item">
        <div class="rpp-detalhe-item__head">
          <span class="rpp-detalhe-item__kicker">Item {{ g.ordem }}</span>
          <div class="rpp-detalhe-item__nome">{{ g.nome }}</div>
        </div>
        <div class="rpp-detalhe-item__meta">
          <div class="rpp-mini-card">
            <span class="rpp-mini-card__label">Identificação (ID do item)</span>
            <span class="rpp-mini-card__value">ID {{ g.ordem }}</span>
          </div>
          <div class="rpp-mini-card">
            <span class="rpp-mini-card__label">Quantidade</span>
            <span class="rpp-mini-card__value">{{ g.quantidade_fmt }}</span>
          </div>
          <div class="rpp-mini-card">
            <span class="rpp-mini-card__label">Unidade</span>
            <span class="rpp-mini-card__value">{{ g.unidade }}</span>
          </div>
        </div>
        <div class="rpp-fontes-cards">
          {% for f in g.fontes %}
          <div class="rpp-fonte-card">
            <div class="rpp-fonte-card__index">{{ loop.index }}</div>
            <div class="rpp-fonte-card__content">
              <div class="rpp-fonte-row rpp-fonte-row--3">
                <div class="rpp-mini-compact rpp-mini-compact--featured">
                  <span class="rpp-mini-compact__label">Fornecedor</span>
                  <span class="rpp-mini-compact__value rpp-mini-compact__value--strong">{{ f.fornecedor }}</span>
                </div>
                <div class="rpp-mini-compact">
                  <span class="rpp-mini-compact__label">CNPJ</span>
                  <span class="rpp-mini-compact__value">{{ f.cnpj }}</span>
                </div>
                <div class="rpp-mini-compact rpp-mini-compact--featured">
                  <span class="rpp-mini-compact__label">Valor</span>
                  <span class="rpp-mini-compact__value rpp-mini-compact__value--strong">{{ f.valor }}</span>
                </div>
              </div>

              <div class="rpp-fonte-row rpp-fonte-row--3">
                <div class="rpp-mini-compact">
                  <span class="rpp-mini-compact__label">Órgão</span>
                  <span class="rpp-mini-compact__value">{{ f.orgao }}</span>
                </div>
                <div class="rpp-mini-compact">
                  <span class="rpp-mini-compact__label">Modalidade</span>
                  <span class="rpp-mini-compact__value">{{ f.tipo }}</span>
                </div>
                <div class="rpp-mini-compact">
                  <span class="rpp-mini-compact__label">Data</span>
                  <span class="rpp-mini-compact__value">{{ f.data }}</span>
                </div>
              </div>

              <div class="rpp-fonte-row rpp-fonte-row--5">
                <div class="rpp-mini-compact rpp-mini-compact--wide">
                  <span class="rpp-mini-compact__label">ID / Processo</span>
                  <span class="rpp-mini-compact__value">{{ loop.index }} / {{ f.processo or 'N/D' }}</span>
                </div>
                <div class="rpp-mini-compact">
                  <span class="rpp-mini-compact__label">Qtd.</span>
                  <span class="rpp-mini-compact__value">{{ g.quantidade_fmt }}</span>
                </div>
                <div class="rpp-mini-compact">
                  <span class="rpp-mini-compact__label">Unid.</span>
                  <span class="rpp-mini-compact__value">{{ g.unidade }}</span>
                </div>
                <div class="rpp-mini-compact">
                  <span class="rpp-mini-compact__label">Fonte</span>
                  <span class="rpp-mini-compact__value">{{ f.tipo }}</span>
                </div>
                <div class="rpp-mini-compact">
                  <span class="rpp-mini-compact__label">UF</span>
                  <span class="rpp-mini-compact__value">{{ (f.municipio_uf or '—').split('/')[-1] }}</span>
                </div>
              </div>

              <div class="rpp-fonte-row rpp-fonte-row--2">
                <div class="rpp-mini-compact rpp-mini-compact--wide">
                  <span class="rpp-mini-compact__label">Descrição do item</span>
                  <span class="rpp-mini-compact__value">{{ g.nome }}</span>
                </div>
                <div class="rpp-mini-compact rpp-mini-compact--wide">
                  <span class="rpp-mini-compact__label">Ajuste</span>
                  <span class="rpp-mini-compact__value">{{ f.ajuste }}</span>
                </div>
              </div>
            </div>
          </div>
          {% endfor %}
        </div>
      </div>
      {% endfor %}
    </section>

    <section class="rpp-block">
      <h2 class="rpp-section-title">Informações dos fornecedores</h2>
      <p class="rpp-section-lead">Dados cadastrais identificados nas fontes da pesquisa</p>
      {% if ctx.cnpjs_fontes %}
      <div class="rpp-fornecedores-grid">
        {% for c in ctx.cnpjs_fontes %}
        <div class="rpp-fornecedor-card">
          <div class="rpp-fornecedor-card__title">Fornecedor {{ loop.index }}</div>
          <div class="rpp-fornecedor-card__line"><strong>CNPJ:</strong> {{ c }}</div>
          <div class="rpp-fornecedor-card__line"><strong>Telefone:</strong> Não informado</div>
          <div class="rpp-fornecedor-card__line"><strong>Email:</strong> Não informado</div>
          <div class="rpp-fornecedor-card__line"><strong>Endereço:</strong> Não informado</div>
        </div>
        {% endfor %}
      </div>
      {% else %}
      <p class="rpp-cnpj-empty">Nenhum CNPJ estruturado foi localizado nos metadados salvos dos itens.</p>
      {% endif %}
    </section>

  </div>
</body>
</html>
"""
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
) -> bytes:
    ctx = montar_contexto_relatorio(
        cotacao=cotacao,
        itens_qs=itens_qs,
        titulo_relatorio=titulo_relatorio,
        url_verificacao=url_verificacao,
        anexo_fornecedor_url=anexo_fornecedor_url,
        formula_id=formula_id,
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


def nome_arquivo_relatorio(cotacao_id: int, titulo_relatorio: str, *, sistema_nome: str = "", usuario_nome: str = "", dt=None) -> str:
    now = dt or timezone.now()
    stamp = timezone.localtime(now).strftime("%Y%m%d-%H%M")
    sistema = _slug_part(sistema_nome, max_len=26) or "docmaster-pesquisador-pncp"
    usuario = _slug_part(usuario_nome, max_len=26) or "usuario"
    titulo = _slug_part(titulo_relatorio, max_len=42) or "relatorio"
    return f"{sistema}_{usuario}_{stamp}_cotacao-{int(cotacao_id)}_{titulo}.pdf"
