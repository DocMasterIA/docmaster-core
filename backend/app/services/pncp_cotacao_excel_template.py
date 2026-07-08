"""
Exportação de cotação PNCP a partir de planilha-modelo (.xlsx / .xlsm) com slots.

Slots suportados (ver docs/pncp/COTACAO-EXCEL-SLOTS-MAPEAMENTO.md):
  globais: DATA_HORARIO_GERACAO, PREFEITURA_E_DATA, RESPONSAVEL_PESQUISA_PREÇOS,
           VALOR_EXTENSO, PREFEITURA_ESTADO
  por item (linha-modelo): ID_ITEM, NOME_ITEM
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
from backend.app.services.pncp_relatorio_itens import texto_orgao_capa_prefeitura_cotacao
from backend.app.utils.cotacao_valor_total import somar_valor_total_estimado_itens
from backend.app.utils.valor_extenso_pt import valor_monetario_por_extenso

# Slots repetidos por linha de item na planilha-modelo.
ITEM_SLOT_NAMES = frozenset({"ID_ITEM", "NOME_ITEM"})

# Aliases (sem acento / grafia alternativa) → slot canônico.
SLOT_ALIASES: Dict[str, str] = {
    "RESPONSAVEL_PESQUISA_PRECOS": "RESPONSAVEL_PESQUISA_PREÇOS",
    "RESPONSAVEL_PESQUISA_PRECO": "RESPONSAVEL_PESQUISA_PREÇOS",
    "RESPONSAVEL_PESQUISA_PREÇOS": "RESPONSAVEL_PESQUISA_PREÇOS",
    "VALOR_EXTENSO": "VALOR_EXTENSO",
    "VALOR_POR_EXTENSO": "VALOR_EXTENSO",
}

_SLOT_PATTERN = re.compile(r"\{([^{}]+)\}")


def default_cotacao_excel_template_path() -> Path:
    env = (getattr(settings, "PNCP_COTACAO_EXCEL_TEMPLATE", None) or "").strip()
    if env:
        return Path(env)
    base = Path(getattr(settings, "BASE_DIR", Path(__file__).resolve().parents[2]))
    for name in (
        "cotacao_pesquisa_precos.xlsm",
        "cotacao_pesquisa_precos.xlsx",
        "cotacao_export.xlsm",
        "cotacao_export.xlsx",
    ):
        candidate = base / "template_packages" / "pncp" / name
        if candidate.is_file():
            return candidate
    return base / "template_packages" / "pncp" / "cotacao_pesquisa_precos.xlsm"


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
) -> Dict[str, str]:
    """Monta valores dos slots globais da planilha."""
    itens = list(itens or cotacao.itens.all().order_by("id"))
    usuario = cotacao.usuario
    agora = timezone.now()
    data_pesquisa = cotacao.created_at or agora

    prefeitura_estado = texto_orgao_capa_prefeitura_cotacao(cotacao, usuario)
    if not prefeitura_estado:
        prefeitura_estado = "—"

    prefeitura_e_data = prefeitura_estado
    data_pesquisa_txt = _format_date_br(data_pesquisa)
    if data_pesquisa_txt:
        prefeitura_e_data = f"{prefeitura_estado}, {data_pesquisa_txt}"

    total = somar_valor_total_estimado_itens(itens, refletidos)
    valor_extenso = valor_monetario_por_extenso(total) if total is not None else ""

    return {
        "DATA_HORARIO_GERACAO": _format_dt_br(agora),
        "PREFEITURA_E_DATA": prefeitura_e_data,
        "PREFEITURA_ESTADO": prefeitura_estado,
        "RESPONSAVEL_PESQUISA_PREÇOS": _responsavel_pesquisa(cotacao),
        "VALOR_EXTENSO": valor_extenso,
    }


def build_item_slot_context(item: Any) -> Dict[str, str]:
    numero = getattr(item, "numero_item", None)
    if numero is None and isinstance(item, dict):
        numero = item.get("numero_item")
    descricao = getattr(item, "descricao_item", None)
    if descricao is None and isinstance(item, dict):
        descricao = item.get("descricao_item")
    item_id = getattr(item, "id", None)
    if item_id is None and isinstance(item, dict):
        item_id = item.get("id")
    id_exibicao = str(numero or item_id or "").strip()
    return {
        "ID_ITEM": id_exibicao,
        "NOME_ITEM": str(descricao or "").strip(),
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
) -> None:
    if not items:
        return
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
            item_ctx = build_item_slot_context(item)
            merged = {**global_ctx, **item_ctx}
            for col_idx, raw in enumerate(template_values, start=1):
                if raw is None:
                    continue
                text = str(raw)
                if "{" not in text:
                    ws.cell(row=target_row, column=col_idx, value=raw)
                    continue
                ws.cell(row=target_row, column=col_idx, value=_substitute_slots(text, merged))


def apply_slots_to_workbook(wb, global_ctx: Mapping[str, str], items: Sequence[Any]) -> None:
    """Substitui slots globais e expande linhas-modelo de itens em todas as abas."""
    for ws in wb.worksheets:
        _apply_item_row_templates(ws, items, global_ctx)
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
    itens: Optional[Sequence[Any]] = None,
) -> io.BytesIO:
    try:
        from openpyxl import load_workbook
    except Exception as exc:
        raise RuntimeError("Exportação XLSX indisponível. Dependência 'openpyxl' não encontrada.") from exc

    itens = list(itens or cotacao.itens.all().order_by("id"))
    suffix = template_path.suffix.lower()
    keep_vba = suffix == ".xlsm"
    wb = load_workbook(template_path, keep_vba=keep_vba)
    global_ctx = build_global_slot_context(cotacao, refletidos=refletidos, itens=itens)
    apply_slots_to_workbook(wb, global_ctx, itens)

    stream = io.BytesIO()
    # Saída sempre .xlsx (sem macros), mesmo quando o modelo base é .xlsm.
    wb.save(stream)
    stream.seek(0)
    return stream


def template_available(path: Optional[Path] = None) -> bool:
    p = path or default_cotacao_excel_template_path()
    return p.is_file()


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
