# NYAYMITRA 2.0 — Installation & Deployment Guide

**Project:** NYAYMITRA 2.0  
**Developed by:** Divyesh Bambhaniya  
**Repository:** [dhundhwana-arch/Nyaymitra-2.0](https://github.com/dhundhwana-arch/Nyaymitra-2.0/tree/arena/2497125a-nyaymitra-2-0)  
**Canonical Branch:** `arena/2497125a-nyaymitra-2-0`  
**Verified Handover Commit:** `9b2ee1f49b70ca2cc8ebafa2f017f7e24cdeee4a`  
**Document Date:** 2026-11-20  

> **Scope & Accuracy Notice:** This guide corrects documented drift in the repository's earlier [`SETUP.md`](https://github.com/dhundhwana-arch/Nyaymitra-2.0/blob/arena/2497125a-nyaymitra-2-0/SETUP.md) (which referenced the superseded branch `arena/812d6894-nyaymitra-2-0` and migrations `001–004`). As of commit `9b2ee1f`, the canonical branch is `arena/2497125a-nyaymitra-2-0`, `backend/migrations/` contains six reversible SQL migration pairs (`001–006`), and **no public cloud deployment is live yet**.

---

## 1. Prerequisites

| Component | Requirement | Purpose |
| :--- | :--- | :--- |
| **Python** | 3.11+ (3.12+ in `Dockerfile`) | FastAPI backend, SQLite/FTS5, migrations, pytest |
| **pip / venv** | Standard Python packaging | Dependency installation (`backend/requirements.txt`, `backend/requirements-dev.txt`) |
| **SQLite** | 3.40+ with FTS5 enabled (bundled with Python) | Primary relational store and full-text search index |
| **Node.js** | 20+ / 22+ (optional) | Frontend syntax checks (`node --check`) and jsdom E2E / smoke scripts |
| **Git** | 2.30+ | Repository checkout and branch management |
| **Docker** *(optional)* | 24+ | Containerized local or cloud deployment via `Dockerfile` |
| **Java 17+ JDK & Android SDK** *(optional, currently missing in sandbox)* | JDK 17+ / Gradle | Required only to compile the Capacitor Android wrapper (`android/`) |

---

## 2. Repository Installation

Clone the repository and check out the verified canonical branch:

```bash
git clone https://github.com/dhundhwana-arch/Nyaymitra-2.0.git
cd Nyaymitra-2.0
git checkout arena/2497125a-nyaymitra-2-0
```

Create and activate an isolated Python virtual environment, then install runtime and development dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
```

If you also plan to run ingestion pipelines (for official PDF/diglot corpus import), install the separate ingestion dependencies (kept separate so AGPL-3.0 `pymupdf` is excluded from the runtime image):

```bash
pip install -r requirements-ingestion.txt
```

---

## 3. Environment Configuration

Copy the tracked template [`.env.example`](https://github.com/dhundhwana-arch/Nyaymitra-2.0/blob/arena/2497125a-nyaymitra-2-0/.env.example) (or `deploy/nyaymitra.env.example`) to `.env` in the repository root. **Never commit `.env`, API keys, or admin tokens to Git.**

```bash
cp .env.example .env
```

### Complete Environment Variable Reference (Verified from `.env.example`)

| Group | Variable | Default | Description |
| :--- | :--- | :--- | :--- |
| **Runtime** | `NYAYMITRA_ENV` | `development` | Set to `production` to enforce startup security preflight checks |
| **Runtime** | `NYAYMITRA_HOST` | `0.0.0.0` | Bind interface for Uvicorn |
| **Runtime** | `NYAYMITRA_PORT` | `8000` | Listening HTTP port |
| **Runtime** | `NYAYMITRA_LOG_LEVEL` | `INFO` | Structured application log level |
| **Runtime** | `NYAYMITRA_DB_PATH` | `data/nyaymitra.db` | SQLite database path (production preflight blocks paths inside git checkout) |
| **Runtime** | `NYAYMITRA_STORAGE_DIR` | `storage/documents` | Uploaded citizen document storage directory |
| **Runtime** | `NYAYMITRA_SERVE_WEB` | `true` | Serve the Vanilla JS SPA from `web/` directly via FastAPI |
| **Runtime** | `NYAYMITRA_ALLOWED_ORIGINS` | *(empty)* | Comma-separated CORS origins; CORS is disabled when empty |
| **Access** | `NYAYMITRA_ADMIN_TOKEN` | *(empty)* | High-entropy secret for `/admin` write operations (`PATCH`, `POST /admin/backup`) |
| **Access** | `NYAYMITRA_MONITOR_TOKEN` | *(empty)* | Distinct high-entropy secret for `/admin` read-only endpoints |
| **AI Provider** | `NYAYMITRA_AI_PROVIDER` | `auto` | Provider mode (`auto`, offline grounded fallback, or OpenAI-compatible) |
| **AI Provider** | `NYAYMITRA_AI_BASE_URL` | *(empty)* | Base URL for OpenAI-compatible inference endpoint |
| **AI Provider** | `NYAYMITRA_AI_MODEL` | *(empty)* | Model identifier for external LLM provider |
| **AI Provider** | `NYAYMITRA_AI_API_KEY` | *(empty)* | Secret API key for external LLM provider (never commit) |
| **AI Provider** | `NYAYMITRA_AI_TIMEOUT_S` | `20` | Upstream LLM request timeout in seconds |
| **AI Provider** | `NYAYMITRA_AI_MAX_OUTPUT_TOKENS` | `700` | Maximum output token cap |
| **AI Provider** | `NYAYMITRA_AI_FALLBACK_MODE` | `offline_grounded` | Fallback behavior when no live LLM key is configured or provider fails |
| **Limits** | `NYAYMITRA_MAX_BODY_BYTES` | `524288` | Max JSON request body size (512 KB) |
| **Limits** | `NYAYMITRA_MAX_UPLOAD_BYTES` | `10485760` | Max multipart upload size (10 MB) |
| **Limits** | `NYAYMITRA_RATE_LIMIT_WINDOW_S` | `60` | Fixed rate-limit window duration in seconds |
| **Limits** | `NYAYMITRA_RATE_LIMIT_READ` | `120` | Per-IP read requests per window |
| **Limits** | `NYAYMITRA_RATE_LIMIT_WRITE` | `30` | Per-IP write requests per window |
| **Limits** | `NYAYMITRA_RATE_LIMIT_AI` | `20` | Per-IP AI endpoint requests per window |
| **Limits** | `NYAYMITRA_RATE_LIMIT_ADMIN` | `10` | Per-IP admin endpoint requests per window |
| **Privacy** | `NYAYMITRA_TRUST_PROXY_HEADERS` | `false` | Trust `X-Forwarded-*` only behind a controlled reverse proxy |
| **Privacy** | `NYAYMITRA_PII_RETENTION_DAYS` | `180` | Default retention period before PII purge eligibility |

> **Admin Security Rule:** Leaving both `NYAYMITRA_ADMIN_TOKEN` and `NYAYMITRA_MONITOR_TOKEN` unset disables `/admin` with HTTP `403`. In `NYAYMITRA_ENV=production`, `create_app()` refuses to start if tokens are unset, short, placeholder-like, low-entropy, or identical; if `NYAYMITRA_DB_PATH` lies inside the Git checkout; or if `NYAYMITRA_TRUST_PROXY_HEADERS=true` without `NYAYMITRA_ALLOWED_ORIGINS`.

Generate high-entropy tokens locally before enabling `/admin`:

```bash
python3 -c "import secrets; print('ADMIN:', secrets.token_urlsafe(32)); print('MONITOR:', secrets.token_urlsafe(32))"
```

---

## 4. Database Initialization & Integrity Check

Initialize SQLite, apply all six reversible migrations (`001_initial.sql` through `006_article_text_normalized.sql`), seed the baseline dataset (9 Constitution article entries, 11 departments, 5 triage guides, 18 glossary terms, and 2,125 quarantined legacy rows), and verify schema integrity:

```bash
python3 scripts/init_db.py --info
python3 scripts/check_db.py
```

Expected verification output from `scripts/check_db.py`: `RESULT: OK` (22 tables, 30 indexes, FTS5 virtual table operational).

---

## 5. Running the Backend & Frontend

### Single-Origin Local Run (Recommended for Demo & Development)

FastAPI serves both the REST API (`/api/v1/*`) and the Vanilla JS frontend (`web/`) when `NYAYMITRA_SERVE_WEB=true`:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Alternatively, use the platform launcher scripts in the repository root:

```bash
./run.sh        # Linux / macOS / Termux
run.bat         # Windows
```

### Local Access URLs

| Surface | URL | Notes |
| :--- | :--- | :--- |
| **Citizen SPA** | `http://localhost:8000/` | 6 hash routes: `#/home`, `#/assistant`, `#/complaint`, `#/library`, `#/departments`, `#/glossary` |
| **Admin Console** | `http://localhost:8000/admin` | Requires valid `NYAYMITRA_ADMIN_TOKEN` or `NYAYMITRA_MONITOR_TOKEN` |
| **Liveness Check** | `http://localhost:8000/api/v1/health` | Returns `{status, version, checks}` (root `/health` is intentionally 404) |
| **Readiness Check** | `http://localhost:8000/api/v1/ready` | Verifies DB, migrations, storage, and AI provider status |
| **System Metadata** | `http://localhost:8000/api/v1/meta` | Returns corpus counts, capabilities, and UI disclaimer banner state |
| **OpenAPI JSON** | `http://localhost:8000/api/openapi.json` | Machine-readable schema (`/api/docs` and `/redoc` disabled by design) |

### Split-Origin Frontend (Cloudflare Pages / Static Host)

The frontend in `web/` is a zero-build Vanilla JS SPA with `_headers`, `_redirects`, `manifest.webmanifest`, `sw.js`, and `config.js`. For split-origin deployment, point `web/config.js` to the deployed FastAPI backend origin and configure `NYAYMITRA_ALLOWED_ORIGINS` on the backend to match the frontend origin.

---

## 6. Available Automated Tests & Checks

| Check | Command | Scope |
| :--- | :--- | :--- |
| **Backend Unit & Integration Suite** | `python3 -m pytest backend/tests` | 22 test modules (460 collected tests) |
| **Source-Quality Tooling Tests** | `python3 -m pytest tests` | 15 tests for ingestion/source tooling |
| **Combined Suite + Coverage** | `python3 -m pytest --cov=backend/app --cov-report=term-missing` | 475 tests total (92% verified coverage on 2026-11-12/14) |
| **Frontend JS Syntax Check** | `node --check web/app.js && node --check web/admin.js` | Syntax validation for citizen and admin scripts |
| **Frontend Smoke Test (jsdom)** | `node scripts/smoke_web.mjs` | 14 checks against a running local `uvicorn` instance |
| **Full E2E Activation (jsdom)** | `node scripts/e2e_activation.mjs` | 43 jsdom E2E checks (single-origin and split-origin) |
| **Database Health Check** | `python3 scripts/check_db.py` | SQLite integrity, migrations, and table checks |
| **AI Provider Verification** | `python3 scripts/verify_ai_provider.py` | Verifies live LLM connectivity (exits `3` when unconfigured) |
| **Dependency Vulnerability Audit** | `pip-audit -r backend/requirements.txt` | Checks runtime dependencies for known CVEs |

---

## 7. Cloud Deployment Requirements & Current Status

**Current Status:** `CONFIGURED, NEVER DEPLOYED` (0 live deployments, 0 environments, 0 releases/tags).

### Configured Deployment Targets
1. **Backend (Render / Docker):** `render.yaml` and `Dockerfile` are committed. Earlier Render builds (`srv-dborak0u01pc7386e2q0`, `srv-dborcv3m8hqs73eqk530`) failed on 2026-11-09 on older commits before the canonical `arena/2497125a-nyaymitra-2-0` branch stabilized. Before deploying to Render:
   - Mount a persistent disk outside the Git checkout for `NYAYMITRA_DB_PATH` and `NYAYMITRA_STORAGE_DIR` (ephemeral disks lose SQLite data on restart).
   - Set `NYAYMITRA_ENV=production`, strong distinct `NYAYMITRA_ADMIN_TOKEN` and `NYAYMITRA_MONITOR_TOKEN`, `NYAYMITRA_ALLOWED_ORIGINS`, and `NYAYMITRA_TRUST_PROXY_HEADERS=true`.
   - Use a single Uvicorn worker (`--workers 1`) while SQLite + in-memory rate limiting are active.
2. **Frontend (Cloudflare Pages):** `wrangler.toml`, `web/_headers`, `web/_redirects`, and `.github/workflows/ci.yml` (`deploy-frontend`) are configured. Deployment is gated on setting the `CLOUDFLARE_API_TOKEN` repository secret in GitHub Actions and confirming the backend API URL in `web/config.js`.
3. **Android Wrapper (Capacitor):** `capacitor.config.js` and `android/` (`in.nyaymitra.app`) are synced, but `./gradlew assembleRelease` has never been executed because JDK 17+ and the Android SDK are unavailable in the development sandbox.

---

## 8. Backup, Recovery & Data Retention

| Operation | Mechanism | Command / Endpoint |
| :--- | :--- | :--- |
| **Automated SQLite Backup** | CLI script or Admin API | `python3 scripts/backup_db.py` or `POST /api/v1/admin/backup` (with `X-Admin-Token`) |
| **Backup Verification** | Built-in `PRAGMA integrity_check` | Verified automatically during `POST /api/v1/admin/backup` and `scripts/check_db.py` |
| **Restore Procedure** | Stop Uvicorn → replace `NYAYMITRA_DB_PATH` with verified `.db` backup → run `scripts/check_db.py` → restart Uvicorn | Manual operator procedure |
| **PII Retention Purge** | `backend/app/services/retention.py` + `scripts/purge_data.py` | `python3 scripts/purge_data.py` (purges records older than `NYAYMITRA_PII_RETENTION_DAYS`, default 180 days; audit trail preserved) |
| **Migration Rollback** | Reversible `.down.sql` pairs (`001–006`) | Take a backup first, then apply target `.down.sql` script in reverse order |
