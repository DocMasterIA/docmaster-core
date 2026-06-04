#!/usr/bin/env bash
# Lista volumes Docker que contêm pncp_researcher_local.db (para recuperar índice antigo).
set -euo pipefail

DB_NAME="pncp_researcher_local.db"
found=0
INSPECT_IMAGE="${PNCP_INSPECT_IMAGE:-docmaster-pncp_researcher_service}"

echo "Procurando ${DB_NAME} em todos os volumes Docker..."
echo "(imagem de inspecção: ${INSPECT_IMAGE}; override: PNCP_INSPECT_IMAGE=...)"
echo ""

while read -r vol; do
  [[ -z "$vol" ]] && continue
  line="$(docker run --rm -v "${vol}":/v:ro "${INSPECT_IMAGE}" python3 -c "
import os, sys
db = sys.argv[1]
for p in ('/v/pncp/' + db, '/v/' + db, '/v/data/pncp/' + db):
    if os.path.isfile(p):
        print(os.path.getsize(p), p)
        sys.exit(0)
sys.exit(1)
" "${DB_NAME}" 2>/dev/null || true)"
  if [[ -z "$line" ]]; then
    line="$(docker run --rm -v "${vol}":/v:ro alpine sh -c "
      for p in /v/pncp/${DB_NAME} /v/${DB_NAME} /v/data/pncp/${DB_NAME}; do
        if [ -f \"\$p\" ]; then
          stat -c '%s %n' \"\$p\"
          exit 0
        fi
      done
      exit 1
    " 2>/dev/null || true)"
  fi
  [[ -z "$line" ]] && continue
  bytes="${line%% *}"
  path="${line#* }"
  mb=$((bytes / 1024 / 1024))
  echo "VOLUME=${vol}"
  echo "  path=${path}"
  echo "  size=${mb} MB (${bytes} bytes)"
  echo ""
  found=1
done < <(docker volume ls -q)

if [[ "$found" -eq 0 ]]; then
  echo "Nenhum volume com ${DB_NAME} encontrado."
  echo "Procure backup .db no host ou outro servidor."
  exit 1
fi

echo "Para usar o volume grande no PNCP, veja: docs/deploy/PNCP-RESEARCHER-24-7.md (secção Recuperar índice)."
