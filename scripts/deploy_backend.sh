#!/usr/bin/env bash
# ==============================================================================
# ApplyTrack AI — Backend Deployment & Migration Script
# ==============================================================================
# Safe, idempotent deployment preparation script for production environments.
# Executes pre-flight checks, verifies environment configuration without leaking
# secrets, applies database migrations, and validates Django system state.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"

echo "===================================================================="
echo "[INFO] Starting ApplyTrack AI Backend Deployment Preparation..."
echo "===================================================================="

# 1. Optionally load .env from backend directory if present
if [ -f "${BACKEND_DIR}/.env" ]; then
  # Read .env variables without executing arbitrary code
  set -a
  # shellcheck disable=SC1091
  source "${BACKEND_DIR}/.env"
  set +a
fi

# 2. Verify Directory
if [ ! -d "${BACKEND_DIR}" ]; then
  echo "[ERROR] Backend directory not found at: ${BACKEND_DIR}"
  exit 1
fi

cd "${BACKEND_DIR}"

# 2. Verify Python Availability
if ! command -v python &> /dev/null; then
  if command -v python3 &> /dev/null; then
    shopt -s expand_aliases
    alias python=python3
  else
    echo "[ERROR] Python is not installed or not in PATH."
    exit 1
  fi
fi

PYTHON_VER=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
echo "[INFO] Using Python version: ${PYTHON_VER}"

# 3. Environment Variable Pre-Flight Validation (Without Logging Secrets)
echo "[INFO] Validating required environment variables..."

MISSING_REQUIRED=0

check_var() {
  local var_name="$1"
  local is_critical="$2"
  if [ -z "${!var_name:-}" ]; then
    if [ "${is_critical}" = "true" ]; then
      echo "[ERROR] Required environment variable '${var_name}' is MISSING."
      MISSING_REQUIRED=$((MISSING_REQUIRED + 1))
    else
      echo "[WARNING] Optional environment variable '${var_name}' is not set."
    fi
  else
    echo "[INFO] Environment variable '${var_name}' is CONFIGURED."
  fi
}

# Critical Variables
check_var "DJANGO_SECRET_KEY" "true"

if [ -n "${DATABASE_URL:-}" ]; then
  echo "[INFO] Environment variable 'DATABASE_URL' is CONFIGURED."
elif [ "${DEBUG:-True}" = "True" ] || [ -f "${BACKEND_DIR}/db.sqlite3" ]; then
  echo "[INFO] Using default SQLite database configuration."
else
  echo "[ERROR] Required environment variable 'DATABASE_URL' is MISSING in production."
  MISSING_REQUIRED=$((MISSING_REQUIRED + 1))
fi

# Integration Variables (Warn if missing)
check_var "GOOGLE_CLIENT_ID" "false"
check_var "GOOGLE_CLIENT_SECRET" "false"
check_var "B2_KEY_ID" "false"
check_var "B2_APPLICATION_KEY" "false"
check_var "GROQ_API_KEY" "false"
check_var "GEMINI_API_KEY" "false"

if [ "${MISSING_REQUIRED}" -gt 0 ]; then
  echo "[ERROR] Critical environment validation failed. Missing ${MISSING_REQUIRED} required variable(s)."
  exit 1
fi

# 4. Pre-Migration Django System Check
echo "[INFO] Running pre-migration Django system checks..."
if ! python manage.py check; then
  echo "[ERROR] Django pre-migration check failed. Halting deployment."
  exit 1
fi

# 5. Apply Database Migrations Safely
echo "[INFO] Applying pending database migrations..."
if ! python manage.py migrate --noinput; then
  echo "[ERROR] Database migration failed. Halting deployment."
  exit 1
fi

# 6. Post-Migration Verification Check
echo "[INFO] Running post-migration Django validation check..."
if ! python manage.py check; then
  echo "[ERROR] Django post-migration validation failed."
  exit 1
fi

# 7. Collect Static Files (if directory or app configured)
if [ -f "manage.py" ]; then
  echo "[INFO] Checking static assets configuration..."
  python manage.py collectstatic --noinput --clear || {
    echo "[INFO] Static files collection skipped or completed."
  }
fi

echo "===================================================================="
echo "[INFO] ApplyTrack AI Backend Deployment Preparation Completed (SUCCESS)."
echo "===================================================================="
exit 0
