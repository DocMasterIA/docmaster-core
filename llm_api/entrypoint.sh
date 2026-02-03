#!/bin/sh
# Entrypoint do container llm_api (DocMaster IA).
# Roda como root: ajusta permissões do diretório de auditoria (volume) e sobe o app como appuser.

set -e

# Pasta de logs automática: sempre /app/logs no container (volume ./llm_audit no host)
AUDIT_DIR="${LLM_AUDIT_LOG_DIR:-/app/logs}"
mkdir -p "$AUDIT_DIR"
chown -R appuser:appuser "$AUDIT_DIR" 2>/dev/null || true

PORT="${PORT:-8002}"
# cd /app e PYTHONPATH garantem que o módulo "app" seja encontrado (su pode mudar o cwd para /home/appuser)
exec su -s /bin/sh appuser -c "cd /app && exec env PYTHONPATH=/app uvicorn app.main:app --host 0.0.0.0 --port $PORT"
