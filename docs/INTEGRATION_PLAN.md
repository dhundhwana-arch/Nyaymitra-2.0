# NYAYMITRA 2.0 — Architecture & Integration Plan

**Status:** approved plan executed on branch `arena/812d6894-nyaymitra-2-0`.
**Read first:** `docs/REPOSITORY_AUDIT.md`.

The plan below is ordered so that every phase leaves the repository in a runnable state. Phase numbers follow the
mission brief.

---

## 1. Target architecture

```
                         ┌──────────────────────────────────────────────┐
  Browser (mobile-first)  │  web/  vanilla HTML+CSS+JS, no CDN, gu/en    │
  same-origin, CSP-safe   │  home · assistant · complaint · library      │
                         │  documents · departments · admin             │
                         └───────────────┬──────────────────────────────┘
                                         │ fetch('/api/v1/...')
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FastAPI app  (backend/app)                                                  │
│                                                                             │
│  middleware: request-id · security headers · rate limit · body-size limit    │
│              · redacting structured logger · safe error envelope             │
│                                                                             │
│  routers/                                                                   │
│    meta        GET /api/v1/meta            capabilities, disclaimers, i18n   │
│    health      GET /api/v1/health, /ready  service + db + provider probe     │
│    constitution GET /api/v1/constitution/articles?q=&part=&page=            │
│                 GET /api/v1/constitution/articles/{id}                      │
│                 GET /api/v1/constitution/parts  /coverage                   │
│    ai         POST /api/v1/ai/explain       grounded explain + citations    │
│               POST /api/v1/ai/terminology   plain-language glossary lookup  │
│    complaints POST /api/v1/complaints       create (validated + confirmed)  │
│               GET  /api/v1/complaints/{ref}?token=  retrieve own draft      │
│    documents  POST /api/v1/documents        upload (type/size validated)     │
│               GET  /api/v1/documents/{id}   own doc, token-gated             │
│    departments GET /api/v1/departments?category=&state=                     │
│    admin      GET  /api/v1/admin/stats, /admin/queries, /admin/errors,      │
│               GET  /admin/sources, PATCH /admin/articles/{id}/verification  │
│                    (X-Admin-Token, RBAC admin/monitor)                      │
│    feedback   POST /api/v1/feedback         report wrong/unsafe answer      │
│                                                                             │
│  services/  constitution · complaints · documents · departments · triage    │
│  ai/        provider registry · router · rag (retrieval+citation check)     │
│             · guard (prompt injection) · eval (hallucination harness)       │
│  db         sqlite3 (WAL, FK on) · migrations/*.sql · repository helpers     │
└───────────────────────────┬─────────────────────────────────────────────────┘
                            │
                  ┌─────────▼──────────┐         ┌────────────────────────────┐
                  │ SQLite (WAL)       │         │ storage/documents (private)│
                  │ legal_sources      │         │ random filenames, no       │
                  │ constitution_...   │         │ directory traversal,       │
                  │ departments        │         │ size/type allow-list       │
                  │ complaints         │         └────────────────────────────┘
                  │ documents          │
                  │ query_logs         │
                  │ audit_log          │
                  │ legacy_import_*    │  ← quarantined, never served
                  └────────────────────┘
```

### Design rules applied throughout

1. **Verified ≠ generated.** Every legal row carries `verification_status`, `source_id`, `source_locator`,
   `last_checked_at`. The UI renders the badge. Generated prose is always labelled *AI explanation*.
2. **No provider, no guess.** `AIProvider` protocol with `UnavailableProvider` default. If no key is configured or
   the provider errors, the API returns `503 provider_unavailable` and the UI shows an explicit message.
3. **Retrieval-gated answering.** The prompt is built only from retrieved verified rows; a post-processing
   citation validator strips/rejects any article number that was not in the retrieval set.
4. **Never invent missing text.** If an article has no verified text, the API returns
   `text_status: "not_available"` and the UI says so; the ingestion pipeline reports missing numbers instead of
   filling them.
5. **Same-origin + no CDN.** Frontend is served by FastAPI; no third-party scripts; works offline on a LAN.
6. **Preserve, then supersede.** Legacy data is exported with provenance to `data/legacy/`; legacy frontend files
   are kept under `frontend/` with a `LEGACY_NOTES.md`, no longer served.

---

## 2. Phase plan and outcomes

| Phase | Work | Deliverable / exit criterion |
|---|---|---|
| 1 | Repository audit | `docs/REPOSITORY_AUDIT.md` (done, commit `38d6fe6`) |
| 2 | Architecture + integration plan | this document + `docs/INTEGRATION_PLAN.md` |
| 3 | Backup + branch | working branch `arena/812d6894-nyaymitra-2-0`; legacy DB and all legacy assets exported to `data/legacy/` with checksums before any file is removed |
| 4 | Backend + database | `backend/app/**`, `backend/migrations/*.sql`, migrations applied idempotently, `scripts/init_db.py`, `scripts/backup_db.py`, forward/rollback documented in `docs/DATABASE_SCHEMA.md` |
| 5 | Frontend | `web/**` mobile-first accessible UI, gu/en, loading/error/empty states, no CDN, served by FastAPI with CSP |
| 6 | Constitution & legal knowledge | curated `constitution_articles` seed (owner-authored, clearly labelled), FTS5 search, parts/coverage endpoints, ingestion pipeline with duplicate/missing/OCR-confidence validation |
| 7 | AI + RAG | provider abstraction (`offline`, `openai_compatible`), retrieval, citation validation, prompt-injection guard, hallucination eval harness, `503` when unavailable |
| 8 | Voice & accessibility | Web Speech API with feature detection, full text alternative, explicit confirmation before submitting a transcribed complaint, skip-links, labels, aria-live, focus states |
| 9 | Security | rate limiting, body limits, upload allow-list + magic-byte check, admin token RBAC, audit log, PII redaction in logs, security headers/CSP, safe error envelope, `docs/SECURITY_AUDIT.md` |
| 10 | Testing | pytest suite (unit/integration/E2E via TestClient) + JS syntax/DOM checks + coverage script; `docs/TESTING_REPORT.md` with real outputs |
| 11 | Documentation | the 12 required documents, all reflecting the real implementation |
| 12 | Final audit + PR | `docs/KNOWN_LIMITATIONS.md`, PR with summary, test evidence, migration instructions, known limitations |

---

## 3. Data strategy

```
data/raw/                        owner-supplied official PDFs/text (git-ignored)
data/seed/                       curated, human-authored seed JSON (committed)
data/legacy/                     quarantined legacy exports + provenance (committed)
storage/documents/               private uploaded files (git-ignored)
```

* The **2 125 legacy rows** are exported to `data/legacy/constitution_articles_legacy_2026-11-07.jsonl.gz`
  together with a checksum, a count, and the audit findings. The `constitution_articles` table is then rebuilt with
  a new schema; legacy text lives on in `legacy_import_chunks` (searchable only by admin) and in the archive.
* **Seed content** is limited to what the repository's own author wrote (Articles 14/19/21/21A/22/32/39A + Preamble,
  plus the two criminal-law entries and their Gujarati paraphrases) and to the triage knowledge already in the repo.
  Each record ships with `verification_status: "requires_human_verification"`, a `source_url` pointing at the
  official publisher, `source_locator`, and `last_checked_at: null` (never checked from this environment).
* **Nothing is invented to fill gaps.** Missing articles are reported by `/constitution/coverage` and by the
  ingestion report.

## 4. Rollback strategy

* `scripts/init_db.py --migrate` records every applied migration in `schema_migrations` (id, checksum, applied_at).
* Each migration file has a paired `NNN_*.down.sql` where a down-migration is safe; the runner supports
  `--rollback-to N`.
* `scripts/backup_db.py` performs `sqlite3 .backup` to `backups/nyaymitra-<timestamp>.db` **before** a migration
  when `--backup` is passed; restore documented in `docs/DEPLOYMENT_GUIDE.md`.
* No destructive step is taken without the backup existing (verified in tests).

## 5. Explicit non-goals

* No final legal decision-making, no guilt/innocence statements, no outcome predictions.
* No auto-filing of complaints to government portals (no integration credentials exist, and doing so without the
  owner's legal review would be irresponsible).
* No storage of real citizen data in this public repository.
* No claim of complete legal verification. Human expert sign-off is required
  (`docs/LEGAL_VERIFICATION_CHECKLIST.md`).

---

## 6. Execution addendum (branch `arena/812d6894-nyaymitra-2-0`)

Phases 1–12 of the table are implemented. Outcome against the plan's own phases:

| Phase | Delivered | Status |
|---|---|---|
| 1. Audit | `docs/REPOSITORY_AUDIT.md` (+ §14/§15 addenda) | COMPLETE |
| 2. Archive and quarantine | `data/legacy/*.jsonl.gz` with sha256, `legacy_import_chunks`, `scripts/export_legacy.py` | COMPLETE AND TESTED |
| 3. Database | 15 tables, FTS5, migrations + down-migrations, backup/restore | COMPLETE AND TESTED |
| 4. Backend core | `create_app`, middleware, error envelope, health/ready/meta | COMPLETE AND TESTED |
| 5. Legal data API | search, article detail, parts, coverage, provenance | COMPLETE AND TESTED |
| 6. AI/RAG | provider abstraction, retrieval-first, citation validation, guard, offline composer | COMPLETE AND TESTED (live provider untested) |
| 7. Citizen workflows | complaints (+preview, token access), documents, departments, feedback, glossary | COMPLETE AND TESTED |
| 8. Admin | roles, stats, queues, audit, backups, document index, legacy quarantine | COMPLETE AND TESTED |
| 9. Frontend | `web/` six routes, gu/en, accessible forms, admin console, PWA manifest | IMPLEMENTED AND TESTED IN JSDOM (no real device yet) |
| 10. Security | token hashing, rate limits, upload validation, CSP, permissions, redaction | COMPLETE AND TESTED |
| 11. Testing | 187 pytest tests, 92% coverage, jsdom journeys, CI workflow (pytest ×2, pip-audit, frontend), changeset integrity checker | COMPLETE |
| 12. Documentation | 12 documents in `docs/` + README | COMPLETE except legal sign-off, which is human work |

### Design rules — compliance

1. **Retrieval before generation** — `services/constitution.retrieve_for_ai` runs first; no rows and
   no triage match produces an explicit "insufficient sources" answer.
2. **No unsupported legal claims** — model output is validated against the retrieved set; failures
   fall back and are flagged `degraded`.
3. **Unverified is visible** — every citation and article carries `verification_status` and
   `text_status`; `/meta` reports `verified_text: 0`.
4. **Never invent text** — `text_en`/`text_gu` stay `NULL` until an official document is ingested;
   the importer reports missing numbers rather than synthesising them.
5. **No verdicts** — guard patterns in English and Gujarati reject guilt/outcome/impersonation.
6. **Nothing is deleted** — legacy rows live in a gzip archive and a quarantined table, reachable
   only through the admin endpoint that labels them as unusable.

### Deviations from the plan

* **Swagger UI disabled.** `/api/docs` would have loaded assets from a CDN, which the CSP blocks and
  an offline deployment cannot reach. The schema stays at `/api/openapi.json`; the reference is
  `docs/API_DOCUMENTATION.md`.
* **Stricter admin rate-limit bucket added** (not in the original plan) after the audit showed the
  admin token shared the public read limit.
* **Chunked request bodies refused** rather than streamed, because their size cannot be verified
  before buffering.
* **`--workers 1` is a deployment requirement**, documented in `docs/DEPLOYMENT_GUIDE.md`, because
  rate limiting is in-process and SQLite writes are serialised.
