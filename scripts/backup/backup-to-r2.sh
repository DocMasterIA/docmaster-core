#!/usr/bin/env bash
# Backup DocMaster → Cloudflare R2
#
# Objetivo: base recuperável (ex. repor users) SEM reenviar GB todos os dias.
#
# Perfis (BACKUP_PROFILE):
#   auto     — backend: só sobe se o db mudou de tamanho; se subir, arquiva a
#              cópia anterior em history/backend/ (retenção barata ~15MB×N).
#              índices de preço: só se o .db no volume mudou vs R2.
#   critical — só lógica do backend/media (com skip + history)
#   indexes  — só índices
#   full     — força upload de tudo (ainda arquiva backend anterior)
#
# Remoto rolling: current/  +  history/backend/*.sqlite3
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
rclone listremotes | grep -qx "${RCLONE_REMOTE}:" \
  || die "Remote rclone '${RCLONE_REMOTE}' não existe. Rode: ./scripts/backup/setup-rclone-r2.sh"

PROFILE="${BACKUP_PROFILE}"
case "$PROFILE" in
  auto|critical|indexes|full) ;;
  *) die "BACKUP_PROFILE inválido: ${PROFILE} (use auto|critical|indexes|full)" ;;
esac

DO_CRITICAL=0
DO_INDEXES=0
FORCE_ALL=0
case "$PROFILE" in
  auto) DO_CRITICAL=1; DO_INDEXES=1 ;;
  critical) DO_CRITICAL=1 ;;
  indexes) DO_INDEXES=1 ;;
  full) DO_CRITICAL=1; DO_INDEXES=1; FORCE_ALL=1 ;;
esac

STAMP="$(date +%Y%m%d-%H%M%S)"
STAMP_DIR="${STAGING_ROOT}/${STAMP}"
mkdir -p "$STAMP_DIR"/{backend,pncp,platforms,crosslink}

REMOTE_DEST="$(r2_remote_path)"
[[ "${BACKUP_MODE}" == "versioned" ]] && REMOTE_DEST="$(r2_remote_path "$STAMP")"
HISTORY_DEST="$(r2_prefix_root)/history/backend"

log "=== Backup DocMaster → R2 ==="
log "env: ${BACKUP_R2_ENV_LOADED}"
log "profile: ${PROFILE}  mode: ${BACKUP_MODE}"
log "stamp: ${STAMP}"
log "staging: ${STAMP_DIR}"
log "remote: ${REMOTE_DEST}"

ERRORS=0
UPLOADED_INDEXES=0
SKIPPED_INDEXES=0
BACKEND_STATUS="skipped"

upload_path() {
  local local_path="$1"
  local remote_sub="$2"
  [[ -e "$local_path" ]] || return 0
  if [[ -n "$remote_sub" ]]; then
    log "upload → ${REMOTE_DEST}/${remote_sub}"
    rclone copy "$local_path" "${REMOTE_DEST}/${remote_sub}" \
      --progress --s3-upload-concurrency 4 --transfers 4 --retries 10 --retries-sleep 10s
  else
    log "upload → ${REMOTE_DEST}/$(basename "$local_path")"
    rclone copy "$local_path" "${REMOTE_DEST}" \
      --progress --s3-upload-concurrency 4 --transfers 4 --retries 10 --retries-sleep 10s
  fi
}

prune_backend_history() {
  local keep="${BACKUP_BACKEND_HISTORY_KEEP}"
  mapfile -t hist < <(rclone lsf "${HISTORY_DEST}" 2>/dev/null | sed 's|/$||' | sort -r || true)
  if ((${#hist[@]} > keep)); then
    for old in "${hist[@]:keep}"; do
      [[ -z "$old" ]] && continue
      log "Apagar history antigo: ${old}"
      rclone deletefile "${HISTORY_DEST}/${old}" 2>/dev/null \
        || rclone delete "${HISTORY_DEST}/${old}" 2>/dev/null \
        || true
    done
  fi
}

archive_remote_backend_db() {
  local remote_db="${REMOTE_DEST}/backend/db.sqlite3"
  local bytes
  bytes="$(remote_object_bytes "backend/db.sqlite3" | tr -d '[:space:]')"
  bytes="${bytes:-0}"
  if [[ "$bytes" -lt 100 ]]; then
    log "Sem db remoto anterior para arquivar"
    return 0
  fi
  log "Arquivar db atual → history/backend/${STAMP}-db.sqlite3 (${bytes} B)"
  rclone mkdir "${HISTORY_DEST}" 2>/dev/null || true
  rclone copyto "${remote_db}" "${HISTORY_DEST}/${STAMP}-db.sqlite3" \
    --retries 5 --retries-sleep 5s
  prune_backend_history
}

maybe_backup_index() {
  local enabled="$1"
  local vol="$2"
  local rel="$3"
  local dest_file="$4"
  local remote_rel="$5"

  [[ "$enabled" == "1" ]] || return 0
  [[ "$DO_INDEXES" == "1" ]] || return 0

  if [[ "$FORCE_ALL" != "1" ]]; then
    if ! index_db_needs_upload "$vol" "$rel" "$remote_rel"; then
      SKIPPED_INDEXES=$((SKIPPED_INDEXES + 1))
      return 0
    fi
  else
    log "full: forçar índice ${remote_rel}"
  fi

  if ! volume_exists "$vol"; then
    log "AVISO: volume ${vol} inexistente — skip ${remote_rel}"
    return 0
  fi

  if snapshot_sqlite_volume "$vol" "$rel" "$dest_file"; then
    upload_path "$dest_file" "$(dirname "$remote_rel")"
    UPLOADED_INDEXES=$((UPLOADED_INDEXES + 1))
  else
    log "AVISO: falha snapshot ${remote_rel}"
    ERRORS=$((ERRORS + 1))
  fi
}

# --- CRÍTICO: users / dados fixos / media ---
if [[ "$DO_CRITICAL" == "1" && "${BACKUP_BACKEND_DB:-1}" == "1" ]]; then
  log "Backend DB (${VOL_BACKEND_DATA})..."
  if ! volume_exists "${VOL_BACKEND_DATA}"; then
    log "AVISO: volume ${VOL_BACKEND_DATA} não existe"
    ERRORS=$((ERRORS + 1))
  else
    local_b="$(volume_file_bytes "${VOL_BACKEND_DATA}" "db.sqlite3" | tr -d '[:space:]')"
    remote_b="$(remote_object_bytes "backend/db.sqlite3" | tr -d '[:space:]')"
    local_b="${local_b:-0}"
    remote_b="${remote_b:-0}"
    need_backend=0
    if [[ "$FORCE_ALL" == "1" ]]; then
      need_backend=1
      log "full: forçar backend (local=${local_b} remote=${remote_b})"
    elif [[ "$local_b" -lt 100 ]]; then
      log "AVISO: db local inválido/vazio (${local_b} B)"
      ERRORS=$((ERRORS + 1))
    elif [[ "$remote_b" -eq "$local_b" ]]; then
      log "skip backend (sem alteração de tamanho: ${local_b} B) — R2 mantém a cópia atual"
      BACKEND_STATUS="unchanged"
    else
      need_backend=1
      log "backend mudou: local=${local_b} remote=${remote_b} → arquivar + atualizar"
    fi

    if [[ "$need_backend" == "1" ]]; then
      archive_remote_backend_db
      if ! snapshot_sqlite_volume "${VOL_BACKEND_DATA}" "db.sqlite3" \
        "${STAMP_DIR}/backend/db.sqlite3"; then
        snapshot_sqlite_volume "${VOL_BACKEND_DATA}" "backend/data/db.sqlite3" \
          "${STAMP_DIR}/backend/db.sqlite3" \
          || { log "AVISO: backend DB não snapshotado"; ERRORS=$((ERRORS + 1)); }
      fi
      if [[ -f "${STAMP_DIR}/backend/db.sqlite3" ]]; then
        upload_path "${STAMP_DIR}/backend/db.sqlite3" "backend"
        BACKEND_STATUS="updated"
      fi

      if [[ "${BACKUP_BACKEND_MEDIA:-1}" == "1" ]] && volume_exists "${VOL_BACKEND_MEDIA}"; then
        log "Backend MEDIA (só quando db mudou)..."
        if snapshot_dir_volume "${VOL_BACKEND_MEDIA}" "." \
          "${STAMP_DIR}/backend/media.tar.gz"; then
          upload_path "${STAMP_DIR}/backend/media.tar.gz" "backend"
        else
          log "AVISO: media falhou"
          ERRORS=$((ERRORS + 1))
        fi
      fi
    fi
  fi
elif [[ "$DO_CRITICAL" == "1" ]]; then
  log "BACKUP_BACKEND_DB=0 — skip backend"
else
  log "Perfil sem critical — skip backend/media"
fi

FORCE_INDEXES="$FORCE_ALL"
maybe_backup_index "${BACKUP_PNCP_DB:-1}" \
  "${VOL_PNCP_DATA}" "pncp_researcher_local.db" \
  "${STAMP_DIR}/pncp/pncp_researcher_local.db" \
  "pncp/pncp_researcher_local.db"

if [[ "${BACKUP_PLATFORM_DBS:-1}" == "1" ]]; then
  for db in tce_rs_local.db compras_gov_local.db notas_fiscais_local.db; do
    maybe_backup_index 1 \
      "${VOL_PRICE_PLATFORM}" "$db" \
      "${STAMP_DIR}/platforms/${db}" \
      "platforms/${db}"
  done
fi

maybe_backup_index "${BACKUP_CROSSLINK_DB:-1}" \
  "${VOL_PRICE_CROSSLINK}" "price_cross_refs.db" \
  "${STAMP_DIR}/crosslink/price_cross_refs.db" \
  "crosslink/price_cross_refs.db"

write_manifest "$STAMP_DIR" "$STAMP"
if [[ -f "${STAMP_DIR}/manifest.json" ]]; then
  upload_path "${STAMP_DIR}/manifest.json" ""
fi

log "Verificar destino..."
rclone size "${REMOTE_DEST}" || true
rclone ls "${REMOTE_DEST}" | head -n 40 || true
log "Histórico backend (últimos):"
rclone lsf "${HISTORY_DEST}" 2>/dev/null | sort -r | head -n 5 || log "(sem history ainda)"

if [[ "${BACKUP_MODE}" != "versioned" && "${BACKUP_PURGE_OLD_STAMPS}" == "1" ]]; then
  mapfile -t stamps < <(rclone lsf "$(r2_prefix_root)" --dirs-only | sed 's|/$||' || true)
  for old in "${stamps[@]:-}"; do
    [[ -z "$old" || "$old" == "${BACKUP_REMOTE_SLOT}" || "$old" == "history" ]] && continue
    if [[ "$old" =~ ^[0-9]{8}-[0-9]{6}$ ]]; then
      log "Apagar stamp legado: ${old}"
      rclone purge "$(r2_prefix_root)/${old}"
    fi
  done
fi

KEEP_LOCAL="${BACKUP_KEEP_LOCAL_STAGING}"
mapfile -t local_stamps < <(find "$STAGING_ROOT" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort -r)
if ((${#local_stamps[@]} > KEEP_LOCAL)); then
  for old in "${local_stamps[@]:KEEP_LOCAL}"; do
    log "Apagar staging local: ${old}"
    rm -rf "${STAGING_ROOT}/${old}"
  done
fi

log "=== Backup OK profile=${PROFILE} backend=${BACKEND_STATUS} ==="
log "índices uploaded=${UPLOADED_INDEXES} skipped=${SKIPPED_INDEXES} avisos=${ERRORS}"
echo "STAMP=${STAMP}"
echo "BACKUP_PROFILE=${PROFILE}"
echo "BACKUP_MODE=${BACKUP_MODE}"
echo "BACKEND_STATUS=${BACKEND_STATUS}"
echo "REMOTE=${REMOTE_DEST}"
echo "INDEXES_UPLOADED=${UPLOADED_INDEXES}"
echo "INDEXES_SKIPPED=${SKIPPED_INDEXES}"
echo "SNAPSHOT_WARNINGS=${ERRORS}"
