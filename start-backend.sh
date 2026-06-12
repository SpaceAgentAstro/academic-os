#!/bin/bash
# Start the AcademicOS API backend
# Usage: ./start-backend.sh [--reload]
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV_PYTHON="$(dirname "$0")/../../../.venv/bin/uvicorn"
if [ ! -f "$VENV_PYTHON" ]; then
  VENV_PYTHON="/Users/mouadmaamma/academic-os/.venv/bin/uvicorn"
fi

exec "$VENV_PYTHON" backend.main:app --host 0.0.0.0 --port 8000 "$@"
