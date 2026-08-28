#!/usr/bin/env bash
# Wrapper para backup R2 agendado (cron / Task Scheduler).
# Espera Docker, corre backup-to-r2.sh, regista exit no log.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"

BACKUP_R2_ENV="${BACKUP_R2_ENV:-${HOME}/docmaster-backups/backup-r2.env}"
RCLONE_CONFIG="${RCLONE_CONFIG:-${HOME}/docmaster-backups/rclone.conf}"
BACKUP_LOG="${BACKUP_LOG:-${HOME}/docmaster-backups/backup.log}"
DOCKER_WAIT_SECONDS="${DOCKER_WAIT_SECONDS:-300}"

mkdir -p "$(dirname "$BACKUP_LOG")"
exec >>"$BACKUP_LOG" 2>&1

echo ""
echo "========== $(date -Is) run-daily-backup start =========="
echo "REPO=${REPO}"
echo "BACKUP_R2_ENV=${BACKUP_R2_ENV}"
echo "RCLONE_CONFIG=${RCLONE_CONFIG}"

if [[ ! -f "$BACKUP_R2_ENV" ]]; then
  echo "ERRO: env em falta: ${BACKUP_R2_ENV}"
  exit 1
fi

export BACKUP_R2_ENV RCLONE_CONFIG
# Diário: críticos sempre; índices só se o .db mudou de tamanho no volume
export BACKUP_PROFILE="${BACKUP_PROFILE:-auto}"
export BACKUP_MODE="${BACKUP_MODE:-rolling}"

# PATH típico (cron tem PATH mínimo)
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${HOME}/bin:${PATH}"
if [[ -x /usr/bin/rclone ]]; then
  :
elif [[ -x /usr/local/bin/rclone ]]; then
  :
elif command -v rclone >/dev/null 2>&1; then
  :
else
  echo "ERRO: rclone não encontrado no PATH=${PATH}"
  exit 1
fi

echo "==> A aguardar Docker (até ${DOCKER_WAIT_SECONDS}s)..."
deadline=$((SECONDS + DOCKER_WAIT_SECONDS))
while ! docker info >/dev/null 2>&1; do
  if (( SECONDS >= deadline )); then
    echo "ERRO: Docker não ficou pronto a tempo"
    exit 1
  fi
  sleep 5
done
echo "==> Docker OK"

cd "$REPO"
chmod +x "${SCRIPT_DIR}/backup-to-r2.sh" 2>/dev/null || true

set +e
"${SCRIPT_DIR}/backup-to-r2.sh"
rc=$?
set -e

echo "========== $(date -Is) run-daily-backup end rc=${rc} =========="
exit "$rc"
