#!/usr/bin/env bash
# Baixa um stamp do R2 e restaura para os volumes Docker configurados.
# CUIDADO: sobrescreve dados locais. Pare os writers antes.
#
# Uso:
#   ./scripts/backup/restore-from-r2.sh              # current/ (rolling)
#   ./scripts/backup/restore-from-r2.sh current
#   ./scripts/backup/restore-from-r2.sh 20260825-033000 --download-only
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

load_backup_env
require_docker
require_cmd rclone

RCLONE_CONFIG_FILE="${BACKUP_ROOT}/rclone.conf"
[[ -f "$RCLONE_CONFIG_FILE" ]] && export RCLONE_CONFIG="$RCLONE_CONFIG_FILE"

STAMP="${1:-${BACKUP_REMOTE_SLOT}}"
MODE="${2:-}"

if [[ "${BACKUP_MODE}" != "versioned" && ( "$STAMP" == "current" || "$STAMP" == "${BACKUP_REMOTE_SLOT}" ) ]]; then
  DEST="$(r2_remote_path)"
  RESTORE_DIR="${BACKUP_ROOT}/restore/${BACKUP_REMOTE_SLOT}"
else
  DEST="$(r2_prefix_root)/${STAMP}"
  RESTORE_DIR="${BACKUP_ROOT}/restore/${STAMP}"
fi
mkdir -p "$RESTORE_DIR"

log "Download ${DEST} → ${RESTORE_DIR}"
rclone copy "$DEST" "$RESTORE_DIR" --progress
rclone ls "$RESTORE_DIR" | head -n 50 || true

if [[ "$MODE" == "--download-only" ]]; then
  log "Download-only: ficheiros em ${RESTORE_DIR}"
  exit 0
fi

echo ""
echo "Isto vai SOBRESCREVER dados nos volumes:"
echo "  backend DB:   ${VOL_BACKEND_DATA}"
echo "  backend media:${VOL_BACKEND_MEDIA}"
echo "  PNCP:         ${VOL_PNCP_DATA}"
echo "  platforms:    ${VOL_PRICE_PLATFORM}"
echo "  crosslink:    ${VOL_PRICE_CROSSLINK}"
echo ""
echo "Pare backend / pncp_researcher / feeds ANTES de continuar."
read -r -p "Digite RESTORE para confirmar: " confirm
[[ "$confirm" == "RESTORE" ]] || die "Abortado."

restore_sqlite_to_volume() {
  local vol="$1"
  local src_file="$2"
  local dest_rel="$3"
  [[ -f "$src_file" ]] || { log "skip (sem ficheiro): $src_file"; return 0; }
  volume_exists "$vol" || die "volume inexistente: $vol"
  local src_dir src_base
  src_dir="$(dirname "$src_file")"
  src_base="$(basename "$src_file")"
  log "Restore SQLite ${src_base} → ${vol}:${dest_rel}"
  docker run --rm \
    -v "${vol}:/v" \
    -v "${src_dir}:/in:ro" \
    "${BACKUP_TOOL_IMAGE}" \
    python -c "
import os, shutil, sys
src = '/in/' + sys.argv[1]
dest_rel = sys.argv[2].lstrip('/')
# Prefer path that already exists; else write basename at volume root
candidates = [
    '/v/' + dest_rel,
    '/v/' + os.path.basename(dest_rel),
    '/v/pncp/' + os.path.basename(dest_rel),
]
dest = None
for p in candidates:
    parent = os.path.dirname(p)
    if os.path.isdir(parent) and (os.path.isfile(p) or not os.path.exists(p)):
        # if any sibling db exists in parent, use that layout
        dest = p
        break
if dest is None:
    dest = '/v/' + os.path.basename(dest_rel)
os.makedirs(os.path.dirname(dest), exist_ok=True)
# replace atomically-ish
tmp = dest + '.restoring'
shutil.copy2(src, tmp)
os.replace(tmp, dest)
# drop leftover WAL/SHM from old live db if present
for suf in ('-wal', '-shm', '-journal'):
    side = dest + suf
    if os.path.exists(side):
        os.remove(side)
print('restored', dest, 'bytes', os.path.getsize(dest))
" "$src_base" "$dest_rel"
}

restore_media_tar() {
  local vol="$1"
  local tgz="$2"
  [[ -f "$tgz" ]] || { log "skip media (sem tar): $tgz"; return 0; }
  volume_exists "$vol" || die "volume inexistente: $vol"
  log "Restore MEDIA → ${vol}"
  local base
  base="$(basename "$tgz")"
  docker run --rm \
    -v "${vol}:/v" \
    -v "$(dirname "$tgz"):/in:ro" \
    "${BACKUP_TOOL_IMAGE}" \
    bash -c "set -euo pipefail
find /v -mindepth 1 -maxdepth 1 -exec rm -rf {} +
tar -C /v -xzf \"/in/${base}\"
echo restored media
du -sh /v
"
}

[[ "${BACKUP_BACKEND_DB:-1}" == "1" ]] && \
  restore_sqlite_to_volume "${VOL_BACKEND_DATA}" \
    "${RESTORE_DIR}/backend/db.sqlite3" "db.sqlite3"

[[ "${BACKUP_BACKEND_MEDIA:-1}" == "1" ]] && \
  restore_media_tar "${VOL_BACKEND_MEDIA}" "${RESTORE_DIR}/backend/media.tar.gz"

[[ "${BACKUP_PNCP_DB:-1}" == "1" ]] && \
  restore_sqlite_to_volume "${VOL_PNCP_DATA}" \
    "${RESTORE_DIR}/pncp/pncp_researcher_local.db" "pncp_researcher_local.db"

if [[ "${BACKUP_PLATFORM_DBS:-1}" == "1" ]]; then
  for db in tce_rs_local.db compras_gov_local.db notas_fiscais_local.db; do
    restore_sqlite_to_volume "${VOL_PRICE_PLATFORM}" \
      "${RESTORE_DIR}/platforms/${db}" "$db"
  done
fi

[[ "${BACKUP_CROSSLINK_DB:-1}" == "1" ]] && \
  restore_sqlite_to_volume "${VOL_PRICE_CROSSLINK}" \
    "${RESTORE_DIR}/crosslink/price_cross_refs.db" "price_cross_refs.db"

log "=== Restore concluído (${STAMP}) ==="
log "Suba os serviços e valide counts (usuários, itens PNCP, templates)."
echo "STAMP=${STAMP}"
echo "RESTORE_DIR=${RESTORE_DIR}"
