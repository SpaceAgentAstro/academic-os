#!/bin/bash
# Start the AcademicOS API backend
# Usage: ./start-backend.sh [--reload]
#
# Binds to 127.0.0.1 by default — do NOT expose the port publicly without an
# authenticating reverse proxy and API_KEY set (see Errors/security.md AOS-001/003).
# Override the bind host/port via HOST / PORT environment variables.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

# Resolve uvicorn from the active virtualenv, a repo-local .venv, or PATH —
# no hardcoded developer paths (AOS-016 / RT-014).
if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/uvicorn" ]; then
  UVICORN="$VIRTUAL_ENV/bin/uvicorn"
elif [ -x "$SCRIPT_DIR/.venv/bin/uvicorn" ]; then
  UVICORN="$SCRIPT_DIR/.venv/bin/uvicorn"
else
  UVICORN="uvicorn"
fi

exec "$UVICORN" backend.main:app --host "$HOST" --port "$PORT" "$@"
