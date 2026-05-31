#!/usr/bin/env bash
# Instala systemd para subir DocMaster automaticamente após reboot.
#
# Uso:
#   sudo ./scripts/install-docmaster-boot-service.sh
#   sudo ./scripts/install-docmaster-boot-service.sh --with-pncp-ingest
#
set -euo pipefail

WITH_PNCP_INGEST=0
for arg in "$@"; do
  case "$arg" in
    --with-pncp-ingest) WITH_PNCP_INGEST=1 ;;
    -h|--help)
      echo "Uso: sudo $0 [--with-pncp-ingest]"
      exit 0
      ;;
    *)
      echo "Opção desconhecida: $arg"
      exit 1
      ;;
  esac
done

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Execute com sudo: sudo $0"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
RUN_USER="${SUDO_USER:-${DOCMASTER_RUN_USER:-adryan}}"
RUN_GROUP="$(id -gn "$RUN_USER")"
RUN_HOME="$(getent passwd "$RUN_USER" | cut -d: -f6)"

render_unit() {
  local src="$1"
  local dest="$2"
  sed \
    -e "s|^User=.*|User=${RUN_USER}|" \
    -e "s|^Group=.*|Group=${RUN_GROUP}|" \
    -e "s|^WorkingDirectory=.*|WorkingDirectory=${REPO}|" \
    -e "s|^Environment=DOCMASTER_DEPLOY_DIR=.*|Environment=DOCMASTER_DEPLOY_DIR=${REPO}|" \
    -e "s|^Environment=HOME=.*|Environment=HOME=${RUN_HOME}|" \
    -e "s|^Environment=PNCP_INGEST_LOG=.*|Environment=PNCP_INGEST_LOG=${RUN_HOME}/pncp-ingest.log|" \
    -e "s|^EnvironmentFile=-.*|EnvironmentFile=-${REPO}/.env|" \
    -e "s|^ExecStart=.*ensure-docmaster-stack.sh|ExecStart=${REPO}/scripts/ensure-docmaster-stack.sh|" \
    -e "s|^ExecStart=.*run-pncp-index-ingest-loop.sh|ExecStart=${REPO}/scripts/run-pncp-index-ingest-loop.sh|" \
    "$src" >"$dest"
}

chmod +x "$REPO/scripts/ensure-docmaster-stack.sh" "$REPO/scripts/ensure-pncp-ingest-loop.sh"

echo "==> Docker no boot"
systemctl enable docker.service

echo "==> Instalando docmaster-stack.service (REPO=$REPO, USER=$RUN_USER)"
render_unit "$REPO/deploy/docmaster-stack.service.example" /etc/systemd/system/docmaster-stack.service
systemctl daemon-reload
systemctl enable docmaster-stack.service

if [[ "$WITH_PNCP_INGEST" -eq 1 ]]; then
  echo "==> Instalando docmaster-pncp-ingest.service"
  render_unit "$REPO/deploy/docmaster-pncp-ingest.service.example" /etc/systemd/system/docmaster-pncp-ingest.service
  systemctl enable docmaster-pncp-ingest.service
else
  systemctl disable docmaster-pncp-ingest.service 2>/dev/null || true
fi

echo "==> A subir stack agora"
systemctl start docmaster-stack.service
if [[ "$WITH_PNCP_INGEST" -eq 1 ]]; then
  systemctl start docmaster-pncp-ingest.service
fi

echo ""
systemctl --no-pager status docmaster-stack.service || true
if [[ "$WITH_PNCP_INGEST" -eq 1 ]]; then
  systemctl --no-pager status docmaster-pncp-ingest.service || true
fi

echo ""
echo "OK  Boot automático ativo."
echo "    Após reboot: systemctl status docmaster-stack.service"
echo "    Logs:        journalctl -u docmaster-stack.service -n 80 --no-pager"
if [[ "$WITH_PNCP_INGEST" -eq 1 ]]; then
  echo "    Ingest log:  tail -f ${RUN_HOME}/pncp-ingest.log"
fi
echo "    Doc:         docs/deploy/BOOT-AUTOMATICO.md"
