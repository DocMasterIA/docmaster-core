#!/usr/bin/env bash
# Verifica pré-requisitos antes de instalar o boot automático (systemd).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${DOCMASTER_ENV_FILE:-$REPO/.env}"
RUN_USER="${SUDO_USER:-${USER:-adryan}}"

ok=0
warn=0
fail=0

pass() { echo "  OK   $*"; ok=$((ok + 1)); }
note() { echo "  AVISO $*"; warn=$((warn + 1)); }
bad()  { echo "  ERRO $*"; fail=$((fail + 1)); }

echo "==> DocMaster boot — pré-requisitos (REPO=$REPO)"
echo ""

if command -v docker >/dev/null 2>&1; then
  pass "docker instalado"
else
  bad "docker não encontrado"
fi

if systemctl is-enabled docker >/dev/null 2>&1; then
  pass "docker.service enabled no boot"
else
  note "docker.service não está enabled — rode: sudo systemctl enable docker"
fi

if id -nG "$RUN_USER" | tr ' ' '\n' | grep -qx docker; then
  pass "utilizador $RUN_USER no grupo docker"
else
  bad "utilizador $RUN_USER fora do grupo docker — sudo usermod -aG docker $RUN_USER && relogar"
fi

if [[ -f "$ENV_FILE" ]]; then
  pass ".env encontrado: $ENV_FILE"
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  if [[ -n "${CLOUDFLARE_TUNNEL_TOKEN:-}" ]]; then
    pass "CLOUDFLARE_TUNNEL_TOKEN definido"
  else
    bad "CLOUDFLARE_TUNNEL_TOKEN vazio em $ENV_FILE (site ficará 1033 sem túnel)"
  fi
else
  bad "ficheiro $ENV_FILE inexistente — cp .env.example .env e preencha o token"
fi

if [[ -f "$REPO/docker-compose.yml" ]]; then
  pass "docker-compose.yml presente"
else
  bad "docker-compose.yml não encontrado em $REPO"
fi

if [[ -x "$REPO/scripts/ensure-docmaster-stack.sh" ]]; then
  pass "ensure-docmaster-stack.sh executável"
else
  note "chmod +x $REPO/scripts/ensure-docmaster-stack.sh"
fi

if systemctl is-enabled docmaster-stack.service >/dev/null 2>&1; then
  pass "docmaster-stack.service já enabled"
elif [[ -f /etc/systemd/system/docmaster-stack.service ]]; then
  note "unit existe mas não enabled — sudo systemctl enable docmaster-stack.service"
else
  note "docmaster-stack.service não instalado — sudo ./scripts/install-docmaster-boot-service.sh"
fi

echo ""
echo "Resumo: $ok OK, $warn avisos, $fail erros"
if [[ "$fail" -gt 0 ]]; then
  echo "Corrija os ERRO antes do boot automático. Ver docs/deploy/BOOT-AUTOMATICO.md"
  exit 1
fi
exit 0
