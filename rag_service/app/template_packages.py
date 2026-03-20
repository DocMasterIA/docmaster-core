from __future__ import annotations

from pathlib import Path
from typing import Dict


TEMPLATE_PACKAGES_ROOT = Path(__file__).resolve().parents[2] / "template_packages"
LEGACY_TR_BASE_DIR = TEMPLATE_PACKAGES_ROOT / "tr_base"
LAW_14133_ROOT = TEMPLATE_PACKAGES_ROOT / "lei_14133"


PACKAGE_DIRS: Dict[str, str] = {
    "dispensa_75_i_manutencao_veiculos": "dispensa_75_i_manutencao_veiculos",
    "dispensa_75_i_obras_engenharia": "dispensa_75_i_obras_engenharia",
    "dispensa_75_ii_compras": "dispensa_75_ii_compras",
    "dispensa_75_ii_servicos": "dispensa_75_ii_servicos",
    "dispensa_75_ii_compras_servicos_inclusos": "dispensa_75_ii_compras_servicos_inclusos",
    "inexigibilidade_74_i_show_artistico": "inexigibilidade_74_i_show_artistico",
    "tr_dfd_generico": "tr_dfd_generico",
}


def get_package_template_paths(slot_package_key: str | None) -> Dict[str, Path]:
    """
    Resolve caminhos de templates TR/DFD/Ofício para um pacote.
    Se o pacote não existir, cai em `tr_dfd_generico`.
    """
    key = (slot_package_key or "").strip().lower() or "tr_dfd_generico"
    folder = PACKAGE_DIRS.get(key, PACKAGE_DIRS["tr_dfd_generico"])
    base = LAW_14133_ROOT / folder
    return {
        "base_dir": base,
        "tr": base / "TR_modelo_base.docx",
        "dfd": base / "DFD_modelo_base.docx",
        "oficio": base / "OFICIO_modelo_base.docx",
    }


def ensure_fallback_path(path: Path, legacy_filename: str) -> Path:
    """
    Usa o arquivo do pacote quando existir; senão, retorna fallback legado em template_packages/tr_base.
    """
    if path.exists():
        return path
    return LEGACY_TR_BASE_DIR / legacy_filename
