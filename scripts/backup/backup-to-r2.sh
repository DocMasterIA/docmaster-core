#!/usr/bin/env bash
# Snapshot dos volumes críticos + upload para Cloudflare R2 + prune de retenção.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

load_backup_env
require_docker
require_cmd rclone python3

RCLONE_CONFIG_FILE="${BACKUP_ROOT}/rclone.conf"
if [[ -f "$RCLONE_CONFIG_FILE" ]]; then
  export RCLONE_CONFIG="$RCLONE_CONFIG_FILE"
fi
require_cmd rclone
rclone listremotes | grep -qx "${RCLONE_REMOTE}:" \
  || die "Remote rclone '${RCLONE_REMOTE}' não existe. Rode: ./scripts/backup/setup-rclone-r2.sh"

STAMP="$(date +%Y%m%d-%H%M%S)"
STAMP_DIR="${STAGING_ROOT}/${STAMP}"
mkdir -p "$STAMP_DIR"/{backend,pncp,platforms,crosslink}

log "=== Backup DocMaster → R2 ==="
log "env: ${BACKUP_R2_ENV_LOADED}"
log "stamp: ${STAMP}"
log "staging: ${STAMP_DIR}"

ERRORS=0
ok_or_mark() {
  if ! "$@"; then
    log "AVISO: falhou: $*"
    ERRORS=$((ERRORS + 1))
    return 1
  fi
}

# --- Backend SQLite ---
if [[ "${BACKUP_BACKEND_DB:-1}" == "1" ]]; then
  log "Backend DB (${VOL_BACKEND_DATA})..."
  if volume_exists "${VOL_BACKEND_DATA}"; then
    if ! snapshot_sqlite_volume "${VOL_BACKEND_DATA}" "db.sqlite3" \
      "${STAMP_DIR}/backend/db.sqlite3"; then
      if ! snapshot_sqlite_volume "${VOL_BACKEND_DATA}" "backend/data/db.sqlite3" \
        "${STAMP_DIR}/backend/db.sqlite3"; then
        log "AVISO: backend DB não snapshotado"
        ERRORS=$((ERRORS + 1))
      fi
    fi
  else
    log "AVISO: volume ${VOL_BACKEND_DATA} não existe — skip backend DB"
    ERRORS=$((ERRORS + 1))
  fi
fi

# --- Backend MEDIA ---
if [[ "${BACKUP_BACKEND_MEDIA:-1}" == "1" ]]; then
  log "Backend MEDIA (${VOL_BACKEND_MEDIA})..."
  if volume_exists "${VOL_BACKEND_MEDIA}"; then
    ok_or_mark snapshot_dir_volume "${VOL_BACKEND_MEDIA}" "." \
      "${STAMP_DIR}/backend/media.tar.gz" || true
  else
    log "AVISO: volume ${VOL_BACKEND_MEDIA} não existe — skip media"
  fi
fi

# --- PNCP researcher ---
if [[ "${BACKUP_PNCP_DB:-1}" == "1" ]]; then
  log "PNCP DB (${VOL_PNCP_DATA})..."
  if volume_exists "${VOL_PNCP_DATA}"; then
    ok_or_mark snapshot_sqlite_volume "${VOL_PNCP_DATA}" "pncp_researcher_local.db" \
      "${STAMP_DIR}/pncp/pncp_researcher_local.db" || true
  else
    log "AVISO: volume ${VOL_PNCP_DATA} não existe — skip PNCP"
    ERRORS=$((ERRORS + 1))
  fi
fi

# --- Platform DBs ---
if [[ "${BACKUP_PLATFORM_DBS:-1}" == "1" ]]; then
  log "Platform DBs (${VOL_PRICE_PLATFORM})..."
  if volume_exists "${VOL_PRICE_PLATFORM}"; then
    for db in tce_rs_local.db compras_gov_local.db notas_fiscais_local.db; do
      log "  → ${db}"
      snapshot_sqlite_volume "${VOL_PRICE_PLATFORM}" "${db}" \
        "${STAMP_DIR}/platforms/${db}" \
        || log "AVISO: ${db} não encontrado (ok se fonte ainda não ingerida)"
    done
  else
    log "AVISO: volume ${VOL_PRICE_PLATFORM} não existe — skip platforms"
  fi
fi

# --- Crosslink ---
if [[ "${BACKUP_CROSSLINK_DB:-1}" == "1" ]]; then
  log "Crosslink (${VOL_PRICE_CROSSLINK})..."
  if volume_exists "${VOL_PRICE_CROSSLINK}"; then
    snapshot_sqlite_volume "${VOL_PRICE_CROSSLINK}" "price_cross_refs.db" \
      "${STAMP_DIR}/crosslink/price_cross_refs.db" \
      || log "AVISO: price_cross_refs.db não encontrado"
  else
    log "AVISO: volume ${VOL_PRICE_CROSSLINK} não existe — skip crosslink"
  fi
fi

# Garante que há pelo menos um artefato além de pastas vazias
FILE_COUNT="$(find "$STAMP_DIR" -type f ! -name 'manifest.json' | wc -l | tr -d ' ')"
if [[ "${FILE_COUNT}" -eq 0 ]]; then
  die "Nenhum ficheiro snapshotado (erros=${ERRORS}). Confira VOL_* no env e: docker volume ls"
fi
log "Artefactos snapshotados: ${FILE_COUNT} (avisos=${ERRORS})"

write_manifest "$STAMP_DIR" "$STAMP"

REMOTE_DEST="$(r2_remote_path "$STAMP")"
log "Upload → ${REMOTE_DEST}"
rclone copy "${STAMP_DIR}" "${REMOTE_DEST}" \
  --progress \
  --s3-upload-concurrency 4 \
  --transfers 4

log "Verificar objetos remotos..."
rclone ls "${REMOTE_DEST}" | head -n 40
rclone size "${REMOTE_DEST}"

# --- Prune remoto ---
KEEP="${BACKUP_KEEP_REMOTE}"
log "Retenção remota: manter ${KEEP} stamps mais recentes"
mapfile -t stamps < <(rclone lsf "$(r2_remote_path)" --dirs-only | sed 's|/$||' | sort -r)
if ((${#stamps[@]} > KEEP)); then
  for old in "${stamps[@]:KEEP}"; do
    [[ -z "$old" ]] && continue
    log "Apagar remoto antigo: ${old}"
    rclone purge "$(r2_remote_path "$old")"
  done
fi

# --- Prune staging local ---
KEEP_LOCAL="${BACKUP_KEEP_LOCAL_STAGING}"
mapfile -t local_stamps < <(find "$STAGING_ROOT" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort -r)
if ((${#local_stamps[@]} > KEEP_LOCAL)); then
  for old in "${local_stamps[@]:KEEP_LOCAL}"; do
    log "Apagar staging local: ${old}"
    rm -rf "${STAGING_ROOT}/${old}"
  done
fi

log "=== Backup OK: ${STAMP} ==="
echo "STAMP=${STAMP}"
echo "REMOTE=${REMOTE_DEST}"
echo "SNAPSHOT_WARNINGS=${ERRORS}"
if [[ "${ERRORS}" -gt 0 ]]; then
  log "Concluído com ${ERRORS} aviso(s) — confira o log acima."
  exit 0
fi
