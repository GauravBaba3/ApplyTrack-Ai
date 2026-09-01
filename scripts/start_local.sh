#!/usr/bin/env bash
# ==============================================================================
# ApplyTrack AI — Local Development Starter Script
# ==============================================================================
# Provides clear, modular startup modes for local development.
# Supports individual process startup or multi-process supervised startup.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"

MODE="${1:-}"

print_usage() {
  echo "ApplyTrack AI — Local Development Helper"
  echo "Usage: $0 [mode]"
  echo ""
  echo "Modes:"
  echo "  backend    Start Django development API server (port 8000)"
  echo "  worker     Start local background email worker daemon"
  echo "  frontend   Start Vite React development server (port 5173/5174)"
  echo "  checks     Run system validation, migration check & frontend build"
  echo "  all        Start Backend, Worker, and Frontend concurrently"
  echo ""
  echo "Examples:"
  echo "  $0 backend"
  echo "  $0 worker"
  echo "  $0 frontend"
  echo "  $0 all"
}

case "${MODE}" in
  backend)
    echo "[INFO] Starting Django Development Server on http://localhost:8000..."
    cd "${BACKEND_DIR}"
    exec python manage.py runserver 0.0.0.0:8000
    ;;

  worker)
    echo "[INFO] Starting Local Email Worker..."
    cd "${BACKEND_DIR}"
    exec python manage.py run_email_worker --worker-id=local-worker-01 --poll-interval=5
    ;;

  frontend)
    echo "[INFO] Starting Vite Frontend Development Server..."
    cd "${FRONTEND_DIR}"
    exec npm run dev
    ;;

  checks)
    echo "[INFO] Running System Checks..."
    "${SCRIPT_DIR}/check_system.sh"
    ;;

  all)
    echo "===================================================================="
    echo "[INFO] Starting all ApplyTrack AI services locally (Supervised)..."
    echo "===================================================================="

    PIDS=()

    cleanup() {
      echo ""
      echo "[INFO] Shutting down all local processes..."
      for pid in "${PIDS[@]}"; do
        if kill -0 "${pid}" 2>/dev/null; then
          kill "${pid}" 2>/dev/null || true
        fi
      done
      wait 2>/dev/null || true
      echo "[INFO] All services stopped cleanly."
    }

    trap cleanup SIGINT SIGTERM EXIT

    # Start Backend
    echo "[INFO] Spawning Backend Server..."
    (cd "${BACKEND_DIR}" && python manage.py runserver 0.0.0.0:8000) &
    PIDS+=($!)

    # Start Worker
    echo "[INFO] Spawning Email Worker..."
    (cd "${BACKEND_DIR}" && python manage.py run_email_worker --worker-id=local-worker-01 --poll-interval=5) &
    PIDS+=($!)

    # Start Frontend
    echo "[INFO] Spawning Frontend Dev Server..."
    (cd "${FRONTEND_DIR}" && npm run dev) &
    PIDS+=($!)

    echo "[INFO] All 3 services running. Press Ctrl+C to terminate all services."
    wait
    ;;

  *)
    print_usage
    exit 1
    ;;
esac
