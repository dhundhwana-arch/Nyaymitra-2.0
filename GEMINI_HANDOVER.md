# GEMINI HANDOVER

**NYAYMITRA 2.0 — Complete handover brief for a successor AI**

**Created & Developed by Bambhaniya Divyesh Nonghanbhai**

**Handover commit:** `342103eca3e209e10bd705a2ac5c48225c9afe13`
**Branch:** `arena/2497125a-nyaymitra-2-0` (PR #2, open, not merged)
**Repository:** `https://github.com/dhundhwana-arch/Nyaymitra-2.0`

---

## 0. Read this first

You are taking over a **working, tested engineering prototype** whose legal corpus is nearly empty and which is **not deployed**. That is the whole situation in one sentence.

The project's defining discipline is **honesty about its own limits**. Every prior agent that added a false claim made the project worse. Your most valuable instinct here is to check before you assert.

**Three rules that are not negotiable:**

1. **Never claim the Constitution is loaded, verified, or that output is legal advice.** It is 9 explanations, 0 official texts, 0 human-verified.
2. **Never deploy or merge to `main`** without the owner's explicit approval.
3. **Never overwrite or delete existing work to "clean up."** Five audit reports are already permanently lost (§9). Do not add to that count.

---

## 1. Project vision and requirements

**Vision:** a citizen of India, with no lawyer and limited literacy, describes a problem in their own language and is guided to the right constitutional provision, the right department, and the right free legal-aid channel — without being misled by a machine that pretends to be a lawyer.

**Hard requirements that shaped the architecture:**

| # | Requirement | How the code honours it |
|---|---|---|
| R1 | Never invent law | Retrieval-before-generation; refuse when nothing retrieved |
| R2 | Every claim traceable | Citations validated against the retrieved set only |
| R3 | Never present unverified text as official | DB `CHECK` default `requires_human_verification`; ingestion never writes `verified` |
| R4 | No outcome promises | Guard rejects guilt/outcome/impersonation language |
| R5 | Citizen privacy | Hashed IPs, one-time tokens, redacted audit log, retention purge, no API caching |
| R6 | Work offline / low bandwidth | Offline deterministic provider; PWA app shell; no CDN |
| R7 | Multilingual, honestly | 23 languages with **per-language status**, never collapsed into one claim |
| R8 | Reversible everything | 6 up/down migrations; importer journalled with `rollback` |

---

## 2. Actual architecture

```
Browser (web/ — vanilla JS SPA, no framework, CSP default-src 'self')
   │
   ├── Pages/static host ── _headers, _redirects (self-only CSP)
   │
   └── /api/v1/*  ─────────────────────────────┐
                                               │
                        FastAPI (backend/app/main.py)
                        ├── middleware.py   CSP, headers, request IDs
                        ├── security.py     token hashing, compare_digest
                        ├── routers/  (10)  41 operations
                        ├── services/ (16)  domain logic
                        └── ai/
                             ├── retrieval (FTS5, bm25, max 4 rows)
                             ├── offline.py       deterministic, default
                             ├── openai_compatible.py  optional, untested
                             └── guard.py         outcome-language filter
                                               │
                                     SQLite + FTS5
                                     22 tables, 30 indexes
                                     6 reversible migrations
```

**Request path for an AI answer (the safety core):**

1. Validate and normalise the question.
2. Detect prompt injection (log it, but still answer safely).
3. **Retrieve** candidate articles via FTS5 `bm25` — cap 4.
4. If **nothing** retrieved → refuse with "I do not have verified information." **No generation happens.**
5. Generate (offline template, or live provider if configured).
6. **Validate every citation** against the retrieved set — reject any citation not in it.
7. Run the outcome/guilt language guard.
8. Label provenance: `[સમજૂતી — સત્તાવાર લખાણ નથી]` ("explanation — not the official text").

**This ordering is the product.** Do not refactor it into generate-then-check.

---

## 3. Existing file locations

```
/
├── MASTER_PROJECT_CONTEXT.md        ← 12-section source of truth. READ THIS SECOND.
├── PROJECT_FINAL_STATUS.md          ← final status assessment
├── COMPLETED_WORK_INVENTORY.md      ← evidence-backed inventory
├── GEMINI_HANDOVER.md              ← this file
├── README.md                       ← user-facing overview (accurate)
├── docs/INDEX.md                   ← map of all documentation
├── docs/                           ← 32 docs, 5,458 lines
│   ├── ARCHITECTURE.md  API_DOCUMENTATION.md  DATABASE_SCHEMA.md
│   ├── FEATURE_STATUS.md  KNOWN_LIMITATIONS.md  TESTING_REPORT.md
│   ├── RELEASE_READINESS_CHECKLIST.md  REMAINING_BLOCKERS.md
│   ├── audits/ ip/ legal/ security/
├── backend/
│   ├── app/        48 files, 8,209 lines
│   │   ├── main.py  config.py  middleware.py  security.py  metrics.py  languages.py
│   │   ├── routers/    10 files
│   │   ├── services/   16 files
│   │   └── ai/         offline, openai_compatible, retrieval, guard
│   ├── migrations/ 001…006 (.sql + .down.sql)
│   └── tests/      22 files, 4,643 lines, 460 tests
├── web/            45 files — index.html, app.js (1,636 lines), admin.html, locales/ (23), assets/
├── frontend/legacy/  6 files, 5.2 MB — SUPERSEDED prototype, do not extend
├── data/
│   ├── seed/       constitution(9) sources(15) departments(11) triage(5) glossary(18)
│   └── legacy/     constitution_articles_legacy_2026-11-07.jsonl.gz (2,125 rows)
├── scripts/        18 tools — init_db, check_db, backup_db, purge_data, import_*, inventory_*
├── tests/          15 source-tool tests
├── android/        53 files — Capacitor, never built
├── deploy/  Dockerfile  render.yaml  wrangler.toml  .github/workflows/ci.yml
└── GOVERNMENT_SUBMISSION_PACKAGE/  10 PDFs + EVIDENCE_MATRIX.md + sources/
```

---

## 4. Existing APIs (41 operations)

Base: `/api/v1`

| Area | Endpoints |
|---|---|
| System | `health` · `ready` · `meta` |
| Constitution | `articles` · `parts` · `coverage` · `articles/{id}` · `articles/{id}/text` |
| Discovery | `departments` · `library` · `languages` · `languages/detect` |
| AI | `ai/explain` · `ai/terminology` · `ai/glossary` |
| Complaints | `complaints` · `complaints/preview` · `complaints/{reference}` |
| Documents | `documents` · `documents/{id}` · `documents/{id}/content` |
| Feedback | `feedback` |
| Admin (token) | `stats` · `metrics` · `queries` · `answers` · `errors` · `audit` · `complaints` · `documents` · `sources` · `verification-queue` · `ai/health` · `ai/usage` · `review-packet` · `legacy-chunks` · `backup` · `articles/{id}/verification` (PATCH) |

**Traps:** `/api/docs` is **404 by design** (Swagger's CDN assets violate the CSP) — use `/api/openapi.json`. `GET /health` is 404 — use `/api/v1/health`.

---

## 5. Database structure (22 tables)

**Core:** `constitution_articles` · `article_texts` · `article_sources` · `legal_sources` · `departments` · `triage_guides`
**Interaction:** `complaints` · `documents` · `feedback` · `query_logs` · `ai_answers`
**Governance:** `audit_log` · `error_log` · `schema_migrations`
**Ingestion:** `ingest_runs` · `import_changes` · `legacy_import_chunks`

**Critical invariants — break these and you break the product:**

```sql
-- article_texts.verification_status
CHECK (verification_status IN ('official_text','requires_human_verification','human_verified'))
DEFAULT 'requires_human_verification'
```

* `legacy_import_chunks` (2,125 rows) is **quarantined** — admin-only, never on a public endpoint.
* Migrations must stay reversible: every `NNN_*.sql` needs `NNN_*.down.sql`.
* **Never set `verification_status='verified'`** without a named human reviewer.

---

## 6. Test commands and actual results

```bash
# Setup
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
.venv/bin/pip install -r requirements-ingestion.txt   # needed for tests/

# Run
.venv/bin/python -m pytest backend/tests -o addopts=""   # 460 passed
.venv/bin/python -m pytest tests -o addopts=""           #  15 passed
.venv/bin/python -m pytest backend/tests -o addopts="" --cov=backend/app   # 92%

# Frontend (needs: pip install --no-save jsdom)
node scripts/e2e_activation.mjs <frontend-url> [backend-url]   # 43 checks
node scripts/smoke_web.mjs <url>
```

**Executed in this handover session (2026-11-12):**

| Suite | Result |
|---|---|
| `backend/tests` | **460 passed** |
| `tests` | **15 passed** |
| **Total** | **475 passed**, 0 failed |
| Coverage | **92 %** (3,932 stmts, 328 missed) |
| `scripts/init_db.py` | 22 tables, 30 indexes, seeds OK |
| `scripts/check_db.py` | `RESULT: OK` |

**Not executed here (historical results only):** jsdom E2E 43/43, smoke test, real-device, accessibility, load, live LLM, Android build.

**Three test traps that will waste your time if unread:**
1. `pytest.ini` sets `addopts = -q`; a second `-q` **hides the summary**. Always `-o addopts=""`.
2. Without `pymupdf`, one test **skips silently** — you'll see 459+1 instead of 460.
3. E2E and smoke share the same per-IP rate-limit bucket (read 120, admin 10 per 60 s). **Run E2E first** or restart the server.

---

## 7. Known bugs and blockers

| # | Issue | Severity | Fix |
|---|---|---|---|
| B1 | **No authoritative Constitution text** — 0 of 9 articles | **BLOCKER** | owner supplies official PDFs; use Phase 4 importer |
| B2 | **0 human-verified** content | **BLOCKER** | named reviewer signs off via `/admin` queue |
| B3 | No real-device / AT test ever | High | run on an actual phone + screen reader |
| B4 | Live LLM never exercised | Medium | needs API key + evaluation |
| B5 | 21 locales at 5–10 %, machine-translated | Medium | translate + native review |
| B6 | Rate limits tighter than E2E assumes | Low | documented; run E2E first |
| B7 | Voice I/O untested | Low | **do not demo** |
| B8 | No backup rotation | Low | operator cron |
| B9 | Shared operator tokens, no MFA | Medium (residual risk R-7) | per-user accounts |
| B10 | APK never built | Low | `npm run cap:build` |
| B11 | GitHub repo description says *"Gemini Production Engine"* — **false** | Embarrassing | owner must fix; automation gets 403 |

---

## 8. Incomplete modules

`IBNT`: live LLM provider · PWA on device · voice I/O · Android APK.
`PARTIAL`: locale coverage (21 languages).
`BLOCKED`: legal corpus · human verification.
`NEVER STARTED`: per-user accounts + MFA · load testing · accessibility audit · live deployment.

---

## 9. Important technical decisions — and what is unrecoverable

| Decision | Why |
|---|---|
| Canonical = `arena/08f8f3c5` lineage | Most complete implementation (312 files), chosen on 10 documented criteria |
| Nothing rewritten, nothing force-pushed | `main` is an ancestor; promotion is a fast-forward |
| Santali corpus **quarantined, not fixed** | 2,125 rows are regex fragments of a PDF, not articles. Needs diglot/OCR. **Do not "repair"** |
| Swagger disabled | CDN assets violate the self-only CSP |
| Offline provider is the default | Deterministic; structurally cannot invent a provision |
| `pymupdf` (AGPL-3.0) kept out of runtime | Ingestion only; the shipped image contains no AGPL code |
| 23 languages with distinct statuses | Prevents "supports 23 languages" becoming a false claim |
| Phase 4 / 4A as separate commits | Preserves provenance and allows independent revert |

**Permanently lost — five audit reports from an earlier conversation whose workspace was unreachable:**

`COMPLETE_PROJECT_FORENSIC_AUDIT.md` · `NYAYMITRA_RECONCILIATION_REPORT.md` · `PR2_FINAL_RELEASE_REVIEW.md` · `NYAYMITRA_POST_REVIEW_INTEGRATION.md` · `NYAYMITRA_PHASE4A_INTEGRATION.md`

**Their findings survive** in `docs/CANONICAL_BUILD_AND_BRANCH_RECONCILIATION.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/RELEASE_READINESS_CHECKLIST.md` and `MASTER_PROJECT_CONTEXT.md` §11. The documents do not. **Do not fabricate replacements.**

---

## 10. Exact next tasks, in priority order

| # | Task | Owner or Gemini | Detail |
|---|---|---|---|
| 1 | **Merge PR #2** | **owner** | `git push origin 342103e:main` is a pure fast-forward — but needs approval; PR has 0 reviews |
| 2 | **Fix repo description** | **owner** | currently false; `gh repo edit` → 403 for automation |
| 3 | **Supply Constitution PDFs (EN + GU)** | **owner** | unblocks B1; then `.venv/bin/python scripts/import_constitution_data.py --help` |
| 4 | **Name a human reviewer** | **owner** | unblocks B2; review via `/admin` verification queue |
| 5 | **Deploy** | owner + Gemini | Cloudflare Pages (`wrangler.toml`) + backend host; config already exists |
| 6 | Re-run E2E + smoke | Gemini | `node scripts/e2e_activation.mjs …` before any demo |
| 7 | Real-device + AT test | Gemini | closes B3 |
| 8 | Translate remaining 21 locales | Gemini + native speakers | closes B5 |
| 9 | Build APK | Gemini | `npm run cap:build` |
| 10 | Per-user accounts + MFA | Gemini | closes B9 |

---

## 11. Things you must NOT rebuild

These exist, work, and are tested. Rebuilding them destroys value and breaks tests.

* **Do not rewrite the migration system.** 6 reversible migrations, verified round-trip.
* **Do not replace FTS5 retrieval with a vector store.** It works, it's tested, it's dependency-free.
* **Do not re-implement the safety pipeline** (retrieve → refuse → generate → cite-validate → guard). It is the product's core asset.
* **Do not "fix" the Santali corpus.** It is deliberately quarantined.
* **Do not re-enable Swagger** at `/api/docs`.
* **Do not add a CDN or external font.** The CSP forbids it and E2E enforces it.
* **Do not cache API responses in the service worker.** They may contain personal data.
* **Do not restructure `frontend/legacy/`.** It is a historical artefact, not a codebase.
* **Do not re-do the documentation set.** 32 docs + 5 root documents exist and are accurate.
* **Do not delete `main`.** It is the ancestor that makes PR #2 a fast-forward.

---

## 12. How to verify you have the right code

```bash
git fetch origin
git rev-parse origin/arena/2497125a-nyaymitra-2-0
# expect: 342103eca3e209e10bd705a2ac5c48225c9afe13

git rev-list --count origin/main..origin/arena/2497125a-nyaymitra-2-0   # 61
git rev-list --count origin/main                                        # main = 53df9ea
```

If `main` is still `53df9eabed4f4216490945e0f292c2b4ffacea55` and no deployment exists, **nothing has been merged or shipped** — which is the expected state.

---

## 13. Orientation in five minutes

1. Read `MASTER_PROJECT_CONTEXT.md` (§4 module inventory, §7 legal status).
2. Read `docs/FEATURE_STATUS.md` — 5-status vocabulary and evidence per feature.
3. Read `docs/RELEASE_READINESS_CHECKLIST.md` — what gates deployment.
4. Run the two test commands. If you see 460 + 15, the environment is sound.
5. Read `docs/KNOWN_LIMITATIONS.md` before promising anything to the owner.

**The fastest way to be useful here** is not to write code. It is to close B1 and B3 — the corpus and the real-device test. Everything else is already built.

---

**Created & Developed by Bambhaniya Divyesh Nonghanbhai**
