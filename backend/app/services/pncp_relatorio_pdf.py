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

from backend.app.services.pncp_relatorio_itens import agrupar_itens_relatorio_pesquisa_precos

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


def montar_contexto_relatorio(
    *,
    cotacao,
    itens_qs,
    titulo_relatorio: str,
    url_verificacao: str,
) -> RelatorioCotacaoContext:
    itens = list(itens_qs.order_by("id"))
    grupos, total_linhas = agrupar_itens_relatorio_pesquisa_precos(itens)
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
      </div>
      <div class="rpp-head-main__col rpp-head-main__col--qr">
        <img class="rpp-head-main__qr" src="{{ ctx.qr_data_url }}" alt="" />
      </div>
    </header>

    <div class="rpp-meta-grid">
      <div class="rpp-card rpp-card--accent">
        <span class="rpp-card__label">Cotação (título interno)</span>
        <span class="rpp-card__value">{{ ctx.titulo_cotacao }}</span>
      </div>
      <div class="rpp-card">
        <span class="rpp-card__label">Data da pesquisa</span>
        <span class="rpp-card__value">{{ ctx.data_pesquisa_exibicao }}</span>
      </div>
      <div class="rpp-card">
        <span class="rpp-card__label">Emitido em</span>
        <span class="rpp-card__value">{{ ctx.emitido_em_exibicao }}</span>
      </div>
      <div class="rpp-card">
        <span class="rpp-card__label">Responsável</span>
        <span class="rpp-card__value">{{ ctx.criado_por }}{% if ctx.criado_por_email %}<span class="rpp-card__value--muted"> — {{ ctx.criado_por_email }}</span>{% endif %}</span>
      </div>
      <div class="rpp-card">
        <span class="rpp-card__label">Termo PNCP</span>
        <span class="rpp-card__value">{{ ctx.termo_pncp }}</span>
      </div>
      <div class="rpp-card">
        <span class="rpp-card__label">Itens (grupos)</span>
        <span class="rpp-card__value">{{ ctx.total_itens }}</span>
      </div>
      <div class="rpp-card">
        <span class="rpp-card__label">Cotações registradas</span>
        <span class="rpp-card__value">{{ ctx.total_linhas_cotacao }}</span>
      </div>
    </div>

    <section class="rpp-block">
      <h2 class="rpp-section-title">Metodologia Aplicada</h2>
      <p class="rpp-section-lead">Base legal, método matemático e critérios de seleção das cotações</p>
      <div class="rpp-metodologia">
        <h3 class="rpp-metodologia__title">IN 65/2021 · Lei 14.133</h3>
        <p>
          A presente pesquisa de preços foi materializada com base na Lei nº 14.133/2021 e na Instrução Normativa nº 65/2021,
          adotando como método matemático a média aritmética dos preços obtidos, em conformidade com o art. 3º da referida instrução.
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
      <h2 class="rpp-section-title">Resultado consolidado</h2>
      <p class="rpp-section-lead">Resumo dos itens com média das cotações e situação da pesquisa (mínimo de 3 fontes por item para «Válido»).</p>
      <div class="rpp-table-wrap">
        <table class="rpp-table rpp-table--consolidado">
          <thead>
            <tr>
              <th>Item</th>
              <th>Descrição</th>
              <th>Quantidade</th>
              <th>Cotações</th>
              <th>Média</th>
              <th>Situação</th>
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
              <td>{{ g.situacao }}</td>
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
        <div class="rpp-table-wrap">
          <table class="rpp-table rpp-table--fontes">
            <thead>
              <tr>
                <th>Fonte</th>
                <th>Fornecedor</th>
                <th>CNPJ</th>
                <th>Data</th>
                <th>Valor</th>
                <th>Órgão</th>
                <th>Município/UF</th>
                <th>Processo</th>
                <th>Ajuste</th>
              </tr>
            </thead>
            <tbody>
              {% for f in g.fontes %}
              <tr>
                <td>{{ f.tipo }}</td>
                <td>{{ f.fornecedor }}</td>
                <td>{{ f.cnpj }}</td>
                <td>{{ f.data }}</td>
                <td>{{ f.valor }}</td>
                <td>{{ f.orgao }}</td>
                <td>{{ f.municipio_uf }}</td>
                <td>{{ f.processo }}</td>
                <td>{{ f.ajuste }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
      {% endfor %}
    </section>

    <section class="rpp-block">
      <h2 class="rpp-section-title">CNPJ identificados nas fontes (quando disponíveis)</h2>
      {% if ctx.cnpjs_fontes %}
      <ul class="rpp-cnpj-list">
        {% for c in ctx.cnpjs_fontes %}
        <li>{{ c }}</li>
        {% endfor %}
      </ul>
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
) -> bytes:
    ctx = montar_contexto_relatorio(
        cotacao=cotacao,
        itens_qs=itens_qs,
        titulo_relatorio=titulo_relatorio,
        url_verificacao=url_verificacao,
    )
    html = renderizar_html_relatorio(ctx)
    base_url = _SERVICES_DIR.as_uri() + "/"
    return HTML(string=html, base_url=base_url).write_pdf()


def nome_arquivo_relatorio(cotacao_id: int, titulo_relatorio: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", titulo_relatorio, flags=re.UNICODE)[:60]
    slug = re.sub(r"[-\s]+", "-", slug, flags=re.UNICODE).strip("-") or "relatorio"
    return f"relatorio-cotacao-{cotacao_id}-{slug}.pdf"
