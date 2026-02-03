#!/bin/sh
# Entrypoint do container llm_api (DocMaster IA).
# Roda como root: ajusta permissões do diretório de auditoria (volume) e sobe o app como appuser.

set -e

# Garante que LLM_AUDIT_LOG_DIR exista e seja gravável pelo appuser (volume ./llm_audit -> /app/logs)
if [ -n "$LLM_AUDIT_LOG_DIR" ]; then
  mkdir -p "$LLM_AUDIT_LOG_DIR"
  chown -R appuser:appuser "$LLM_AUDIT_LOG_DIR" 2>/dev/null || true
fi

PORT="${PORT:-8002}"
exec su -s /bin/sh appuser -c "exec uvicorn app.main:app --host 0.0.0.0 --port $PORT"
