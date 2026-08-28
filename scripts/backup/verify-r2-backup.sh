#!/usr/bin/env bash
# Verifica o backup rolling (current/) ou um stamp versionado.
# Uso:
#   ./scripts/backup/verify-r2-backup.sh
#   ./scripts/backup/verify-r2-backup.sh current
#   ./scripts/backup/verify-r2-backup.sh 20260826-040808
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

load_backup_env
require_cmd rclone

RCLONE_CONFIG_FILE="${BACKUP_ROOT}/rclone.conf"
[[ -f "$RCLONE_CONFIG_FILE" ]] && export RCLONE_CONFIG="$RCLONE_CONFIG_FILE"

ARG="${1:-}"

echo "BACKUP_MODE=${BACKUP_MODE}"
log "Prefix root: $(r2_prefix_root)"
echo ""
echo "=== Pastas em ${R2_PREFIX}/ ==="
rclone lsf "$(r2_prefix_root)" --dirs-only | sed 's|/$||' | sort -r | nl || true

if [[ "${BACKUP_MODE}" != "versioned" ]]; then
  DEST="$(r2_remote_path)"
  if [[ -n "$ARG" && "$ARG" != "${BACKUP_REMOTE_SLOT}" && "$ARG" != "current" ]]; then
    DEST="$(r2_prefix_root)/${ARG}"
    log "A inspecionar pasta pedida: ${ARG}"
  fi
else
  STAMP="${ARG:-}"
  if [[ -z "$STAMP" ]]; then
    STAMP="$(rclone lsf "$(r2_prefix_root)" --dirs-only | sed 's|/$||' | sort -r | head -n1 || true)"
    [[ -n "$STAMP" ]] || die "Nenhum stamp no R2."
  fi
  DEST="$(r2_remote_path "$STAMP")"
fi

echo ""
echo "=== Conteúdo ${DEST} ==="
rclone ls "$DEST" || die "Pasta remota vazia ou inexistente"
echo ""
rclone size "$DEST"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
if rclone copy "${DEST}/manifest.json" "$TMP/" 2>/dev/null; then
  echo ""
  echo "=== manifest.json ==="
  python3 -m json.tool "${TMP}/manifest.json" 2>/dev/null || cat "${TMP}/manifest.json"
else
  log "AVISO: sem manifest.json"
fi

log "OK — verify concluído"
echo "REMOTE=${DEST}"
