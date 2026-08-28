#!/usr/bin/env bash
# Biblioteca partilhada — backup R2 DocMaster.
# shellcheck disable=SC2034

set -euo pipefail

# Este ficheiro vive em scripts/backup/lib/
_BACKUP_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_BACKUP_REPO_ROOT="$(cd "${_BACKUP_LIB_DIR}/../../.." && pwd)"

load_backup_env() {
  local env_file="${BACKUP_R2_ENV:-}"
  if [[ -z "$env_file" ]]; then
    if [[ -f "${HOME}/docmaster-backups/backup-r2.env" ]]; then
      env_file="${HOME}/docmaster-backups/backup-r2.env"
    elif [[ -f "${_BACKUP_REPO_ROOT}/config/backup-r2.env" ]]; then
      env_file="${_BACKUP_REPO_ROOT}/config/backup-r2.env"
    else
      echo "ERRO: defina BACKUP_R2_ENV ou crie ~/docmaster-backups/backup-r2.env" >&2
      echo "  cp ${_BACKUP_REPO_ROOT}/config/backup-r2.env.example ~/docmaster-backups/backup-r2.env" >&2
      exit 1
    fi
  fi
  if [[ ! -f "$env_file" ]]; then
    echo "ERRO: ficheiro env não encontrado: $env_file" >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  set -a
  # shellcheck source=/dev/null
  source "$env_file"
  set +a
  export BACKUP_R2_ENV_LOADED="$env_file"

  RCLONE_REMOTE="${RCLONE_REMOTE:-docmaster_r2}"
  R2_BUCKET="${R2_BUCKET:-docmaster-backups}"
  R2_PREFIX="${R2_PREFIX:-docmaster}"
  BACKUP_ROOT="${BACKUP_ROOT:-${HOME}/docmaster-backups}"
  # rolling (default): um único destino current/ — atualiza no sítio, NÃO empilha GB/dia
  # versioned: pasta datada por corrida (só se precisares de histórico explícito)
  BACKUP_MODE="${BACKUP_MODE:-rolling}"
  BACKUP_REMOTE_SLOT="${BACKUP_REMOTE_SLOT:-current}"
  # auto (default diário): users/media sempre; índices de preço só se o .db no volume mudou de tamanho
  # critical: só backend db + media
  # indexes: só pncp/platforms/crosslink (respeita skip-if-unchanged)
  # full: força snapshot+upload de tudo
  BACKUP_PROFILE="${BACKUP_PROFILE:-auto}"
  # Quantas cópias antigas do db.sqlite3 guardar em history/backend/ (recuperar users apagados)
  BACKUP_BACKEND_HISTORY_KEEP="${BACKUP_BACKEND_HISTORY_KEEP:-14}"
  BACKUP_KEEP_REMOTE="${BACKUP_KEEP_REMOTE:-2}"
  BACKUP_KEEP_LOCAL_STAGING="${BACKUP_KEEP_LOCAL_STAGING:-1}"
  BACKUP_TOOL_IMAGE="${BACKUP_TOOL_IMAGE:-python:3.12-slim-bookworm}"
  BACKUP_PURGE_OLD_STAMPS="${BACKUP_PURGE_OLD_STAMPS:-1}"

  if [[ -z "${R2_ENDPOINT:-}" && -n "${R2_ACCOUNT_ID:-}" ]]; then
    R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
  fi

  STAGING_ROOT="${BACKUP_ROOT}/staging"
  mkdir -p "$BACKUP_ROOT" "$STAGING_ROOT"
}

require_cmd() {
  local c
  for c in "$@"; do
    if ! command -v "$c" >/dev/null 2>&1; then
      echo "ERRO: comando obrigatório em falta: $c" >&2
      exit 1
    fi
  done
}

require_docker() {
  require_cmd docker
  if ! docker info >/dev/null 2>&1; then
    echo "ERRO: Docker não está acessível (daemon off ou permissão)." >&2
    exit 1
  fi
}

volume_exists() {
  local vol="$1"
  [[ -n "$vol" ]] && docker volume inspect "$vol" >/dev/null 2>&1
}

# Destino remoto do backup “atual”.
# rolling → prefix/current  |  versioned → prefix/<stamp>
r2_remote_path() {
  local stamp="${1:-}"
  if [[ "${BACKUP_MODE}" == "versioned" ]]; then
    if [[ -n "$stamp" ]]; then
      echo "${RCLONE_REMOTE}:${R2_BUCKET}/${R2_PREFIX}/${stamp}"
    else
      echo "${RCLONE_REMOTE}:${R2_BUCKET}/${R2_PREFIX}"
    fi
  else
    echo "${RCLONE_REMOTE}:${R2_BUCKET}/${R2_PREFIX}/${BACKUP_REMOTE_SLOT}"
  fi
}

r2_prefix_root() {
  echo "${RCLONE_REMOTE}:${R2_BUCKET}/${R2_PREFIX}"
}

# Tamanho de um ficheiro dentro de um volume Docker (0 se não existir).
volume_file_bytes() {
  local vol="$1"
  local rel="$2"
  volume_exists "$vol" || { echo 0; return 0; }
  docker run --rm -v "${vol}:/v:ro" "${BACKUP_TOOL_IMAGE}" python -c "
import os, sys
rel = sys.argv[1].lstrip('/')
base = os.path.basename(rel)
cands = [
    '/v/' + rel,
    '/v/data/' + rel,
    '/v/pncp/' + base,
    '/v/platforms/' + base,
    '/v/crosslink/' + base,
    '/v/' + base,
]
for p in cands:
    if os.path.isfile(p):
        print(os.path.getsize(p))
        raise SystemExit(0)
for root, dirs, files in os.walk('/v'):
    if root[len('/v'):].count(os.sep) > 3:
        dirs.clear()
        continue
    if base in files:
        print(os.path.getsize(os.path.join(root, base)))
        raise SystemExit(0)
print(0)
" "$rel" 2>/dev/null || echo 0
}

# Tamanho de um objeto no R2 (0 se não existir). path relativo ao slot current/, ex: pncp/foo.db
remote_object_bytes() {
  local rel="$1"
  local dest
  dest="$(r2_remote_path)"
  # rclone lsl: "  12345 2026-01-01 00:00:00.000 path"
  local line
  line="$(rclone lsl "${dest}/${rel}" 2>/dev/null | head -n1 || true)"
  if [[ -z "$line" ]]; then
    echo 0
    return 0
  fi
  # primeiro campo numérico
  echo "$line" | awk '{print $1; exit}'
}

# 0 = igual (skip); 1 = precisa upload
index_db_needs_upload() {
  local vol="$1"
  local rel="$2"
  local remote_rel="$3"
  local local_b remote_b
  local_b="$(volume_file_bytes "$vol" "$rel" | tr -d '[:space:]')"
  remote_b="$(remote_object_bytes "$remote_rel" | tr -d '[:space:]')"
  local_b="${local_b:-0}"
  remote_b="${remote_b:-0}"
  if [[ "$local_b" -lt 100 ]]; then
    log "índice local ausente/vazio: ${vol}:${rel} (${local_b} B)"
    return 1
  fi
  if [[ "$remote_b" -eq "$local_b" ]]; then
    log "skip índice (tamanho igual ${local_b} B): ${remote_rel}"
    return 1
  fi
  log "índice mudou: ${remote_rel} local=${local_b} remote=${remote_b} → upload"
  return 0
}

log() {
  echo "[$(date -Is)] $*"
}

die() {
  echo "ERRO: $*" >&2
  exit 1
}

# Snapshot SQLite consistente (.backup) de um ficheiro dentro de um volume Docker.
# Uso: snapshot_sqlite_volume VOL_NAME REL_PATH_IN_VOL DEST_FILE
#
# Nota: volumes :ro + WAL falham com "unable to open database file".
# Estratégia: copiar .db (+ -wal/-shm se existirem) para /out e aí fazer .backup.
snapshot_sqlite_volume() {
  local vol="$1"
  local rel="$2"
  local dest="$3"
  local dest_dir
  dest_dir="$(dirname "$dest")"
  mkdir -p "$dest_dir"

  volume_exists "$vol" || die "volume inexistente: $vol"

  docker run --rm \
    -v "${vol}:/v:ro" \
    -v "${dest_dir}:/out" \
    "${BACKUP_TOOL_IMAGE}" \
    python -c "
import os, shutil, sqlite3, sys

src_rel = sys.argv[1]
out_name = sys.argv[2]
base = os.path.basename(src_rel)
candidates = [
    '/v/' + src_rel.lstrip('/'),
    '/v/data/' + src_rel.lstrip('/'),
    '/v/pncp/' + base,
    '/v/platforms/' + base,
    '/v/crosslink/' + base,
    '/v/' + base,
]
src = next((p for p in candidates if os.path.isfile(p)), None)
if src is None:
    # procura por basename até profundidade 3
    for root, dirs, files in os.walk('/v'):
        depth = root[len('/v'):].count(os.sep)
        if depth > 3:
            dirs.clear()
            continue
        if base in files:
            src = os.path.join(root, base)
            break
if src is None:
    print('FICHEIRO NAO ENCONTRADO. Tentados:', candidates, file=sys.stderr)
    try:
        print('top /v:', os.listdir('/v')[:40], file=sys.stderr)
    except Exception as e:
        print(e, file=sys.stderr)
    sys.exit(2)

src_size = os.path.getsize(src)
if src_size < 100:
    print(
        f'FICHEIRO INVALIDO/VAZIO: {src} ({src_size} bytes). '
        'Volume provavelmente errado ou DB corrompido/vazio.',
        file=sys.stderr,
    )
    sys.exit(3)

raw_dir = '/out/.snap_raw_' + out_name.replace('.', '_')
os.makedirs(raw_dir, exist_ok=True)
raw_db = os.path.join(raw_dir, base)
for suf in ('', '-wal', '-shm', '-journal'):
    p = src + suf
    if os.path.isfile(p):
        shutil.copyfile(p, raw_db + suf)

out = '/out/' + out_name
if os.path.exists(out):
    os.remove(out)

# Abre a cópia local (RW em /out) — evita falha WAL em volume :ro
try:
    s = sqlite3.connect(f'file:{raw_db}?mode=ro', uri=True)
except sqlite3.OperationalError:
    s = sqlite3.connect(f'file:{raw_db}?immutable=1', uri=True)
d = sqlite3.connect(out)
with d:
    s.backup(d)
s.close()
d.close()

# limpa cópia bruta (mantém só o .backup final)
shutil.rmtree(raw_dir, ignore_errors=True)
print(src, '->', out, 'bytes', os.path.getsize(out))
" "$rel" "$(basename "$dest")"
}

# Empacota MEDIA (ou pasta) de um volume para tar.gz
# Uso: snapshot_dir_volume VOL_NAME REL_DIR DEST_TGZ
snapshot_dir_volume() {
  local vol="$1"
  local rel="$2"
  local dest="$3"
  local dest_dir
  dest_dir="$(dirname "$dest")"
  mkdir -p "$dest_dir"

  volume_exists "$vol" || die "volume inexistente: $vol"

  docker run --rm \
    -v "${vol}:/v:ro" \
    -v "${dest_dir}:/out" \
    "${BACKUP_TOOL_IMAGE}" \
    bash -c '
set -euo pipefail
rel="'"$rel"'"
out="/out/'"$(basename "$dest")"'"
# Django media pode estar na raiz do volume ou sob media/
if [ -d "/v/${rel}" ]; then
  src="/v/${rel}"
elif [ -d "/v" ] && [ "'"$rel"'" = "." ]; then
  src="/v"
elif [ -d /v/media ]; then
  src=/v/media
else
  src=/v
fi
tar -C "$src" -czf "$out" .
ls -lh "$out"
'
}

write_manifest() {
  local stamp_dir="$1"
  local stamp="$2"
  local manifest="${stamp_dir}/manifest.json"
  python3 - "$manifest" "$stamp" <<'PY' || true
import json, os, sys, time
manifest, stamp = sys.argv[1], sys.argv[2]
root = os.path.dirname(manifest)
files = []
for dirpath, _, names in os.walk(root):
    for n in names:
        if n == "manifest.json":
            continue
        p = os.path.join(dirpath, n)
        rel = os.path.relpath(p, root)
        files.append({"path": rel, "bytes": os.path.getsize(p)})
doc = {
    "stamp": stamp,
    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "host": os.uname().nodename if hasattr(os, "uname") else "",
    "files": files,
    "total_bytes": sum(f["bytes"] for f in files),
}
with open(manifest, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2, ensure_ascii=False)
print(manifest, "files", len(files), "total_bytes", doc["total_bytes"])
PY
}
