from __future__ import annotations

from pathlib import Path
from typing import Dict


TEMPLATE_PACKAGES_ROOT = Path(__file__).resolve().parents[2] / "template_packages"
PROJECT_ROOT = TEMPLATE_PACKAGES_ROOT.parent
LEGACY_TR_BASE_DIR = TEMPLATE_PACKAGES_ROOT / "tr_base"
LAW_14133_ROOT = TEMPLATE_PACKAGES_ROOT / "lei_14133"


PACKAGE_DIRS: Dict[str, str] = {
    "dispensa_75_i_manutencao_veiculos": "dispensa_75_i_manutencao_veiculos",
    "dispensa_75_i_obras_engenharia": "dispensa_75_i_obras_engenharia",
    "dispensa_75_ii_compras": "dispensa_75_ii_compras",
    "dispensa_75_ii_servicos": "dispensa_75_ii_servicos",
    "dispensa_75_ii_compras_servicos_inclusos": "dispensa_75_ii_compras_servicos_inclusos",
    "inexigibilidade_74_i_show_artistico": "inexigibilidade_74_i_show_artistico",
    "inexigibilidade_74_i_fornecedor_exclusivo": "tr_dfd_generico",
    "inexigibilidade_74_i_manutencao_veiculos": "inexigibilidade_74_i_manutencao_de_veiculos",
    "tr_dfd_generico": "tr_dfd_generico",
}

CUSTOM_TR_BASE_BY_PACKAGE: Dict[str, str] = {
    "inexigibilidade_74_i_fornecedor_exclusivo": "TERMO DE REFERENCIA IA - ART 74 I - FORNECEDOR EXCLUSIVO.docx",
}


def get_package_template_paths(slot_package_key: str | None) -> Dict[str, Path]:
    """
    Resolve caminhos de templates TR/DFD/Ofício para um pacote.
    Se o pacote não existir, cai em `tr_dfd_generico`.
    """
    key = (slot_package_key or "").strip().lower() or "tr_dfd_generico"
    folder = PACKAGE_DIRS.get(key, PACKAGE_DIRS["tr_dfd_generico"])
    base = LAW_14133_ROOT / folder
    tr_path = base / "TR_modelo_base.docx"
    custom_tr_filename = CUSTOM_TR_BASE_BY_PACKAGE.get(key)
    if custom_tr_filename:
        tr_path = PROJECT_ROOT / custom_tr_filename
    return {
        "base_dir": base,
        "tr": tr_path,
        "dfd": base / "DFD_modelo_base.docx",
        "oficio": base / "OFICIO_modelo_base.docx",
    }


def ensure_fallback_path(path: Path, legacy_filename: str) -> Path:
    """
    Usa o arquivo do pacote quando existir; senão, retorna fallback legado em template_packages/tr_base.
    """
    if path.exists():
        return path

    # Fallback principal (/app/template_packages/tr_base/<arquivo>)
    legacy_default = LEGACY_TR_BASE_DIR / legacy_filename
    if legacy_default.exists():
        return legacy_default

    # Fallback adicional para cenários de build/volume em caminhos alternativos.
    alt_candidates = [
        Path(__file__).resolve().parents[1] / "template_packages" / "tr_base" / legacy_filename,  # /app/rag_service/template_packages/...
        Path.cwd() / "template_packages" / "tr_base" / legacy_filename,
    ]
    for candidate in alt_candidates:
        if candidate.exists():
            return candidate

    checked = [str(path), str(legacy_default)] + [str(c) for c in alt_candidates]
    raise FileNotFoundError(
        "Template não encontrado em nenhum caminho esperado. "
        f"arquivo={legacy_filename}; caminhos_verificados={checked}"
    )
