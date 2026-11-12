# Architecture — NYAYMITRA 2.0

## 1. Shape of the system

```
                     ┌──────────────────────────── browser ───────────────────────────┐
                     │  web/index.html + app.js   (citizen, gu/en, 6 hash routes)     │
                     │  web/admin.html + admin.js (operator console, token in tab)    │
                     │  no CDN, no inline script/style, CSP self-only                 │
                     └───────────────┬────────────────────────────────────────────────┘
                                     │ JSON over /api/v1 (same origin)
┌────────────────────────────────────▼───────────────────────────────────────────────────┐
│ FastAPI application  (backend/app/main.py → create_app)                                │
│                                                                                        │
│  middleware  RequestContext → SecurityHeaders → BodySizeLimit → RateLimit → ApiNotFound│
│  routers     health · constitution · ai · complaints · documents · departments ·       │
│              feedback · admin (+ static web mount)                                     │
│  deps        db_dependency (one SQLite connection per request) · require_role          │
│  errors      AppError → {error:{code,message,details,request_id}} · 422/404/500        │
└───────────────┬───────────────────────────────────────┬────────────────────────────────┘
                │                                       │
      ┌─────────▼──────────┐                 ┌──────────▼──────────────────────────────┐
      │ services/          │                 │ ai/                                     │
      │ constitution       │                 │ registry → offline | openai_compatible  │
      │ textsearch (gu/en) │                 │ rag (retrieve → prompt → validate)      │
      │ complaints         │                 │ guard (injection, unsafe-advice, cites) │
      │ documents          │                 │ offline (deterministic grounded answer) │
      │ departments        │                 └──────────┬──────────────────────────────┘
      │ triage, glossary   │                            │
      │ monitoring, seed   │                            │
      │ ingest             │                            │
      └─────────┬──────────┘                            │
                │                                       │
      ┌─────────▼───────────────────────────────────────▼──────────────────────────────┐
      │ SQLite (WAL, foreign keys, FTS5)  +  filesystem storage (owner-only 0700/0600)  │
      │ 15 tables, versioned migrations in backend/migrations/                          │
      └────────────────────────────────────────────────────────────────────────────────┘
```

Single process, no external services, no network egress required. That is a deliberate constraint:
the target user may be on a 2G connection in a district court queue.

## 2. Request lifecycle

1. **Rate limit** by client IP and bucket (`read` / `write` / `ai` / `admin`); `/health` exempt.
2. **Body size**: declared `Content-Length` checked against the limit; chunked bodies are refused
   on mutating methods because their size cannot be verified before buffering.
3. **Security headers** including a self-only CSP (`script-src 'self'`, `style-src 'self'`),
   `frame-ancestors 'none'`, `nosniff`, `no-referrer`, `Permissions-Policy`.
4. **Request id** (accepted from the client or generated) put in a contextvar, echoed in the
   response and written into every log line and error record.
5. Router → service → SQLite. One connection per request, `sqlite3.Row`, parameters only.
6. Errors become the same JSON envelope for 4xx and 5xx; internal exception text is logged but
   never returned.

## 3. The AI path (the part that must not lie)

```
question ──► guard.scan_input        (prompt-injection patterns → warning, not silent)
         ──► constitution.retrieve   (FTS5 AND-first, stopwords, overlap threshold, bm25)
             triage.match            (category / keyword → guide + department)
         ──► if no article and no guide: deterministic "insufficient sources" answer, grounded=false
         ──► provider.generate       (offline composer OR live LLM with fenced sources)
         ──► guard.validate_answer   (fabricated article numbers, guilt/outcome/impersonation)
         ──► on failure: offline grounded answer, degraded=true, warning code
         ──► monitoring: query (redacted) + hash, answer, citations, latency, status
```

Design rules enforced in code:

* **Retrieval before generation.** No source rows → no legal claim. The provider never invents a
  provision because it is only given retrieved rows.
* **Citations are validated.** Any `Article N` produced by a model that is not in the retrieved set
  causes rejection and fallback.
* **Unverified stays visible.** Every citation carries `verification_status` and `text_status`; the
  offline composer appends a line when the authoritative text is missing.
* **No verdicts.** `guilt_determination`, `outcome_guarantee` and `impersonation` patterns are
  rejected, in English and Gujarati.
* **Degrade, don't fail** (`offline_grounded`, default) or fail closed (`strict` → HTTP 503 with no
  answer). Both are tested.

Retrieval quality is a real design problem for Gujarati, not a stopword afterthought: FTS5's
default tokenizer splits Gujarati on whitespace, so common particles (`છે`, `માંથી`) matched almost
every row. `services/textsearch.py` supplies Gujarati/Hindi/English stopwords, an AND-first query
with OR fallback, and an overlap threshold; unrelated questions now return **no** articles instead
of a plausible-looking citation.

## 4. Data model in one paragraph

`legal_sources` is the provenance spine: every article, department and triage guide points at a
source row (URL, publisher, retrieval date). `constitution_articles` separates **text** (`text_en`,
`text_gu`, `text_status`) from **explanation** (`citizen_explanation_*`), so a summary can never be
mistaken for the article. `verification_status`, `checked_by` and `last_checked_at` record human
sign-off. `complaints` stores an access-token **hash** only; `documents` stores a random storage
name, a SHA-256 digest and an extraction status. `query_logs`, `ai_answers`, `error_log`,
`audit_log` and `ingest_runs` are the observability/audit trail. `legacy_import_chunks` holds the
quarantined legacy corpus for auditing only. Full detail: `docs/DATABASE_SCHEMA.md`.

## 5. Frontend

Hash routing (`#/home`, `#/assistant`, `#/complaint`, `#/library`, `#/departments`, `#/glossary`)
because it works behind any static path and needs no server rewrite rules. All dynamic text goes
through `textContent` or an `esc()` helper — no raw HTML interpolation of user or API data. The
language choice is stored in `localStorage`; the admin token only in `sessionStorage` for the tab.
Forms are `novalidate` with explicit inline errors, `aria-invalid`, `aria-live` regions, visible
focus, 44 px targets and a reduced-motion path.

## 6. Why these choices

| Choice | Reason |
|---|---|
| SQLite + WAL | One box, no DBA, trivially backupable with `sqlite3_backup`; FTS5 built in |
| Plain HTML/CSS/JS SPA | Works offline, no build step, no CDN, auditable, CSP-friendly |
| Provider abstraction | Legal information must work with **no** API key; a live model is an upgrade, not a dependency |
| Deterministic offline composer | Reproducible answers and citations for testing and audits |
| Versioned SQL migrations with `down` files | Rollback without restoring a backup; tested |
| Verification workflow in the database | Human sign-off is data, not a comment in a document |

## 7. Extension points

* **New language** — add stopwords to `services/textsearch.py`, labels in `web/app.js`, and seed
  columns; language codes are a constrained enum in `models.py`.
* **New provider** — implement `ai/base.AIProvider` and register it in `ai/registry.py`.
* **New corpus** — add a `legal_sources` row, then run `scripts/ingest_constitution.py --apply`.
* **New document format** — extend `ALLOWED` magic signatures in `security.py` and extraction in
  `services/documents.py`; both have tests that fail loudly otherwise.

## 8. Duplicate submissions (complaints)

The wizard generates one `client_request_id` per drafting session (UUID from
`crypto.randomUUID`, with a `getRandomValues` fallback). The server stores it under a partial
unique index, so a double-click, a timeout retry or a back-button resubmit returns
**409 `conflict`** with the existing reference instead of creating a second complaint. For clients
that send no key (curl, an older app), an identical payload inside `duplicate_window_s`
(default 600 s) is treated the same way. A *new* key with identical text is allowed on purpose:
a shared kiosk may file two identical complaints for two people. The retry never receives the
access token — only its hash is stored, so nobody can obtain a token by replaying a request.

## 9. Retention

`services/retention.py` enforces `NYAYMITRA_PII_RETENTION_DAYS`: complaints older than the cutoff,
their documents (rows *and* files, even if the file itself is newer), query logs and their answers
are deleted. The audit trail is kept and the purge writes one audit row with counts only. File
deletion is restricted to paths inside the storage directory; anything else is logged and skipped.
`scripts/purge_data.py` is dry-run by default and is meant to run from cron once the owner has
decided the retention period.

## 10. Operational metrics

`metrics.py` keeps a thread-safe counter map with no personal labels: HTTP totals by status class,
rate-limit hits, AI insufficient-source/rejection/fallback counts, and uptime. It is exposed to the
**monitor** role at `GET /api/v1/admin/metrics` and rendered in the admin console. It is a
single-process signal, not a time series; logs remain the long-term record.

## 11. Ingestion pipeline

```
document.pdf ─► read_pages()          page boundaries preserved
             ─► parse_articles()      number, title, body, page range, Part, Chapter
             ─► boundary_issues()     embedded headings, page headers, oversized bodies
             ─► assess_quality()      blocks apply on duplicates/malformed/low OCR/boundaries
             ─► conflict guard        never replaces non-empty or human-verified text
             ─► write + ingest_runs   report JSON, status completed | completed_with_warnings
             ─► constitution_coverage.py   loaded / with-text / verified counts, missing ranges
```

The quality gate is advisory in the library and enforced by the CLI: `--apply` exits 3 unless
`--force` is given, and a forced run is recorded as `completed_with_warnings` so the override stays
visible. Extraction is never treated as verification: imported rows keep
`verification_status = requires_human_verification`.


---

## Update 2026-11-12 — multilingual milestone

A language registry (`backend/app/languages.py`), per-language interface catalogues (`web/locales/`), a fallback-labelling middleware and the `article_texts` table were added. See [MULTILINGUAL_IMPLEMENTATION_REPORT.md](MULTILINGUAL_IMPLEMENTATION_REPORT.md) §3–4.
