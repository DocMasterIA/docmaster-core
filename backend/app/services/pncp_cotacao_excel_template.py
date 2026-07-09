"""
Exportação de cotação PNCP a partir de planilha-modelo (.xlsx / .xlsm) com slots.

Slots suportados (ver docs/pncp/COTACAO-EXCEL-SLOTS-MAPEAMENTO.md):
  globais: DATA_HORARIO_GERACAO, PREFEITURA_E_DATA, RESPONSAVEL_PESQUISA_PREÇOS,
           VALOR_EXTENSO, PREFEITURA_ESTADO, CNPJ, TELEFONE, DEPARTAMENTO, OBSERVACOES
  por item (linha-modelo): ID_ITEM, NOME_ITEM, UNIDADE, QUANTIDADE, COTACOES_VALIDAS,
                           VALOR_MEDIO, VALOR_TOTAL_HOMOLOGADO
"""
from __future__ import annotations

import io
import re
from copy import copy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from django.conf import settings
from django.utils import timezone

from backend.app.models import PncpCotacao
from backend.app.services.pncp_relatorio_itens import (
    _formatar_moeda_br,
    _fmt_quantidade,
    texto_orgao_capa_prefeitura_cotacao,
)
from backend.app.utils.cotacao_valor_total import somar_valor_total_estimado_itens
from backend.app.utils.valor_extenso_pt import valor_monetario_por_extenso

# Slots repetidos por linha de item na planilha-modelo.
ITEM_SLOT_NAMES = frozenset({
    "ID_ITEM",
    "NOME_ITEM",
    "UNIDADE",
    "QUANTIDADE",
    "COTACOES_VALIDAS",
    "VALOR_MEDIO",
    "VALOR_TOTAL_HOMOLOGADO",
})

# Slots preenchidos pelo usuário no modal de exportação.
USER_PREF_SLOT_NAMES = ("CNPJ", "TELEFONE")
COTACAO_SLOT_NAMES = ("DEPARTAMENTO", "OBSERVACOES")

# Aliases (sem acento / grafia alternativa) → slot canônico.
SLOT_ALIASES: Dict[str, str] = {
    "RESPONSAVEL_PESQUISA_PRECOS": "RESPONSAVEL_PESQUISA_PREÇOS",
    "RESPONSAVEL_PESQUISA_PRECO": "RESPONSAVEL_PESQUISA_PREÇOS",
    "RESPONSAVEL_PESQUISA_PREÇOS": "RESPONSAVEL_PESQUISA_PREÇOS",
    "VALOR_EXTENSO": "VALOR_EXTENSO",
    "VALOR_POR_EXTENSO": "VALOR_EXTENSO",
}

_SLOT_PATTERN = re.compile(r"\{([^{}]+)\}")


def _resolve_repo_roots() -> List[Path]:
    base = Path(getattr(settings, "BASE_DIR", Path(__file__).resolve().parents[2]))
    roots: List[Path] = []
    for candidate in (base, base.parent, Path("/app")):
        if candidate not in roots:
            roots.append(candidate)
    return roots


def default_cotacao_excel_template_path() -> Path:
    env = (getattr(settings, "PNCP_COTACAO_EXCEL_TEMPLATE", None) or "").strip()
    if env:
        return Path(env)

    relative_paths = (
        "template_packages/excell_base/relatorio_base_excell.xlsm",
        "template_packages/excell_base/relatorio_saida_excell.xlsx",
        "template_packages/pncp/cotacao_pesquisa_precos.xlsm",
        "template_packages/pncp/cotacao_pesquisa_precos.xlsx",
    )
    for rel in relative_paths:
        for root in _resolve_repo_roots():
            candidate = root / rel
            if candidate.is_file():
                return candidate

    return _resolve_repo_roots()[0] / relative_paths[0]


def _canonical_slot(raw: str) -> str:
    key = str(raw or "").strip().upper()
    return SLOT_ALIASES.get(key, key)


def _format_dt_br(dt) -> str:
    if dt is None:
        return ""
    tz = timezone.get_current_timezone()
    local = timezone.localtime(dt, tz) if timezone.is_aware(dt) else dt
    return local.strftime("%d/%m/%Y às %H:%M")


def _format_date_br(dt) -> str:
    if dt is None:
        return ""
    tz = timezone.get_current_timezone()
    local = timezone.localtime(dt, tz) if timezone.is_aware(dt) else dt
    return local.strftime("%d/%m/%Y")


def _responsavel_pesquisa(cotacao: PncpCotacao) -> str:
    snap = (getattr(cotacao, "criado_por_nome", None) or "").strip()
    if snap:
        return snap
    u = cotacao.usuario
    if u is None:
        return ""
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
    return full or (getattr(u, "email", None) or "").strip() or str(getattr(u, "pk", ""))


def build_global_slot_context(
    cotacao: PncpCotacao,
    *,
    refletidos: Optional[Mapping[int, Mapping[str, Any]]] = None,
    itens: Optional[Sequence[Any]] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, str]:
    """Monta valores dos slots globais da planilha."""
    itens = list(itens or cotacao.itens.all().order_by("id"))
    usuario = cotacao.usuario
    agora = timezone.now()
    data_pesquisa = cotacao.created_at or agora

    prefeitura_estado = texto_orgao_capa_prefeitura_cotacao(cotacao, usuario)
    if not prefeitura_estado:
        prefeitura_estado = "—"
    prefeitura_estado_fmt = prefeitura_estado.upper()

    prefeitura_e_data = prefeitura_estado_fmt
    data_pesquisa_txt = _format_date_br(data_pesquisa)
    if data_pesquisa_txt:
        prefeitura_e_data = f"{prefeitura_estado_fmt}, {data_pesquisa_txt}"

    total = somar_valor_total_estimado_itens(itens, refletidos)
    valor_extenso = valor_monetario_por_extenso(total).upper() if total is not None else ""

    ctx = {
        "DATA_HORARIO_GERACAO": _format_dt_br(agora),
        "PREFEITURA_E_DATA": prefeitura_e_data,
        "PREFEITURA_ESTADO": prefeitura_estado_fmt,
        "RESPONSAVEL_PESQUISA_PREÇOS": _responsavel_pesquisa(cotacao),
        "VALOR_EXTENSO": valor_extenso,
    }

    extra = extra or {}
    for slot in (*USER_PREF_SLOT_NAMES, *COTACAO_SLOT_NAMES):
        ctx[slot] = str(extra.get(slot, "") or "")
    return ctx


def _item_get(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def _fmt_moeda_ui(v: Any) -> str:
    n = _safe_float(v)
    if n is None:
        return "R$ —"
    return f"R$ {_formatar_moeda_br(n)}"


def _total_cotacoes_validas(fontes: Mapping[str, Any]) -> int:
    return (
        int(fontes.get("governamentais") or 0)
        + int(fontes.get("entesPublicos") or 0)
        + int(fontes.get("dominioAmplo") or 0)
        + int(fontes.get("cotacaoDireta") or 0)
        + int(fontes.get("notasFiscais") or 0)
    )


def _resolve_valor_medio_item(item: Any, refletido: Mapping[str, Any]) -> float:
    """Mesma prioridade da coluna «Média de preço» em CotacaoDetalhe.vue."""
    vu = _safe_float(refletido.get("valor_unitario_refletido"))
    if vu is None:
        vu = _safe_float(_item_get(item, "valor_unitario"))
    if vu is None:
        qtd = _safe_float(_item_get(item, "quantidade")) or _safe_float(refletido.get("quantidade_refletida"))
        vt = _safe_float(_item_get(item, "valor_total"))
        if qtd and qtd > 0 and vt is not None:
            vu = vt / qtd
    return float(vu) if vu is not None else 0.0


def _resolve_valor_total_homologado_item(item: Any, refletido: Mapping[str, Any]) -> Optional[float]:
    vt = _safe_float(refletido.get("valor_total_refletido"))
    if vt is None:
        vt = _safe_float(_item_get(item, "valor_total"))
    if vt is None:
        vt = _safe_float(_item_get(item, "valor_unitario"))
    return vt


def build_item_slot_context(
    item: Any,
    *,
    refletido: Optional[Mapping[str, Any]] = None,
    fontes: Optional[Mapping[str, Any]] = None,
) -> Dict[str, str]:
    refletido = refletido or {}
    fontes = fontes or {}

    numero = _item_get(item, "numero_item")
    descricao = _item_get(item, "descricao_item")
    item_id = _item_get(item, "id")
    id_exibicao = str(numero or item_id or "").strip()

    unidade = str(refletido.get("unidade_medida_refletida") or _item_get(item, "unidade_medida") or "").strip() or "-"
    quantidade = _item_get(item, "quantidade")
    if quantidade is None:
        quantidade = refletido.get("quantidade_refletida")

    valor_medio = _resolve_valor_medio_item(item, refletido)
    valor_total = _resolve_valor_total_homologado_item(item, refletido)

    return {
        "ID_ITEM": id_exibicao,
        "NOME_ITEM": str(descricao or "").strip(),
        "UNIDADE": unidade,
        "QUANTIDADE": _fmt_quantidade(quantidade),
        "COTACOES_VALIDAS": str(_total_cotacoes_validas(fontes)),
        "VALOR_MEDIO": _fmt_moeda_ui(valor_medio),
        "VALOR_TOTAL_HOMOLOGADO": _fmt_moeda_ui(valor_total),
    }


def _substitute_slots(text: str, ctx: Mapping[str, str]) -> str:
    if not text or "{" not in text:
        return text

    def repl(match: re.Match[str]) -> str:
        slot = _canonical_slot(match.group(1))
        if slot in ctx:
            return str(ctx[slot])
        return match.group(0)

    return _SLOT_PATTERN.sub(repl, text)


def _cell_has_item_slot(value: Any) -> bool:
    if value is None:
        return False
    text = str(value)
    if "{" not in text:
        return False
    for m in _SLOT_PATTERN.finditer(text):
        if _canonical_slot(m.group(1)) in ITEM_SLOT_NAMES:
            return True
    return False


def _row_has_item_slot(ws, row_idx: int) -> bool:
    for cell in ws[row_idx]:
        if _cell_has_item_slot(cell.value):
            return True
    return False


def _copy_row_style(ws, src_row: int, dst_row: int) -> None:
    if src_row == dst_row:
        return
    ws.row_dimensions[dst_row].height = ws.row_dimensions[src_row].height
    for col in range(1, ws.max_column + 1):
        src = ws.cell(row=src_row, column=col)
        dst = ws.cell(row=dst_row, column=col)
        if src.has_style:
            dst.font = copy(src.font)
            dst.border = copy(src.border)
            dst.fill = copy(src.fill)
            dst.number_format = src.number_format
            dst.protection = copy(src.protection)
            dst.alignment = copy(src.alignment)


def _apply_item_row_templates(
    ws,
    items: Sequence[Any],
    global_ctx: Mapping[str, str],
    *,
    refletidos: Optional[Mapping[int, Mapping[str, Any]]] = None,
    fontes_counts: Optional[Mapping[int, Mapping[str, Any]]] = None,
) -> None:
    if not items:
        return
    refletidos = refletidos or {}
    fontes_counts = fontes_counts or {}
    template_rows = [r for r in range(1, ws.max_row + 1) if _row_has_item_slot(ws, r)]
    for row_idx in reversed(template_rows):
        template_values = [cell.value for cell in ws[row_idx]]
        if len(items) == 1:
            target_rows = [row_idx]
        else:
            ws.insert_rows(row_idx + 1, amount=len(items) - 1)
            target_rows = list(range(row_idx, row_idx + len(items)))
            for offset, target in enumerate(target_rows):
                if offset == 0:
                    continue
                _copy_row_style(ws, row_idx, target)

        for target_row, item in zip(target_rows, items):
            item_id = int(_item_get(item, "id") or 0)
            item_ctx = build_item_slot_context(
                item,
                refletido=refletidos.get(item_id, {}),
                fontes=fontes_counts.get(item_id, {}),
            )
            merged = {**global_ctx, **item_ctx}
            for col_idx, raw in enumerate(template_values, start=1):
                if raw is None:
                    continue
                text = str(raw)
                if "{" not in text:
                    ws.cell(row=target_row, column=col_idx, value=raw)
                    continue
                ws.cell(row=target_row, column=col_idx, value=_substitute_slots(text, merged))


def apply_slots_to_workbook(
    wb,
    global_ctx: Mapping[str, str],
    items: Sequence[Any],
    *,
    refletidos: Optional[Mapping[int, Mapping[str, Any]]] = None,
    fontes_counts: Optional[Mapping[int, Mapping[str, Any]]] = None,
) -> None:
    """Substitui slots globais e expande linhas-modelo de itens em todas as abas."""
    for ws in wb.worksheets:
        _apply_item_row_templates(
            ws,
            items,
            global_ctx,
            refletidos=refletidos,
            fontes_counts=fontes_counts,
        )
        for row in ws.iter_rows():
            for cell in row:
                val = cell.value
                if val is None or "{" not in str(val):
                    continue
                if isinstance(val, str):
                    cell.value = _substitute_slots(val, global_ctx)


def render_cotacao_excel_from_template(
    cotacao: PncpCotacao,
    template_path: Path,
    *,
    refletidos: Optional[Mapping[int, Mapping[str, Any]]] = None,
    fontes_counts: Optional[Mapping[int, Mapping[str, Any]]] = None,
    itens: Optional[Sequence[Any]] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> io.BytesIO:
    try:
        from openpyxl import load_workbook
    except Exception as exc:
        raise RuntimeError("Exportação XLSX indisponível. Dependência 'openpyxl' não encontrada.") from exc

    itens = list(itens or cotacao.itens.all().order_by("id"))
    # keep_vba=False: remove content-types macroEnabled do modelo .xlsm.
    # Saída sempre .xlsx — compatível com Google Sheets, Excel e LibreOffice.
    # (keep_vba=True + extensão .xlsx corrompe; .xlsm o Google Sheets não abre.)
    wb = load_workbook(template_path, keep_vba=False)
    global_ctx = build_global_slot_context(cotacao, refletidos=refletidos, itens=itens, extra=extra)
    apply_slots_to_workbook(
        wb,
        global_ctx,
        itens,
        refletidos=refletidos,
        fontes_counts=fontes_counts,
    )

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream


def template_available(path: Optional[Path] = None) -> bool:
    p = path or default_cotacao_excel_template_path()
    return p.is_file()


def template_output_ext(path: Optional[Path] = None) -> str:
    """Extensão do arquivo exportado (sempre .xlsx para compatibilidade com Google Sheets)."""
    return "xlsx"


def excel_content_type_for_ext(ext: str) -> str:
    if str(ext).lower().lstrip(".") == "xlsm":
        return "application/vnd.ms-excel.sheet.macroEnabled.12"
    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def list_slots_in_workbook(path: Path) -> Dict[str, List[str]]:
    """Auditoria: localiza slots presentes na planilha (útil ao receber o XLSM base)."""
    from openpyxl import load_workbook

    found: Dict[str, set[str]] = {}
    wb = load_workbook(path, read_only=True, data_only=False, keep_vba=path.suffix.lower() == ".xlsm")
    try:
        for ws in wb.worksheets:
            sheet_hits: set[str] = set()
            for row in ws.iter_rows(values_only=True):
                for val in row:
                    if val is None or "{" not in str(val):
                        continue
                    for m in _SLOT_PATTERN.finditer(str(val)):
                        sheet_hits.add(_canonical_slot(m.group(1)))
            if sheet_hits:
                found[ws.title] = sorted(sheet_hits)
    finally:
        wb.close()
    return {k: v for k, v in found.items()}
