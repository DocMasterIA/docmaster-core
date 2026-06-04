"""
Auditoria de cobertura de fornecedor em fontes PNCP de uma cotação.

Exemplo:
  python manage.py audit_pncp_supplier_coverage --cotacao-id 6
  python manage.py audit_pncp_supplier_coverage --cotacao-id 6 --json
  python manage.py audit_pncp_supplier_coverage --cotacao-id 6 --only-missing
"""
from __future__ import annotations

import json
from typing import Any, List

from django.core.management.base import BaseCommand

from backend.app.models import PncpCotacaoItemCotacao
from backend.app.services.pncp_supplier_gap_audit import (
    GAP_ALREADY_IN_SOURCE,
    GAP_OK,
    probe_fonte_pncp,
    summarize_gap_reports,
)


class Command(BaseCommand):
    help = "Classifica cada fonte PNCP da cotação: por que tem ou não tem fornecedor/CNPJ."

    def add_arguments(self, parser):
        parser.add_argument("--cotacao-id", type=int, required=True)
        parser.add_argument(
            "--only-missing",
            action="store_true",
            help="Sondar só linhas sem cnpj_fornecedor no source.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Saída JSON (para gravar relatório).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Máximo de linhas a sondar (0 = todas).",
        )

    def handle(self, *args, **options):
        cid = int(options["cotacao_id"])
        only_missing = bool(options["only_missing"])
        as_json = bool(options["json"])
        limit = max(0, int(options["limit"] or 0))

        qs = PncpCotacaoItemCotacao.objects.filter(cotacao_id=cid).order_by("id")
        rows = list(qs)
        if not rows:
            self.stderr.write(f"Cotação {cid} sem fontes (PncpCotacaoItemCotacao).")
            return

        reports: List[Any] = []
        probed = 0
        for row in rows:
            src = row.source if isinstance(row.source, dict) else {}
            has_cnpj = bool(str(src.get("cnpj_fornecedor") or "").strip())
            if only_missing and has_cnpj:
                continue
            if limit and probed >= limit:
                break
            probed += 1
            rep = probe_fonte_pncp(
                row_id=row.id,
                numero_pncp=row.numero_pncp or "",
                ano_compra=row.ano_compra,
                sequencial_compra=row.sequencial_compra,
                numero_item=row.numero_item or "",
                source=src,
            )
            reports.append(rep)

        summary = summarize_gap_reports(reports)
        total = len(rows)
        with_cnpj = sum(
            1 for r in rows if str((r.source or {}).get("cnpj_fornecedor") or "").strip()
        )

        if as_json:
            payload = {
                "cotacao_id": cid,
                "total_fontes": total,
                "com_cnpj_no_source": with_cnpj,
                "sondadas": len(reports),
                "summary": summary,
                "reports": [r.to_dict() for r in reports],
            }
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        self.stdout.write(f"=== Cotação {cid} ===")
        self.stdout.write(f"Fontes totais: {total} | com CNPJ no source: {with_cnpj}")
        self.stdout.write(f"Sondadas: {len(reports)}")
        self.stdout.write("--- Resumo (gap_reason → quantidade) ---")
        for reason, n in summary.items():
            self.stdout.write(f"  {reason}: {n}")
        self.stdout.write("--- Detalhe ---")
        for rep in reports:
            if rep.gap_reason in (GAP_OK, GAP_ALREADY_IN_SOURCE):
                continue
            self.stdout.write(
                f"id={rep.row_id} | {rep.gap_reason} | np={rep.numero_pncp[:50]} "
                f"| item={rep.numero_item} | sit={rep.situacao_item or '-'} | temRes={rep.tem_resultado}"
            )
            for layer in rep.layers:
                self.stdout.write(
                    f"    {layer.name}: HTTP {layer.status_code}"
                    + (f" ({layer.error})" if layer.error else "")
                )

        self.stdout.write("")
        self.stdout.write(
            "Meta 100%: só é atingível para fontes em que a PNCP publica resultado ou contrato. "
            "Veja docs/PLANO-MODULO-COBERTURA-FORNECEDOR-PNCP.md seção «Roteiro 100%»."
        )
