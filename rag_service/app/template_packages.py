from __future__ import annotations

from pathlib import Path
from typing import Dict


TEMPLATE_PACKAGES_ROOT = Path(__file__).resolve().parents[2] / "template_packages"
PROJECT_ROOT = TEMPLATE_PACKAGES_ROOT.parent
LEGACY_TR_BASE_DIR = TEMPLATE_PACKAGES_ROOT / "tr_base"
LAW_14133_ROOT = TEMPLATE_PACKAGES_ROOT / "lei_14133"

# Nomes dos modelos DFD no disco (cada pasta de pacote em lei_14133/<pasta>/).
DFD_MODELO_BASE = "DFD_modelo_base.docx"
DFD_MODELO_BASE_V2 = "DFD_modelo_base_v2.docx"

# Pastas sob `template_packages/lei_14133/<pasta>/` onde pode existir `DFD_modelo_base_v2.docx`
# (versão sem a linha de «Nº Processo»). Chave do pacote → pasta no disco.
PACKAGE_DIRS: Dict[str, str] = {
    "dispensa_75_i_manutencao_veiculos": "dispensa_75_i_manutencao_veiculos",
    "dispensa_75_i_obras_engenharia": "dispensa_75_i_obras_engenharia",
    "dispensa_75_ii_compras": "dispensa_75_ii_compras",
    "dispensa_75_ii_servicos": "dispensa_75_ii_servicos",
    "dispensa_75_ii_compras_servicos_inclusos": "dispensa_75_ii_compras_servicos_inclusos",
    "inexigibilidade_74_i_fornecedor_exclusivo": "inexigibilidade_74_i_fornecedor_exclusivo",
    "inexigibilidade_74_i_manutencao_veiculos": "inexigibilidade_74_i_manutencao_de_veiculos",
    "tr_dfd_generico": "tr_dfd_generico",
}

# Lista única de pastas físicas (para documentação / checklist de `DFD_modelo_base_v2.docx`).
DFD_V2_ELIGIBLE_PACKAGE_DIRS: tuple[str, ...] = tuple(sorted(set(PACKAGE_DIRS.values())))

CUSTOM_TR_BASE_BY_PACKAGE: Dict[str, str] = {}


def pick_dfd_template_in_package(base_dir: Path, *, has_numero_processo: bool) -> Path:
    """
    Escolhe o DOCX de DFD dentro do pacote.

    - Com número de processo (DFD ou TR): `DFD_modelo_base.docx`.
    - Sem número: `DFD_modelo_base_v2.docx` se existir na pasta do pacote; senão o v1 (mesmo
      fluxo de slots e limpeza de linha vazia que já existia).
    """
    v1 = base_dir / DFD_MODELO_BASE
    v2 = base_dir / DFD_MODELO_BASE_V2
    if not has_numero_processo and v2.exists():
        return v2
    return v1


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
        "dfd": base / DFD_MODELO_BASE,
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
