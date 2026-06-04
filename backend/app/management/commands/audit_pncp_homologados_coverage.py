"""
Cobertura de fornecedor apenas em fontes homologadas/adjudicadas de uma cotação.

  python manage.py audit_pncp_homologados_coverage --cotacao-id 6
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from backend.app.models import PncpCotacaoItemCotacao
from backend.app.services.pncp_supplier_enrichment import item_homologado_para_busca_dict
from backend.app.services.pncp_supplier_gap_audit import (
    GAP_OK,
    GAP_ALREADY_IN_SOURCE,
    probe_fonte_pncp,
    summarize_gap_reports,
)


class Command(BaseCommand):
    help = "Auditoria PNCP restrita a fontes homologadas (meta de cobertura na cotação)."

    def add_arguments(self, parser):
        parser.add_argument("--cotacao-id", type=int, required=True)

    def handle(self, *args, **options):
        cid = int(options["cotacao_id"])
        rows = list(PncpCotacaoItemCotacao.objects.filter(cotacao_id=cid).order_by("id"))
        homolog_rows = []
        outras = 0
        for row in rows:
            src = row.source if isinstance(row.source, dict) else {}
            merged = {**src, "numero_pncp": row.numero_pncp, "ano_compra": row.ano_compra,
                      "sequencial_compra": row.sequencial_compra, "numero_item": row.numero_item}
            if item_homologado_para_busca_dict(merged):
                homolog_rows.append(row)
            else:
                outras += 1

        reports = []
        for row in homolog_rows:
            src = row.source if isinstance(row.source, dict) else {}
            reports.append(
                probe_fonte_pncp(
                    row_id=row.id,
                    numero_pncp=row.numero_pncp or "",
                    ano_compra=row.ano_compra,
                    sequencial_compra=row.sequencial_compra,
                    numero_item=row.numero_item or "",
                    source=src,
                )
            )

        summary = summarize_gap_reports(reports)
        com_cnpj = sum(
            1
            for r in homolog_rows
            if str((r.source or {}).get("cnpj_fornecedor") or "").strip()
        )
        self.stdout.write(f"=== Cotação {cid} — somente homologados ===")
        self.stdout.write(f"Fontes totais: {len(rows)} | homologadas: {len(homolog_rows)} | outras situação: {outras}")
        self.stdout.write(f"Homologadas com CNPJ no source: {com_cnpj}/{len(homolog_rows)}")
        pct = (100.0 * com_cnpj / len(homolog_rows)) if homolog_rows else 0.0
        self.stdout.write(f"Cobertura homologados (source): {pct:.1f}%")
        self.stdout.write("--- gap_reason (homologadas) ---")
        for reason, n in summary.items():
            self.stdout.write(f"  {reason}: {n}")
        pendentes = [
            r for r in reports
            if r.gap_reason not in (GAP_OK, GAP_ALREADY_IN_SOURCE)
        ]
        if pendentes:
            self.stdout.write("--- Homologadas sem fornecedor resolvido ---")
            for r in pendentes:
                self.stdout.write(
                    f"id={r.row_id} | {r.gap_reason} | item={r.numero_item} | sit={r.situacao_item or '-'}"
                )
