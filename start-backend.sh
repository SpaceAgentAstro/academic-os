#!/bin/bash
# Start the AcademicOS API backend
# Usage: ./start-backend.sh [--reload]
#
# Binds to 127.0.0.1 by default. Set HOST=0.0.0.0 only behind an
# authenticating reverse proxy / TLS terminator, and set API_KEY first.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

# Prefer an activated virtualenv, then a repo-local .venv, then PATH.
if [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/uvicorn" ]; then
  UVICORN="$VIRTUAL_ENV/bin/uvicorn"
elif [ -x "$SCRIPT_DIR/.venv/bin/uvicorn" ]; then
  UVICORN="$SCRIPT_DIR/.venv/bin/uvicorn"
else
  UVICORN="uvicorn"
fi

exec "$UVICORN" backend.main:app --host "$HOST" --port "$PORT" "$@"
