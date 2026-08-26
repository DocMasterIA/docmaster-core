#!/usr/bin/env bash
# Configura remote rclone para Cloudflare R2 a partir de backup-r2.env
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

load_backup_env
require_cmd rclone

[[ -n "${R2_ACCESS_KEY_ID:-}" ]] || die "R2_ACCESS_KEY_ID vazio em $BACKUP_R2_ENV_LOADED"
[[ -n "${R2_SECRET_ACCESS_KEY:-}" ]] || die "R2_SECRET_ACCESS_KEY vazio"
[[ -n "${R2_ENDPOINT:-}" ]] || die "R2_ENDPOINT / R2_ACCOUNT_ID em falta"

# Escreve num rclone.conf dedicado (não polui o global sem querer)
RCLONE_CONFIG_FILE="${BACKUP_ROOT}/rclone.conf"
export RCLONE_CONFIG="$RCLONE_CONFIG_FILE"
touch "$RCLONE_CONFIG_FILE"
chmod 600 "$RCLONE_CONFIG_FILE"

log "A configurar remote '${RCLONE_REMOTE}' em ${RCLONE_CONFIG_FILE}"

rclone config delete "${RCLONE_REMOTE}" 2>/dev/null || true

rclone config create "${RCLONE_REMOTE}" s3 \
  provider=Cloudflare \
  access_key_id="${R2_ACCESS_KEY_ID}" \
  secret_access_key="${R2_SECRET_ACCESS_KEY}" \
  endpoint="${R2_ENDPOINT}" \
  acl=private \
  no_check_bucket=true

log "Teste: listar bucket ${R2_BUCKET}..."
rclone lsd "${RCLONE_REMOTE}:${R2_BUCKET}" 2>/dev/null \
  || rclone mkdir "${RCLONE_REMOTE}:${R2_BUCKET}"

rclone lsd "${RCLONE_REMOTE}:${R2_BUCKET}"
log "OK — remote pronto. Use: export RCLONE_CONFIG=${RCLONE_CONFIG_FILE}"
echo "RCLONE_CONFIG=${RCLONE_CONFIG_FILE}"
