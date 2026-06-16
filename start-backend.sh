#!/bin/bash
# Start the AcademicOS API backend
# Usage: ./start-backend.sh [--reload]
#
# Binds to 127.0.0.1 by default — the API has only an optional API-key layer, so
# it must not be published on all interfaces (0.0.0.0) without an authenticating
# reverse proxy in front (AOS-003). Override host/port with HOST / PORT, e.g.
#   HOST=0.0.0.0 API_KEY=... ./start-backend.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

# Prefer an activated virtualenv, then a repo-local .venv, then uvicorn on PATH.
if [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/uvicorn" ]; then
  UVICORN="$VIRTUAL_ENV/bin/uvicorn"
elif [ -x "$SCRIPT_DIR/.venv/bin/uvicorn" ]; then
  UVICORN="$SCRIPT_DIR/.venv/bin/uvicorn"
else
  UVICORN="uvicorn"
fi

exec "$UVICORN" backend.main:app --host "$HOST" --port "$PORT" "$@"
