#!/usr/bin/env bash
# ==============================================================================
# ApplyTrack AI — Production Web Service Startup Script
# ==============================================================================
# Starts the Django WSGI production application via Gunicorn.
# Preserves clean process signal forwarding via 'exec'.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"

echo "[INFO] Initializing ApplyTrack AI Production Web Service..."

cd "${BACKEND_DIR}"

# Validate Python
if ! command -v python &> /dev/null; then
  if command -v python3 &> /dev/null; then
    shopt -s expand_aliases
    alias python=python3
  else
    echo "[ERROR] Python not found."
    exit 1
  fi
fi

# Configurable server parameters
BIND_PORT="${PORT:-8000}"
BIND_HOST="0.0.0.0"
WORKERS="${GUNICORN_WORKERS:-2}"
THREADS="${GUNICORN_THREADS:-4}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"

echo "[INFO] Starting Gunicorn on ${BIND_HOST}:${BIND_PORT} (workers=${WORKERS}, threads=${THREADS}, timeout=${TIMEOUT}s)..."

# Use exec so Gunicorn becomes PID 1/foreground process for clean signal forwarding
exec gunicorn config.wsgi:application \
  --bind "${BIND_HOST}:${BIND_PORT}" \
  --workers "${WORKERS}" \
  --threads "${THREADS}" \
  --timeout "${TIMEOUT}" \
  --access-logfile - \
  --error-logfile -
