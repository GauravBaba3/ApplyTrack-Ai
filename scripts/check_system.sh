#!/usr/bin/env bash
# ==============================================================================
# ApplyTrack AI — Comprehensive System Health & Readiness Check
# ==============================================================================
# Performs end-to-end configuration and integrity validation across Backend,
# Database, Integrations, and Frontend without leaking any sensitive credentials.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"

# Optionally load .env from backend directory if present
if [ -f "${BACKEND_DIR}/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "${BACKEND_DIR}/.env"
  set +a
fi

echo "===================================================================="
echo "ApplyTrack AI — System & Deployment Readiness Check"
echo "===================================================================="

ERRORS_FOUND=0

# 1. Check Python
echo -n "[CHECK] Python Environment: "
if command -v python &>/dev/null; then
  PY_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
  echo "OK (v${PY_VERSION})"
elif command -v python3 &>/dev/null; then
  PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
  echo "OK (python3 v${PY_VERSION})"
else
  echo "FAILED (Python not found in PATH)"
  ERRORS_FOUND=$((ERRORS_FOUND + 1))
fi

# 2. Check Node & npm
echo -n "[CHECK] Node.js & npm: "
if command -v node &>/dev/null && command -v npm &>/dev/null; then
  NODE_VER=$(node -v)
  NPM_VER=$(npm -v)
  echo "OK (Node ${NODE_VER}, npm v${NPM_VER})"
else
  echo "WARNING (Node.js/npm not found in current shell)"
fi

# 3. Audit Environment Variables (Status Only — Zero Secret Leaks)
echo ""
echo "--- Environment Configuration Audit ---"

check_env() {
  local name="$1"
  local required="$2"
  local label="$3"
  printf "  %-30s : " "${name}"
  if [ -n "${!name:-}" ]; then
    echo "CONFIGURED"
  else
    if [ "${required}" = "true" ]; then
      echo "MISSING (Required)"
      ERRORS_FOUND=$((ERRORS_FOUND + 1))
    else
      echo "NOT SET (Optional - ${label})"
    fi
  fi
}

echo "Core Backend:"
check_env "DJANGO_SECRET_KEY" "true" "Security"
if [ -n "${DATABASE_URL:-}" ]; then
  printf "  %-30s : CONFIGURED (Production / Remote)\n" "DATABASE_URL"
elif [ -f "${BACKEND_DIR}/db.sqlite3" ] || [ "${DEBUG:-True}" = "True" ]; then
  printf "  %-30s : DEFAULT (Local SQLite)\n" "DATABASE_URL"
else
  printf "  %-30s : MISSING (Required in Production)\n" "DATABASE_URL"
  ERRORS_FOUND=$((ERRORS_FOUND + 1))
fi
check_env "ALLOWED_HOSTS" "false" "Networking"
check_env "CORS_ALLOWED_ORIGINS" "false" "CORS"

echo "Google OAuth:"
check_env "GOOGLE_CLIENT_ID" "false" "Gmail OAuth"
check_env "GOOGLE_CLIENT_SECRET" "false" "Gmail OAuth"
check_env "GOOGLE_REDIRECT_URI" "false" "OAuth Callback"

echo "Backblaze B2 Storage:"
check_env "B2_KEY_ID" "false" "Object Storage"
check_env "B2_APPLICATION_KEY" "false" "Object Storage"
check_env "B2_BUCKET_NAME" "false" "Object Storage"

echo "AI Providers:"
check_env "GROQ_API_KEY" "false" "Fast LLM Extraction"
check_env "GEMINI_API_KEY" "false" "LLM Extraction"
check_env "OPENROUTER_API_KEY" "false" "LLM Extraction"
check_env "HF_TOKEN" "false" "Zero-Shot Classification"

# 4. Django System Checks
echo ""
echo "--- Django Application Checks ---"
cd "${BACKEND_DIR}"

echo -n "[CHECK] Django System Check: "
if python manage.py check > /dev/null 2>&1; then
  echo "PASSED"
else
  echo "FAILED"
  python manage.py check || true
  ERRORS_FOUND=$((ERRORS_FOUND + 1))
fi

echo -n "[CHECK] Database Migrations Status: "
if python manage.py migrate --check > /dev/null 2>&1; then
  echo "UP TO DATE (All migrations applied)"
else
  echo "PENDING MIGRATIONS DETECTED (Run python manage.py migrate)"
fi

# 5. Frontend Build Verification (if Node/npm available)
if command -v npm &>/dev/null && [ -d "${FRONTEND_DIR}" ]; then
  echo ""
  echo "--- Frontend Build Verification ---"
  cd "${FRONTEND_DIR}"
  echo -n "[CHECK] TypeScript & Vite Build: "
  if npm run build > /dev/null 2>&1; then
    echo "PASSED (0 TypeScript & bundle errors)"
  else
    echo "FAILED"
    ERRORS_FOUND=$((ERRORS_FOUND + 1))
  fi
fi

echo ""
echo "===================================================================="
if [ "${ERRORS_FOUND}" -eq 0 ]; then
  echo "[RESULT] System Health Check PASSED. All core systems ready."
  exit 0
else
  echo "[RESULT] System Health Check FAILED with ${ERRORS_FOUND} issue(s)."
  exit 1
fi
