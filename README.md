# NYAYMITRA 2.0

**Inclusive justice-access and legal-navigation platform.** It helps a citizen describe a problem
in Gujarati or English, find the constitutional provision that applies, understand the official
next step, prepare a complaint draft, and reach the right department or free-legal-aid channel.

It is **not** a lawyer, a court or a judge. It does not decide cases, predict outcomes or
guarantee results, and it never presents unverified material as official law.

---

## Current status (be precise before you rely on it)

| Area | Status |
|---|---|
| Backend API (31 endpoints), database, migrations, seeds | **COMPLETE AND TESTED** |
| Retrieval-before-generation, citation validation, offline grounded answers | **COMPLETE AND TESTED** |
| Complaint intake with deterministic summary, review gate, one-time token | **COMPLETE AND TESTED** |
| Document upload (PDF/image), extraction status, owner-token download | **COMPLETE AND TESTED** |
| Citizen web app (6 routes, gu/en) and admin console | **IMPLEMENTED AND TESTED IN JSDOM** — no real phone/browser session yet |
| Voice input / speech output | **IMPLEMENTED BUT NOT TESTED** (browser APIs) |
| Live LLM provider (`openai_compatible`) | **IMPLEMENTED BUT NOT TESTED** (no API key available) |
| Authoritative Article text in Gujarati/English | **BLOCKED** — official source PDFs not supplied by the owner |
| Legal accuracy of every explanation, helpline and department entry | **REQUIRES HUMAN VERIFICATION** (queue in `/admin`) |
| Automated test suite | **119 tests, 90% line coverage, all passing** |

The corpus ships with **9 human-written article explanations and 0 authoritative texts**. The API
says so on every answer, and the UI shows a warning banner. See
[`docs/LEGAL_VERIFICATION_CHECKLIST.md`](docs/LEGAL_VERIFICATION_CHECKLIST.md).

---

## Quick start

```bash
git clone https://github.com/dhundhwana-arch/Nyaymitra-2.0.git
cd Nyaymitra-2.0
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt

python scripts/init_db.py --info          # migrate + seed (idempotent), print table counts
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

* Citizen app — <http://localhost:8000/>
* Administration — <http://localhost:8000/admin> (set `NYAYMITRA_ADMIN_TOKEN` first)
* Machine-readable API — <http://localhost:8000/api/openapi.json>

`./run.sh` does the same in one step (Linux/macOS); `run.bat` on Windows.
With no AI key configured the app runs fully offline in rule-based, source-grounded mode.

### Try these

| Action | Expected |
|---|---|
| Ask “કાયદા સમક્ષ સમાનતા શું છે?” | Answer citing **Article 14**, labelled requires-human-verification, with disclaimer |
| Ask “zzz qqq” | Explicit “no related article found” — no guess, no invented citation |
| File a complaint | Summary preview on screen **before** anything is saved; reference + token shown once |
| Open `/admin` with the token | Stats, verification queue, redacted queries, errors, complaints metadata, document index |

---

## What is in the box

```
backend/app/          FastAPI application (factory `create_app`)
  ai/                 provider abstraction, retrieval, citation validation, safety guard
  routers/            health, constitution, ai, complaints, documents, departments, feedback, admin
  services/           constitution search, textsearch, complaints, documents, departments,
                      triage, glossary, seeding, ingestion, monitoring
backend/migrations/   versioned SQL with down-migrations
backend/tests/        119 pytest tests
web/                  self-hosted SPA (no CDN) + admin console
data/seed/            curated seed JSON (sources, 9 articles, departments, triage, glossary)
data/legacy/          quarantined 2,125 legacy rows (gzip + sha256), never served to citizens
data/raw/             where the owner puts official Constitution PDFs (git-ignored)
scripts/              init_db, backup_db, ingest_constitution, export_legacy, smoke_web
docs/                 audit, architecture, API, schema, testing, security, legal, deployment
```

Needless to say, the old `backend/database.py`, `frontend/library_fix.js` and other broken
prototype files are archived under `frontend/legacy/` and `scripts/legacy/` with notes; they are
not served.

---

## Tests

```bash
python -m pytest                                  # 119 passed, 90% coverage
python -m pytest -q --cov=backend/app             # coverage report
node --check web/app.js web/admin.js              # frontend syntax
node scripts/smoke_web.mjs http://127.0.0.1:8000  # optional jsdom journeys (needs jsdom)
```

Detailed, honest results — including what is *not* covered — are in
[`docs/TESTING_REPORT.md`](docs/TESTING_REPORT.md). CI runs the suite on Python 3.11 and 3.12
(`.github/workflows/ci.yml`).

---

## Documentation

| Document | What it answers |
|---|---|
| [REPOSITORY_AUDIT.md](docs/REPOSITORY_AUDIT.md) | What was wrong with the repository this replaced |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | How the system is put together and why |
| [INTEGRATION_PLAN.md](docs/INTEGRATION_PLAN.md) | Phased plan, design rules, what was reused from where |
| [FEATURE_STATUS.md](docs/FEATURE_STATUS.md) | Feature-by-feature status with evidence |
| [API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) | Endpoints, schemas, errors, examples |
| [DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | Tables, indexes, migrations, retention |
| [TESTING_REPORT.md](docs/TESTING_REPORT.md) | Commands, results, gaps |
| [SECURITY_AUDIT.md](docs/SECURITY_AUDIT.md) | Threat model, controls, fixed findings, residual risk |
| [LEGAL_VERIFICATION_CHECKLIST.md](docs/LEGAL_VERIFICATION_CHECKLIST.md) | What a human must sign off before this is legal information |
| [KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) | What does not work yet |
| [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) | Local, server, backups, upgrades, rollback |

---

## Licence and data

Source code: see [LICENSE](LICENSE). The Constitution of India and government portal details are
public information, but the **Gujarati and English article texts must be obtained from the
official source** and are not redistributed here. Owner-authored explanations in `data/seed/` are
the project owner's content and remain marked `requires_human_verification` until reviewed.

**Privacy:** complaints and uploaded documents are personal data. Access tokens are stored only as
SHA-256 hashes, the database and storage directory are owner-only (0600/0700), admins see complaint
metadata but never complaint text. Do not deploy publicly without reading
[`docs/SECURITY_AUDIT.md`](docs/SECURITY_AUDIT.md) and
[`docs/DEPLOYMENT_GUIDE.md`](docs/DEPLOYMENT_GUIDE.md).
