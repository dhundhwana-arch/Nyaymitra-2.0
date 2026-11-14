# NYAYMITRA 2.0

**Inclusive justice-access and legal-navigation platform.** It helps a citizen describe a problem
in Gujarati or English (interface selectable in 23 Indian languages — see the language table below), find the constitutional provision that applies, understand the official
next step, prepare a complaint draft, and reach the right department or free-legal-aid channel.

It is **not** a lawyer, a court or a judge. It does not decide cases, predict outcomes or
guarantee results, and it never presents unverified material as official law.

**Created & Developed by Bambhaniya Divyesh Nonghanbhai**

> **Where the current work is:** branch `arena/2497125a-nyaymitra-2-0`, proposed to `main` as
> **PR #2**. It contains the full rebuild (both earlier rebuild branches merged in), the
> data-activation work, and the Phase 4 Constitution importer. `main` still holds the original
> 4 November prototype; **nothing has been merged into it and nothing is deployed.** See
> [`docs/REPOSITORY_AND_PRODUCTION_READINESS.md`](docs/REPOSITORY_AND_PRODUCTION_READINESS.md).

---

## Current status (be precise before you rely on it)

| Area | Status |
|---|---|
| Backend API (41 operations in the OpenAPI schema), database, 5 migrations, seeds | **COMPLETE AND TESTED** |
| Retrieval-before-generation, citation validation, offline grounded answers | **COMPLETE AND TESTED** |
| Complaint intake with deterministic summary, review gate, one-time token | **COMPLETE AND TESTED** |
| Document upload (PDF/image), extraction status, owner-token download | **COMPLETE AND TESTED** |
| Citizen web app (8 routes, gu/en) and admin console | **IMPLEMENTED AND TESTED IN JSDOM** — no real phone/browser session yet |
| Legal Library (`#/legal`, `GET /api/v1/library`): all 43 stored items, search, category and language filters | **COMPLETE AND TESTED** |
| Frontend and backend as separate websites (configurable API address + CORS allowlist) | **COMPLETE AND TESTED LOCALLY** — not verified on the live sites |
| Multilingual architecture: registry of 23 languages, per-language article text with provenance, fallback labelling, RTL | **COMPLETE AND TESTED** (jsdom; no real-device rendering test) |
| Interface text in languages other than Gujarati/English | **MACHINE-TRANSLATED, UNREVIEWED** — essential labels in 17 languages, partial in 4 |
| Legal content in languages other than Gujarati/English | **NONE** — shown in English with a notice; nothing is machine-translated |
| Live deployment | **NOT UPDATED** — nothing from this branch has been deployed |
| Voice input / speech output | **IMPLEMENTED BUT NOT TESTED** (browser APIs) |
| Live LLM provider (`openai_compatible`) | **IMPLEMENTED BUT NOT TESTED** (no API key available) |
| Complaint duplicate-submission protection | **COMPLETE AND TESTED** (idempotency key + fingerprint window) |
| Data-retention purge of complaints/documents | **COMPLETE AND TESTED** (`scripts/purge_data.py`, dry-run default) |
| Dependency vulnerability audit | **COMPLETE** — `pip-audit` clean after upgrading 3 packages |
| Authoritative Article text in Gujarati/English | **BLOCKED** — no source file or extraction exists in the repository; the owner's local files have not been supplied (see [`docs/LOCAL_DATA_RECOVERY_AND_IMPORT_PLAN.md`](docs/LOCAL_DATA_RECOVERY_AND_IMPORT_PLAN.md)) |
| Legal accuracy of every explanation, helpline and department entry | **REQUIRES HUMAN VERIFICATION** (queue in `/admin`) |
| Automated test suite | **443 backend tests + 15 source-tool tests, all passing**; 43-step jsdom end-to-end script passing in both hosting layouts |

The corpus ships with **9 human-written article explanations and 0 authoritative texts**. The API
says so on every answer, and the UI shows a warning banner. See
[`docs/LEGAL_VERIFICATION_CHECKLIST.md`](docs/LEGAL_VERIFICATION_CHECKLIST.md).

---

## Architecture (as it actually is)

```
Browser ── web/ (static single-page app, no build step, no CDN)
   │          web/config.js  → apiBase: "" (same site)  or  "https://<backend>" (separate site)
   ▼
FastAPI  backend/app  ── /api/v1/…   (CORS only for NYAYMITRA_ALLOWED_ORIGINS)
   │   constitution · library · ai (assistant) · departments · complaints · documents · admin
   ▼
SQLite   NYAYMITRA_DB_PATH   schema = backend/migrations/001–006
   ▲
data/seed/*.json  (loaded idempotently at start-up)      data/raw/*.pdf → scripts/ingest_constitution.py
```

Two supported hosting layouts: **one site** (the backend serves `web/` itself — the default) or
**two sites** (static host for `web/` + API host). For two sites run
`python scripts/configure_frontend.py --api-base https://<backend>` and set
`NYAYMITRA_ALLOWED_ORIGINS=https://<frontend>` on the backend.

What a visitor can use today: Home, Assistant, Complaint, Constitution (4 Parts, 9 articles),
Legal Library (43 items), Offices (11), Glossary (18), About. Every Constitution entry is an
owner-written explanation marked `requires_human_verification`; **0 articles have official text**.

---

## Languages

23 languages can be selected: Assamese, Bengali, Bodo, Dogri, Gujarati, Hindi, Kannada, Kashmiri,
Konkani, Maithili, Malayalam, Manipuri, Marathi, Nepali, Odia, Punjabi, Sanskrit, Santali, Sindhi,
Tamil, Telugu, Urdu and English. Urdu, Sindhi and Kashmiri are laid out right-to-left.

| What | Gujarati, English | 17 languages | Bodo, Dogri, Manipuri, Santali |
|---|---|---|---|
| Interface | complete, project-authored | essential labels, **machine-translated, not reviewed** | a few labels, rest in English |
| Explanations of 9 articles | yes (owner-written, not official text) | shown in English, with a notice | shown in English, with a notice |
| Official Constitution text | **0 articles** | **0 articles** | **0 articles** |
| Human-verified content | none | none | none |
| Assistant | answers in the language | understands the script and article number, answers in English and says so | same |

Interface translation, machine translation, official text and verified text are four separate
states and are labelled separately everywhere. The Constitution is never machine-translated.
Live table: `GET /api/v1/languages`, the About page, or
[`docs/LANGUAGE_AVAILABILITY_MATRIX.md`](docs/LANGUAGE_AVAILABILITY_MATRIX.md).

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
  routers/            health, constitution, library, ai, complaints, documents, departments, feedback, admin
  services/           constitution search, textsearch, complaints, documents, departments,
                      triage, glossary, seeding, ingestion, monitoring
backend/migrations/   versioned SQL with down-migrations
backend/tests/        443 pytest tests
web/                  self-hosted SPA (no CDN) + admin console; config.js sets the API address
web/locales/          interface text: one JSON catalogue per language + index.json (registry)
data/seed/            curated seed JSON (sources, 9 articles, departments, triage, glossary)
data/legacy/          quarantined 2,125 legacy rows (gzip + sha256), never served to citizens
data/raw/             where the owner puts official Constitution PDFs (git-ignored)
scripts/              init_db, backup_db, purge_data, ingest_constitution,
                      constitution_coverage, verify_changeset, verify_ai_provider,
                      export_legacy, smoke_web, e2e_activation, configure_frontend,
                      inventory_local_data, build_locales, language_matrix
ingestion/            official-PDF download + text-quality checks (never writes to a database)
docs/                 audit, architecture, API, schema, testing, security, legal, deployment
```

Needless to say, the old `backend/database.py`, `frontend/library_fix.js` and other broken
prototype files are archived under `frontend/legacy/` and `scripts/legacy/` with notes; they are
not served.

---

## Tests

```bash
python -m pytest                                  # 443 passed
python -m pytest tests                            # 15 passed (ingestion/ source-quality tool)
python -m pytest -q --cov=backend/app             # coverage report
node --check web/app.js web/admin.js              # frontend syntax
node scripts/smoke_web.mjs http://127.0.0.1:8000  # optional jsdom journeys (needs jsdom)
node scripts/e2e_activation.mjs <frontend-url> [<backend-url>]      # 43 end-to-end checks incl. all 23 languages (needs jsdom)
pip-audit --vulnerability-service pypi -r backend/requirements.txt   # dependency audit
python scripts/constitution_coverage.py           # what the corpus really contains
python scripts/purge_data.py                      # what retention would delete (dry run)
python scripts/verify_ai_provider.py              # is a real model actually answering? (exit 3 = no)
python scripts/verify_changeset.py --verify backups/<manifest>.json   # is this the tested copy?
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
| [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) | Local, server, backups, retention, metrics, upgrades, rollback |
| [HANDOVER.md](docs/HANDOVER.md) | Where the work is, backup + integrity proof, real-model status, repo separation |
| [FINAL_COMPLETION_REPORT.md](docs/FINAL_COMPLETION_REPORT.md) | Task register, results, completion percentage |
| [NYAYMITRA_DATA_ACTIVATION_REPORT.md](docs/NYAYMITRA_DATA_ACTIVATION_REPORT.md) | Every dataset found, what is displayed, what is missing |
| [NYAYMITRA_FRONTEND_BACKEND_CONNECTION_REPORT.md](docs/NYAYMITRA_FRONTEND_BACKEND_CONNECTION_REPORT.md) | Why the live site was empty, what was fixed, test results |
| [PHASE4_DATA_IMPORT_REPORT.md](docs/PHASE4_DATA_IMPORT_REPORT.md) | Importing the owner's English/Gujarati article files: formats, quality report, diglot and OCR status, Termux transfer |
| [LOCALE_QUALITY_AUDIT.md](docs/LOCALE_QUALITY_AUDIT.md) | Generated audit of the 23 interface catalogues |
| [MULTILINGUAL_IMPLEMENTATION_REPORT.md](docs/MULTILINGUAL_IMPLEMENTATION_REPORT.md) | The 23-language architecture, database/API/frontend changes, tests, limits |
| [LANGUAGE_AVAILABILITY_MATRIX.md](docs/LANGUAGE_AVAILABILITY_MATRIX.md) | What really exists in each language (generated) |
| [DATA_SOURCE_REGISTER.md](docs/DATA_SOURCE_REGISTER.md) | Official sources located, with provenance and what is still unknown |
| [LOCAL_DATA_RECOVERY_AND_IMPORT_PLAN.md](docs/LOCAL_DATA_RECOVERY_AND_IMPORT_PLAN.md) | Search for the owner's local Constitution files, and the import plan |
| [REPOSITORY_AND_PRODUCTION_READINESS.md](docs/REPOSITORY_AND_PRODUCTION_READINESS.md) | Branch state and the deployment checklist |
| [REMAINING_BLOCKERS.md](docs/REMAINING_BLOCKERS.md) | The three external blockers and who owns them |
| [RELEASE_READINESS_CHECKLIST.md](docs/RELEASE_READINESS_CHECKLIST.md) | Gate-by-gate release decision |
| [REPOSITORY_IDENTITY.md](docs/REPOSITORY_IDENTITY.md) | Corrected repository description (owner action) |

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
