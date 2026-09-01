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
echo "[INFO] Executing: python ${WORKER_ARGS[*]}"

# Use exec to ensure signals are forwarded directly to the Django EmailWorker
exec python "${WORKER_ARGS[@]}"
