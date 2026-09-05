#!/usr/bin/env bash
# ==============================================================================
# ApplyTrack AI — Background Email Processing Worker Startup Script
# ==============================================================================
# Starts the Django EmailWorker daemon in the foreground.
# Uses 'exec' to ensure proper UNIX signal propagation (SIGTERM/SIGINT) for
# graceful worker shutdown during deployments and container lifecycle events.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"

echo "===================================================================="
echo "[INFO] Starting ApplyTrack AI Background Email Worker..."
echo "===================================================================="

cd "${BACKEND_DIR}"

# 1. Optionally load .env from backend directory if present
if [ -f "${BACKEND_DIR}/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "${BACKEND_DIR}/.env"
  set +a
fi

# Ensure Python output is completely unbuffered for real-time Render logging
export PYTHONUNBUFFERED=1

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

# Safe database pre-flight check (No credentials or secrets logged)
python -c "
import os, sys
from urllib.parse import urlparse

db_url = os.environ.get('DATABASE_URL', '').strip()
debug_val = os.environ.get('DEBUG', 'True').strip().lower()
is_prod = (debug_val == 'false') or bool(os.environ.get('RENDER'))

if is_prod and not db_url:
    print('[WORKER_DB_ERROR] DATABASE_URL is required in production! Startup aborted.', file=sys.stderr)
    sys.exit(1)

if db_url:
    parsed = urlparse(db_url)
    engine = 'postgresql' if 'postgres' in parsed.scheme else parsed.scheme
    if is_prod and 'sqlite' in engine:
        print('[WORKER_DB_ERROR] Production worker is not allowed to run on SQLite.', file=sys.stderr)
        sys.exit(1)
    db_name = parsed.path.lstrip('/')
    print('[WORKER_DB]')
    print(f'engine={engine}')
    print(f'host={parsed.hostname}')
    print(f'database={db_name}')
else:
    print('[WORKER_DB]')
    print('engine=sqlite3')
    print('host=localhost')
    print('database=db.sqlite3')
"

# Configurable worker parameters from environment
WORKER_ID="${WORKER_ID:-worker-prod-01}"
POLL_INTERVAL="${POLL_INTERVAL:-5}"

WORKER_ARGS=(
  "manage.py"
  "run_email_worker"
  "--worker-id=${WORKER_ID}"
  "--poll-interval=${POLL_INTERVAL}"
)

# Optional batch-size override
if [ -n "${BATCH_SIZE:-}" ]; then
  WORKER_ARGS+=("--batch-size=${BATCH_SIZE}")
fi

# Optional max-batches limit
if [ -n "${MAX_BATCHES:-}" ]; then
  WORKER_ARGS+=("--max-batches=${MAX_BATCHES}")
fi

echo "[INFO] Worker ID: ${WORKER_ID}"
echo "[INFO] Poll Interval: ${POLL_INTERVAL}s"
echo "[INFO] Executing: python -u ${WORKER_ARGS[*]}"

# Use exec to ensure signals are forwarded directly to the Django EmailWorker
exec python -u "${WORKER_ARGS[@]}"

