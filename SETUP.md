# SETUP.md

NYAYMITRA 2.0 — Local setup and development
============================================

## Prerequisites

* Python 3.11+ (3.12+ for the Docker image)
* Node.js (only for the optional browser smoke test)
* `pip`, `venv`

## 1. Clone

```bash
git clone https://github.com/dhundhwana-arch/Nyaymitra-2.0.git
cd Nyaymitra-2.0
git checkout arena/812d6894-nyaymitra-2-0
```

## 2. Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

For development tooling (coverage, audit):

```bash
pip install pytest pytest-cov pip-audit
```

## 3. Configure

Copy the example environment file and review every value:

```bash
cp deploy/nyaymitra.env.example .env
# edit .env — never commit real tokens
```

At minimum set:

* `NYAYMITRA_ADMIN_TOKEN` — at least 24 characters, random, not a placeholder
* `NYAYMITRA_MONITOR_TOKEN` — different from the admin token
* `NYAYMITRA_DB_PATH` — a path outside the repository (e.g. `/data/nyaymitra.db`)
* `NYAYMITRA_STORAGE_DIR` — where uploaded documents live (e.g. `/data/documents`)
* `NYAYMITRA_ENV=production` — only when deploying to production

Leave `NYAYMITRA_AI_PROVIDER=offline` unless you have a reviewed model endpoint
(see `scripts/verify_ai_provider.py`).

## 4. Initialize the database

```bash
python -m backend.app.main
```

This applies migrations (001–004) and seeds the corpus (9 articles, 11 departments,
5 triage guides, 18 glossary terms, 2,125 quarantined legacy rows).

Or run migrations directly:

```bash
python -c "from backend.app.config import load_settings; from backend.app.db import init_database; init_database(load_settings())"
```

## 5. Run

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000/` for the citizen UI and `http://localhost:8000/admin`
for the admin console (requires `NYAYMITRA_ADMIN_TOKEN`).

## 6. Run the test suite

```bash
pytest
```

Expected: all tests pass. Coverage target is 92% (`pytest --cov=backend/app`).

## 7. Dependency audit

```bash
pip-audit --vulnerability-service pypi -r backend/requirements.txt
```

Expected: "No known vulnerabilities found".

## 8. Browser smoke test (optional, needs Node.js)

```bash
npm install --no-save jsdom
NYAYMITRA_ADMIN_TOKEN=local-admin-demo node scripts/smoke_web.mjs http://localhost:8000
```

## 9. Database integrity check

```bash
python scripts/check_db.py
```

## Docker

```bash
docker build -t nyaymitra .
docker run --env-file deploy/nyaymitra.env.example -p 8000:8000 nyaymitra
```

Replace every placeholder in the env file before running. The container runs as a
non-root user and exposes port 8000.

## Zero-budget note

The owner's budget is zero. No paid hosting, no paid domains, no paid API credits are
used or required. Render free tier is suitable only for a read-only demo (its
ephemeral disk loses the database on every restart); for persistent operation use the
Docker image or systemd unit on a host you control.
