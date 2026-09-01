# ApplyTrack AI — Deployment & Startup Automation Guide

This document outlines the production deployment lifecycle, process separation architecture, and local development operations for ApplyTrack AI.

---

## 1. Process Separation Architecture

ApplyTrack AI is designed with strict process isolation across 4 distinct functional tiers:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         APPLYTRACK AI SYSTEM                             │
├───────────────────┬───────────────────┬──────────────────┬───────────────┤
│    WEB SERVICE    │  WORKER SERVICE   │  SCHEDULED CRON  │   FRONTEND    │
│    (Django API)   │   (EmailWorker)   │  (Mgmt Commands) │ (Vite/React)  │
├───────────────────┼───────────────────┼──────────────────┼───────────────┤
│ • Gunicorn WSGI   │ • Priority Queue  │ • Gmail Sync     │ • Glass UI    │
│ • Google OAuth    │ • Backblaze B2 DL │ • P3 Aging       │ • Analytics   │
│ • REST Endpoints  │ • AI Rule Engine  │ • 90d Retention  │ • Real-time   │
│ • Port 8000       │ • Status Pipeline │ • Health Audit   │ • Port 5174   │
└───────────────────┴───────────────────┴──────────────────┴───────────────┘
```

---

## 2. Production Deployment Scripts

All shell scripts are located in the `scripts/` directory and use strict error handling (`set -euo pipefail`) and signal forwarding (`exec`):

| Script | Path | Purpose |
|---|---|---|
| **Deploy Preparation** | [`scripts/deploy_backend.sh`](file:///d:/jobtrack%20ai/ApplyTrack-Ai/scripts/deploy_backend.sh) | Pre-flight validation, environment audit, safe migration application (`python manage.py migrate --noinput`), Django validation, and static asset collection. |
| **Web Service Starter** | [`scripts/start_web.sh`](file:///d:/jobtrack%20ai/ApplyTrack-Ai/scripts/start_web.sh) | Starts Gunicorn WSGI web server (`0.0.0.0:$PORT`) with signal forwarding for graceful reload. |
| **Worker Service Starter** | [`scripts/start_worker.sh`](file:///d:/jobtrack%20ai/ApplyTrack-Ai/scripts/start_worker.sh) | Starts background `EmailWorker` daemon (`--worker-id`, `--poll-interval`) with `SIGTERM`/`SIGINT` handling. |
| **Local Development** | [`scripts/start_local.sh`](file:///d:/jobtrack%20ai/ApplyTrack-Ai/scripts/start_local.sh) | Multi-mode starter (`backend`, `worker`, `frontend`, `checks`, or `all` with sub-process cleanup trap). |
| **System Health Check** | [`scripts/check_system.sh`](file:///d:/jobtrack%20ai/ApplyTrack-Ai/scripts/check_system.sh) | Audits Python, Node/npm, environment variables (masks all secrets), Django checks, migration status, and frontend build. |

---

## 3. Render Deployment Configuration (`render.yaml`)

The infrastructure blueprint defines isolated services:

```yaml
services:
  # 1. Web Service (Django REST API)
  - type: web
    name: applytrack-api
    runtime: python
    rootDir: backend
    buildCommand: "pip install -r requirements.txt && bash ../scripts/deploy_backend.sh"
    startCommand: "bash ../scripts/start_web.sh"
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.9
      - key: DEBUG
        value: "False"

  # 2. Background Worker Service (Email Processing & Multi-Tier AI Cascade)
  - type: worker
    name: applytrack-worker
    runtime: python
    rootDir: backend
    buildCommand: "pip install -r requirements.txt"
    startCommand: "bash ../scripts/start_worker.sh"
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.9
      - key: WORKER_ID
        value: worker-prod-01
      - key: POLL_INTERVAL
        value: "5"

  # 3. Scheduled Cron Job: Incremental Gmail Sync (Every 15 minutes)
  - type: cron
    name: applytrack-sync-gmail
    runtime: python
    rootDir: backend
    schedule: "*/15 * * * *"
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python manage.py sync_gmail_incremental"

  # 4. Scheduled Cron Job: P3 Anti-Starvation & Aging (Hourly)
  - type: cron
    name: applytrack-p3-aging
    runtime: python
    rootDir: backend
    schedule: "0 * * * *"
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python manage.py reprocess_p3_queue"

  # 5. Scheduled Cron Job: 90-Day Raw Email Backblaze B2 Retention Pruning (Daily at 03:00 UTC)
  - type: cron
    name: applytrack-prune-retention
    runtime: python
    rootDir: backend
    schedule: "0 3 * * *"
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python manage.py prune_raw_emails"
```

---

## 4. Local Development Execution

### Using Shell Scripts (Linux / macOS / Git Bash / WSL)
```bash
# 1. Run full readiness check
./scripts/check_system.sh

# 2. Start individual services
./scripts/start_local.sh backend    # Starts Django API on http://localhost:8000
./scripts/start_local.sh worker     # Starts EmailWorker daemon
./scripts/start_local.sh frontend   # Starts Vite dev server on http://localhost:5174

# 3. Or start all services simultaneously with auto-cleanup
./scripts/start_local.sh all
```

### Windows PowerShell Equivalents
```powershell
# Terminal 1: Backend API
cd backend
python manage.py runserver 0.0.0.0:8000

# Terminal 2: Email Processing Worker
cd backend
python manage.py run_email_worker --worker-id=local-worker-01 --poll-interval=5

# Terminal 3: Frontend Dev Server
cd frontend
npm run dev
```

---

## 5. Security & Zero Secret Leakage Audit
- All script outputs mask credentials and display status tags only (`CONFIGURED`, `PRESENT`, `DEFAULT (Local SQLite)`, or `MISSING`).
- Zero API keys, OAuth secrets, database passwords, or Backblaze B2 credentials are leaked in shell outputs or system logs.
- Worker signal handling supports graceful shutdown without terminating in-flight message processing.
