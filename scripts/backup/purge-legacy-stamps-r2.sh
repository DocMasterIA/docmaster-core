#!/usr/bin/env bash
# Apaga pastas datadas legadas no R2 (ex. 20260826-040808), mantém current/.
# Uso: ./scripts/backup/purge-legacy-stamps-r2.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

load_backup_env
require_cmd rclone

RCLONE_CONFIG_FILE="${BACKUP_ROOT}/rclone.conf"
[[ -f "$RCLONE_CONFIG_FILE" ]] && export RCLONE_CONFIG="$RCLONE_CONFIG_FILE"

ROOT="$(r2_prefix_root)"
log "Prefix: ${ROOT}"
echo "Pastas atuais:"
rclone lsf "$ROOT" --dirs-only | sed 's|/$||' | nl || true
echo ""
read -r -p "Apagar TODAS as pastas datadas YYYYMMDD-HHMMSS (manter '${BACKUP_REMOTE_SLOT}')? digite PURGE: " confirm
[[ "$confirm" == "PURGE" ]] || die "Abortado."

mapfile -t stamps < <(rclone lsf "$ROOT" --dirs-only | sed 's|/$||' || true)
for old in "${stamps[@]:-}"; do
  [[ -z "$old" ]] && continue
  [[ "$old" == "${BACKUP_REMOTE_SLOT}" ]] && continue
  if [[ "$old" =~ ^[0-9]{8}-[0-9]{6}$ ]]; then
    log "purge ${old}"
    rclone purge "${ROOT}/${old}"
  else
    log "skip (nome não datado): ${old}"
  fi
done

echo ""
rclone size "$ROOT" || true
rclone lsf "$ROOT" --dirs-only || true
log "OK — legado limpo. Espaço no R2 deve cair para ~1 cópia (~26GB) se current/ estiver completo."
