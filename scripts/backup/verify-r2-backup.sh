#!/usr/bin/env bash
# Lista stamps no R2 e opcionalmente confere um stamp (tamanhos / manifest).
# Uso:
#   ./scripts/backup/verify-r2-backup.sh
#   ./scripts/backup/verify-r2-backup.sh 20260825-033000
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

load_backup_env
require_cmd rclone

RCLONE_CONFIG_FILE="${BACKUP_ROOT}/rclone.conf"
[[ -f "$RCLONE_CONFIG_FILE" ]] && export RCLONE_CONFIG="$RCLONE_CONFIG_FILE"

STAMP="${1:-}"

log "Remote: $(r2_remote_path)"
echo ""
echo "=== Stamps disponíveis ==="
rclone lsf "$(r2_remote_path)" --dirs-only | sed 's|/$||' | sort -r | nl

if [[ -z "$STAMP" ]]; then
  LATEST="$(rclone lsf "$(r2_remote_path)" --dirs-only | sed 's|/$||' | sort -r | head -n1 || true)"
  if [[ -z "$LATEST" ]]; then
    die "Nenhum stamp no R2. Rode backup-to-r2.sh primeiro."
  fi
  STAMP="$LATEST"
  log "Usando stamp mais recente: ${STAMP}"
fi

DEST="$(r2_remote_path "$STAMP")"
echo ""
echo "=== Conteúdo ${STAMP} ==="
rclone ls "$DEST"
echo ""
rclone size "$DEST"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
if rclone copy "${DEST}/manifest.json" "$TMP/" 2>/dev/null; then
  echo ""
  echo "=== manifest.json ==="
  python3 -m json.tool "${TMP}/manifest.json" 2>/dev/null || cat "${TMP}/manifest.json"
else
  log "AVISO: sem manifest.json neste stamp (backup antigo ou incompleto)"
fi

log "OK — verify concluído para ${STAMP}"
echo "STAMP=${STAMP}"
