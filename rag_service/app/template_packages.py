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

# Dispensa rápida usa as mesmas pastas DOCX da dispensa normal (métricas/UI mantêm chave distinta).
PACKAGE_DIR_ALIASES: Dict[str, str] = {
    "dispensa_rapida_75_i_manutencao_veiculos": "dispensa_75_i_manutencao_veiculos",
    "dispensa_rapida_75_i_obras_engenharia": "dispensa_75_i_obras_engenharia",
    "dispensa_rapida_75_ii_compras": "dispensa_75_ii_compras",
    "dispensa_rapida_75_ii_servicos": "dispensa_75_ii_servicos",
    "dispensa_rapida_75_ii_compras_servicos_inclusos": "dispensa_75_ii_compras_servicos_inclusos",
}


def resolve_package_folder(slot_package_key: str | None) -> str:
    """
    Chave do pacote → pasta em lei_14133/.

    Chave desconhecida ou vazia NÃO deve apontar para tr_dfd_generico (pasta vazia no repo):
    isso fazia TR/DFD “funcionarem” via tr_base e Ofício falhar só no fim.
    """
    key = (slot_package_key or "").strip().lower()
    if not key:
        return PACKAGE_DIRS["tr_dfd_generico"]
    if key in PACKAGE_DIRS:
        return PACKAGE_DIRS[key]
    if key in PACKAGE_DIR_ALIASES:
        return PACKAGE_DIR_ALIASES[key]
    if key.startswith("dispensa_rapida_"):
        mapped = "dispensa_" + key[len("dispensa_rapida_") :]
        if mapped in PACKAGE_DIRS:
            return PACKAGE_DIRS[mapped]
    return PACKAGE_DIRS["tr_dfd_generico"]


def _dir_has_any_template_docx(directory: Path) -> bool:
    if not directory.is_dir():
        return False
    for name in ("TR_modelo_base.docx", DFD_MODELO_BASE, "OFICIO_modelo_base.docx"):
        if (directory / name).exists():
            return True
    return False


def package_base_dir_for_folder(folder: str) -> Path:
    """
    Pasta do pacote só se tiver DOCX; senão ancora em tr_base (evita tr_dfd_generico/.gitkeep).
    """
    pkg = LAW_14133_ROOT / folder
    if _dir_has_any_template_docx(pkg):
        return pkg
    return LEGACY_TR_BASE_DIR


def _package_dirs_for_search() -> tuple[Path, ...]:
    """Pastas lei_14133 com modelos (ordem estável, sem duplicar)."""
    seen: set[str] = set()
    dirs: list[Path] = []
    for folder in list(PACKAGE_DIRS.values()) + list(PACKAGE_DIR_ALIASES.values()):
        if folder in seen:
            continue
        seen.add(folder)
        dirs.append(LAW_14133_ROOT / folder)
    return tuple(dirs)


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
    """Resolve caminhos TR/DFD/Ofício; pasta vazia (ex. tr_dfd_generico) usa tr_base como base."""
    key = (slot_package_key or "").strip().lower()
    folder = resolve_package_folder(key)
    base = package_base_dir_for_folder(folder)
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


def ensure_fallback_path(path: Path, legacy_filename: str, *, slot_package_key: str | None = None) -> Path:
    """
    Usa o arquivo do pacote quando existir; senão tr_base; senão qualquer pasta lei_14133 conhecida.
    """
    checked: list[str] = []

    def _try(candidate: Path) -> Path | None:
        checked.append(str(candidate))
        return candidate if candidate.exists() else None

    hit = _try(path)
    if hit:
        return hit

    legacy_default = LEGACY_TR_BASE_DIR / legacy_filename
    hit = _try(legacy_default)
    if hit:
        return hit

    for pkg_dir in _package_dirs_for_search():
        hit = _try(pkg_dir / legacy_filename)
        if hit:
            return hit

    alt_candidates = [
        Path(__file__).resolve().parents[1] / "template_packages" / "tr_base" / legacy_filename,
        Path.cwd() / "template_packages" / "tr_base" / legacy_filename,
    ]
    for candidate in alt_candidates:
        hit = _try(candidate)
        if hit:
            return hit

    key = (slot_package_key or "").strip().lower()
    folder = resolve_package_folder(key) if key else ""
    raise FileNotFoundError(
        "Template não encontrado em nenhum caminho esperado. "
        f"arquivo={legacy_filename}; slot_package_key={key or '(vazio)'}; "
        f"pasta_resolvida={folder or 'tr_dfd_generico'}; caminhos_verificados={checked}"
    )
