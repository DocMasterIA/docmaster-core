#!/bin/sh
# Garante que appuser pode escrever o SQLite em /data/pncp (volume Docker costuma vir como root).
set -e

DB_PATH="${PNCP_LOCAL_DB_PATH:-/data/pncp/pncp_researcher_local.db}"
DB_DIR="$(dirname "$DB_PATH")"
mkdir -p "$DB_DIR"
chown -R appuser:appuser "$DB_DIR"

exec gosu appuser "$@"
