#!/bin/sh
# Garante permissões de escrita nos volumes SQLite (PNCP + plataformas + crosslink).
set -e

for VAR in PNCP_LOCAL_DB_PATH TCE_RS_LOCAL_DB_PATH PRICE_CROSSLINK_DB_PATH; do
  eval "DB_PATH=\${$VAR:-}"
  if [ -n "$DB_PATH" ]; then
    DB_DIR="$(dirname "$DB_PATH")"
    mkdir -p "$DB_DIR"
    chown -R appuser:appuser "$DB_DIR"
  fi
done

PLATFORM_ROOT="${PRICE_PLATFORM_DATA_ROOT:-/data/platforms}"
CROSSLINK_DIR="$(dirname "${PRICE_CROSSLINK_DB_PATH:-/data/crosslink/price_cross_refs.db}")"
mkdir -p "$PLATFORM_ROOT" "$CROSSLINK_DIR"
chown -R appuser:appuser "$PLATFORM_ROOT" "$CROSSLINK_DIR"

exec gosu appuser "$@"
