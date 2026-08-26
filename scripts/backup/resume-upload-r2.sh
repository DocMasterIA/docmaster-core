#!/usr/bin/env bash
# Retoma upload de um stamp já snapshotado em staging (sem refazer .backup).
# Uso:
#   ./scripts/backup/resume-upload-r2.sh 20260826-040808
#   ./scripts/backup/resume-upload-r2.sh            # usa o staging mais recente
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

REMOTE_DEST="$(r2_remote_path "$STAMP")"
log "Retomar upload ${STAMP_DIR} → ${REMOTE_DEST}"
log "(rclone retoma partes já enviadas; podes correr em tmux/screen)"

# --ignore-existing: não reenvia objetos já completos no remoto
# sem isso, rclone copy também costuma saltar iguais por tamanho/modtime
rclone copy "${STAMP_DIR}" "${REMOTE_DEST}" \
  --progress \
  --s3-upload-concurrency 4 \
  --transfers 4 \
  --retries 10 \
  --low-level-retries 20 \
  --retries-sleep 10s

log "Verificar remoto..."
rclone size "${REMOTE_DEST}"
rclone ls "${REMOTE_DEST}"

KEEP="${BACKUP_KEEP_REMOTE}"
log "Retenção remota: manter ${KEEP} stamps"
mapfile -t stamps < <(rclone lsf "$(r2_remote_path)" --dirs-only | sed 's|/$||' | sort -r)
if ((${#stamps[@]} > KEEP)); then
  for old in "${stamps[@]:KEEP}"; do
    [[ -z "$old" ]] && continue
    log "Apagar remoto antigo: ${old}"
    rclone purge "$(r2_remote_path "$old")"
  done
fi

log "=== Upload OK: ${STAMP} ==="
echo "STAMP=${STAMP}"
echo "REMOTE=${REMOTE_DEST}"
