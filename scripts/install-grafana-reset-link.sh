#!/usr/bin/env bash
# Opcional: remove cópia antiga em ~/scripts e aponta para o script do repo.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${HOME}/scripts/grafana-reset-dashboard.sh"
mkdir -p "${HOME}/scripts"
if [[ -f "$TARGET" ]] && ! grep -q 'grafana-reset-dashboard v3' "$TARGET" 2>/dev/null; then
  mv -f "$TARGET" "${TARGET}.bak.$(date +%Y%m%d%H%M%S)"
  echo "Backup: ${TARGET}.bak.*"
fi
ln -sf "${REPO}/scripts/grafana-reset-dashboard.sh" "$TARGET"
echo "OK — ${TARGET} -> ${REPO}/scripts/grafana-reset-dashboard.sh"
echo "Corra: cd ${REPO} && ./scripts/grafana-reset-dashboard.sh"
