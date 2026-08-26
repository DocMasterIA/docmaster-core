#!/usr/bin/env bash
# Mostra tamanhos dos DBs nos volumes configurados no backup-r2.env
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

load_backup_env
require_docker

inspect_vol() {
  local label="$1"
  local vol="$2"
  local hint="$3"
  echo ""
  echo "=== ${label}: ${vol} ==="
  if ! volume_exists "$vol"; then
    echo "  VOLUME NAO EXISTE"
    return 0
  fi
  docker run --rm -v "${vol}:/v:ro" "${BACKUP_TOOL_IMAGE}" python -c "
import os
hint = '''${hint}'''
print('  top:', os.listdir('/v')[:30])
found = []
for root, dirs, files in os.walk('/v'):
    if root[len('/v'):].count(os.sep) > 3:
        dirs.clear()
        continue
    for f in files:
        if f.endswith(('.db', '.sqlite3')) or f == hint or hint in f:
            p = os.path.join(root, f)
            found.append((os.path.getsize(p), p))
found.sort(reverse=True)
if not found:
    print('  (nenhum .db/.sqlite3)')
else:
    for sz, p in found[:20]:
        mb = sz / (1024*1024)
        flag = 'OK' if sz >= 100 else 'VAZIO/INVALIDO'
        print(f'  {flag:14} {mb:10.2f} MB  {p}')
"
}

inspect_vol "BACKEND_DATA" "${VOL_BACKEND_DATA}" "db.sqlite3"
inspect_vol "BACKEND_MEDIA" "${VOL_BACKEND_MEDIA}" "."
inspect_vol "PNCP" "${VOL_PNCP_DATA}" "pncp_researcher_local.db"
inspect_vol "PLATFORMS" "${VOL_PRICE_PLATFORM}" "tce_rs_local.db"
inspect_vol "CROSSLINK" "${VOL_PRICE_CROSSLINK}" "price_cross_refs.db"

echo ""
echo "Outros volumes no Docker que parecem candidatos:"
docker volume ls -q | grep -E 'backend|pncp|price|media' || true
echo ""
echo "Se BACKEND/PNCP aparecerem VAZIO, ajuste VOL_* no backup-r2.env para o volume com MB reais."
