# shellcheck shell=bash
# Utilizador que corre docker compose / systemd (nunca root).
docmaster_resolve_run_user() {
  local repo="${1:-}"
  local u="${DOCMASTER_RUN_USER:-${SUDO_USER:-}}"

  if [[ -z "$u" || "$u" == "root" ]]; then
    if [[ -n "$repo" && -d "$repo" ]]; then
      u="$(stat -c '%U' "$repo" 2>/dev/null || true)"
    fi
  fi
  if [[ -z "$u" || "$u" == "root" ]]; then
    u="${USER:-}"
  fi
  if [[ -z "$u" || "$u" == "root" ]]; then
    u="docmaster"
  fi
  printf '%s' "$u"
}
