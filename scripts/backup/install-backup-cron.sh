#!/usr/bin/env bash
# Instala cron diário do backup R2 para o utilizador atual (ou RUN_USER).
#
# Uso (como docmaster, SEM sudo obrigatório):
#   ./scripts/backup/install-backup-cron.sh
#   ./scripts/backup/install-backup-cron.sh --hour 3 --minute 30
#   ./scripts/backup/install-backup-cron.sh --remove
#
# Nota WSL/Windows: o cron só corre se a VM WSL estiver acordada.
# No PC do cliente, registe também a tarefa Windows:
#   scripts/windows-register-r2-backup.ps1
set -euo pipefail

HOUR=3
MINUTE=30
REMOVE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --hour) HOUR="$2"; shift 2 ;;
    --minute) MINUTE="$2"; shift 2 ;;
    --remove) REMOVE=1; shift ;;
    -h|--help)
      echo "Uso: $0 [--hour H] [--minute M] [--remove]"
      exit 0
      ;;
    *)
      echo "Opção desconhecida: $1" >&2
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"
RUNNER="${SCRIPT_DIR}/run-daily-backup.sh"
MARKER="# docmaster-r2-backup"

chmod +x "$RUNNER" \
  "${SCRIPT_DIR}/backup-to-r2.sh" \
  "${SCRIPT_DIR}/verify-r2-backup.sh" \
  "${SCRIPT_DIR}/resume-upload-r2.sh" \
  2>/dev/null || true

ENV_FILE="${BACKUP_R2_ENV:-${HOME}/docmaster-backups/backup-r2.env}"
if [[ "$REMOVE" -eq 0 && ! -f "$ENV_FILE" ]]; then
  echo "ERRO: ${ENV_FILE} não existe. Configure o R2 antes do cron." >&2
  exit 1
fi

# Linha única (cron)
CRON_LINE="${MINUTE} ${HOUR} * * * BACKUP_R2_ENV=${ENV_FILE} RCLONE_CONFIG=${HOME}/docmaster-backups/rclone.conf BACKUP_LOG=${HOME}/docmaster-backups/backup.log ${RUNNER} ${MARKER}"

existing="$(crontab -l 2>/dev/null || true)"
filtered="$(printf '%s\n' "$existing" | grep -vF "$MARKER" || true)"

if [[ "$REMOVE" -eq 1 ]]; then
  printf '%s\n' "$filtered" | crontab -
  echo "OK — cron DocMaster R2 removido."
  crontab -l 2>/dev/null || echo "(crontab vazio)"
  exit 0
fi

{
  printf '%s\n' "$filtered"
  echo "$CRON_LINE"
} | grep -v '^$' | crontab -

echo "OK — cron instalado (${HOUR}:$(printf '%02d' "$MINUTE") diário)"
echo "    ${CRON_LINE}"
echo ""
echo "Log: ${HOME}/docmaster-backups/backup.log"
echo "Teste agora: ${RUNNER}"
echo ""
echo "Em WSL no Windows, registe também a Task Scheduler:"
echo "  powershell -ExecutionPolicy Bypass -File \\\\wsl\$\\DISTRO\\home\\docmaster\\docmaster-core\\scripts\\windows-register-r2-backup.ps1"
crontab -l | grep -F "$MARKER" || true
