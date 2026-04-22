from __future__ import annotations

import json
import unicodedata
from typing import Any, Dict, Optional, Tuple

from django.core.management.base import BaseCommand

from backend.app.models import PncpCotacaoItemCotacao


def _norm_text(v: Any) -> str:
    s = str(v or "").strip().lower()
    if not s:
        return ""
    s = "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")
    return s


def _normalize_source(raw_source: Any) -> Dict[str, Any]:
    if isinstance(raw_source, dict):
        return dict(raw_source)
    if isinstance(raw_source, str):
        try:
            parsed = json.loads(raw_source)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {}


def _resolve_bucket(source: Dict[str, Any], numero_pncp: str) -> Optional[str]:
    inciso = _norm_text(source.get("inciso_classificacao") or source.get("incisoClassificacao"))
    fonte = _norm_text(source.get("fonte") or source.get("tipo_fonte") or source.get("categoria_fonte"))
    esfera_id = _norm_text(source.get("esfera_id") or source.get("esferaId"))
    esfera_adm = _norm_text(source.get("esfera_administrativa") or source.get("esferaAdministrativa"))

    if inciso in {"inciso_i", "inciso-i", "governamentais", "precos_governamentais", "precos governamentais"}:
        return "governamentais"
    if inciso in {"inciso_ii", "inciso-ii", "entes_publicos", "outros_entes_publicos", "outros entes publicos"}:
        return "entesPublicos"

    if esfera_id == "f" or esfera_adm == "federal":
        return "governamentais"
    if esfera_id in {"e", "m", "d"} or esfera_adm in {"estadual", "municipal", "distrital"}:
        return "entesPublicos"

    if "govern" in fonte:
        return "governamentais"
    if "ente" in fonte:
        return "entesPublicos"
    if "dominio" in fonte:
        return "dominioAmplo"
    if "direta" in fonte:
        return "cotacaoDireta"
    if "nota" in fonte:
        return "notasFiscais"

    if str(numero_pncp or "").strip():
        # fallback legado: com número PNCP assume origem governamental
        return "governamentais"
    return None


def _normalize_esfera(source: Dict[str, Any], bucket: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    esfera_id = _norm_text(source.get("esfera_id") or source.get("esferaId"))
    esfera_adm = _norm_text(source.get("esfera_administrativa") or source.get("esferaAdministrativa"))

    if esfera_id in {"f", "e", "m", "d"}:
        eid = esfera_id.upper()
        if eid == "F":
            return "F", "federal"
        if eid == "E":
            return "E", "estadual"
        if eid == "M":
            return "M", "municipal"
        if eid == "D":
            return "D", "distrital"

    if esfera_adm in {"federal", "estadual", "municipal", "distrital"}:
        if esfera_adm == "federal":
            return "F", "federal"
        if esfera_adm == "estadual":
            return "E", "estadual"
        if esfera_adm == "municipal":
            return "M", "municipal"
        if esfera_adm == "distrital":
            return "D", "distrital"

    # inferência mínima segura
    if bucket == "governamentais":
        return "F", "federal"
    return None, None


class Command(BaseCommand):
    help = "Normaliza source.inciso_classificacao e source.esfera_* em cotações antigas."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Só exibe quantos registros seriam alterados.")
        parser.add_argument("--batch-size", type=int, default=1000, help="Tamanho do lote de bulk_update.")

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        batch_size = max(100, int(options["batch_size"]))

        qs = PncpCotacaoItemCotacao.objects.all().only("id", "numero_pncp", "source")
        to_update = []
        scanned = 0
        changed = 0

        for row in qs.iterator(chunk_size=batch_size):
            scanned += 1
            src = _normalize_source(row.source)
            before = json.dumps(src, ensure_ascii=False, sort_keys=True)

            bucket = _resolve_bucket(src, row.numero_pncp or "")
            if bucket == "governamentais":
                src["inciso_classificacao"] = "inciso_i"
                src["fonte"] = "governamentais"
            elif bucket == "entesPublicos":
                src["inciso_classificacao"] = "inciso_ii"
                src["fonte"] = "entes_publicos"
            elif bucket == "dominioAmplo":
                src["fonte"] = "dominio_amplo"
            elif bucket == "cotacaoDireta":
                src["fonte"] = "cotacao_direta"
            elif bucket == "notasFiscais":
                src["fonte"] = "notas_fiscais"

            esfera_id, esfera_adm = _normalize_esfera(src, bucket)
            if esfera_id:
                src["esfera_id"] = esfera_id
                src["esferaId"] = esfera_id
            if esfera_adm:
                src["esfera_administrativa"] = esfera_adm
                src["esferaAdministrativa"] = esfera_adm

            after = json.dumps(src, ensure_ascii=False, sort_keys=True)
            if before == after:
                continue

            changed += 1
            if not dry_run:
                row.source = src
                to_update.append(row)
                if len(to_update) >= batch_size:
                    PncpCotacaoItemCotacao.objects.bulk_update(to_update, ["source"], batch_size=batch_size)
                    to_update = []

        if not dry_run and to_update:
            PncpCotacaoItemCotacao.objects.bulk_update(to_update, ["source"], batch_size=batch_size)

        self.stdout.write(self.style.SUCCESS(f"Registros lidos: {scanned}"))
        if dry_run:
            self.stdout.write(self.style.WARNING(f"Dry-run: {changed} registro(s) seriam alterados."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Registros alterados: {changed}"))
