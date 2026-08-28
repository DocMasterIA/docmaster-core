#!/usr/bin/env bash
# Retoma upload para o destino rolling (current/) ou stamp versionado.
# Uso:
#   ./scripts/backup/resume-upload-r2.sh              # staging mais recente → current/
#   ./scripts/backup/resume-upload-r2.sh 20260826-040808
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

load_backup_env
require_cmd rclone

RCLONE_CONFIG_FILE="${BACKUP_ROOT}/rclone.conf"
[[ -f "$RCLONE_CONFIG_FILE" ]] && export RCLONE_CONFIG="$RCLONE_CONFIG_FILE"

rclone listremotes | grep -qx "${RCLONE_REMOTE}:" \
  || die "Remote rclone '${RCLONE_REMOTE}' não existe. Rode setup-rclone-r2.sh"

STAMP="${1:-}"
if [[ -z "$STAMP" ]]; then
  STAMP="$(find "$STAGING_ROOT" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort -r | head -n1 || true)"
  [[ -n "$STAMP" ]] || die "Nenhum staging em ${STAGING_ROOT}"
  log "Usando staging mais recente: ${STAMP}"
fi

STAMP_DIR="${STAGING_ROOT}/${STAMP}"
[[ -d "$STAMP_DIR" ]] || die "Staging inexistente: ${STAMP_DIR}"

FILE_COUNT="$(find "$STAMP_DIR" -type f ! -name 'manifest.json' | wc -l | tr -d ' ')"
[[ "${FILE_COUNT}" -gt 0 ]] || die "Staging vazio: ${STAMP_DIR}"

if [[ ! -f "${STAMP_DIR}/manifest.json" ]]; then
  write_manifest "$STAMP_DIR" "$STAMP"
fi

if [[ "${BACKUP_MODE}" == "versioned" ]]; then
  REMOTE_DEST="$(r2_remote_path "$STAMP")"
  log "Retomar copy versionado → ${REMOTE_DEST}"
  rclone copy "${STAMP_DIR}" "${REMOTE_DEST}" \
    --progress --transfers 4 --retries 10 --retries-sleep 10s
else
  REMOTE_DEST="$(r2_remote_path)"
  log "Retomar sync rolling → ${REMOTE_DEST}"
  rclone sync "${STAMP_DIR}" "${REMOTE_DEST}" \
    --progress --transfers 4 --retries 10 --retries-sleep 10s
fi

rclone size "${REMOTE_DEST}"
rclone ls "${REMOTE_DEST}" | head -n 40

log "=== Upload OK ==="
echo "STAMP=${STAMP}"
echo "REMOTE=${REMOTE_DEST}"
echo "BACKUP_MODE=${BACKUP_MODE}"
