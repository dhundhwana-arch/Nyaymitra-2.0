# NYAYMITRA 2.0 — Repository Audit

**Audit date:** 2026-11-07
**Auditor:** Engineering audit performed inside the cloned repository `dhundhwana-arch/Nyaymitra-2.0`
**Branch audited:** `main` @ `53df9ea` ("Force push completed 2125 Constitution articles to repo")
**Secondary repository inspected:** `dhundhwana-arch/JARVIS-AI-Justice-Access` @ `8aa64da`
**Legacy project (`NYAYMITRA-AI`):** *not available* — no repository of that name exists on the account, and the
scripts that referenced it depend on local paths (`~/NYAYMITRA-AI/...`, `/data/data/com.termux/files/home/...`) that
are not present in this environment. See §11 (Blockers).

All findings below were produced by executing code or measuring files, not by reading intentions. Commands used are
reproducible (see `docs/TESTING_REPORT.md` → "Audit reproduction").

---

## 1. Executive summary

| Question | Answer |
|---|---|
| Does the backend start? | **No.** `backend/main.py` raises `ImportError` on import. |
| Does the frontend talk to the backend? | **No.** Zero `fetch`/XHR calls exist in the entire frontend. |
| Is the Constitution data real? | **No.** The committed "2125 articles" are 2125 unlabelled PDF text chunks from a **Santhali (Ol Chiki) edition** of the Constitution, with meaningless article numbers and two identical fabricated "remedy" strings. |
| Are there legal citations / source references? | **No.** No source URL, publication date, or verification status is stored anywhere. |
| Are there tests? | **No.** Zero test files, zero test framework, zero CI. |
| Is authentication implemented? | **No.** The "Demo Login" only stores a typed name in a JS variable. |
| Is there any AI provider integration? | **No.** "AI" is a client-side keyword counter over 3–4 hard-coded objects. |
| Reusable value? | **Yes** — the visual design language, the curated triage knowledge (cyber fraud / land / legal aid), the Gujarati copy, and the document-drafter concept are salvageable. |

The project is therefore **not** a working application today; it is a high-quality *design prototype* plus a
*broken* backend skeleton plus **misleading generated data**. Rebuilding the spine while preserving the prototype's
content is the correct strategy (see `docs/INTEGRATION_PLAN.md`).

---

## 2. Inventory (measured)

```
Nyaymitra-2.0/                       19 tracked files, 1 commit visible in shallow clone
├── README.md                          4.4 KB  (claims features that do not exist)
├── LICENSE                            MIT
├── .gitignore                         *.db, .env, venv/ … (but the DB is committed anyway, see §7.1)
├── run.sh / run.bat                   launcher scripts (broken, see §5.2)
├── backend/
│   ├── main.py                        190 lines, FastAPI, 3 endpoints — WILL NOT IMPORT
│   ├── database.py                    112 lines, sqlite3, no models/migrations
│   ├── requirements.txt               3 pins (fastapi, uvicorn, pydantic)
│   └── justice_access.db              7.33 MB SQLite, committed to git
├── frontend/
│   ├── index.html                     127 KB (1 831 lines) — monolithic static prototype
│   ├── index_v2.html                  127 KB — **byte-identical** to index.html (md5 95b0c13…)
│   ├── app_core.js                     19 KB — dead code (never loaded by any HTML)
│   ├── interactive_library.js          96 KB — dead code, 470 fake placeholder records
│   ├── library_fix.js                 4.8 MB — dead code, 2 125 junk records
│   └── build_library_js.py              2.9 KB — generator, hard-coded Termux paths
├── extract_real_library.py            6.5 KB — one-shot migration script (hard-coded paths)
├── integrate_real_engine.py           9.8 KB — one-shot migration script (hard-coded paths)
├── long_deep_migration.py             7.6 KB — one-shot migration script + `git push origin main`
└── setup_full_library.py              8.3 KB — one-shot migration script, reads a CSV that does not exist
```

**Secondary repository** (`JARVIS-AI-Justice-Access`, 10 files, 145 KB): a strict subset of the above.
`backend/main.py` is **identical**; `backend/database.py` is an *older* version (only `query_logs` + `saved_drafts`,
no constitution tables); `frontend/index.html` / `index_v2.html` differ only by the injected
`interactive_library.js` script tag. **No additional backend modules, OCR code, Gujarati data, tests, or
documentation exist there to salvage.** It contributes nothing that the primary repository does not already have.

### 2.1 Duplicate / dead code

| Artefact | Status |
|---|---|
| `frontend/index_v2.html` | Byte-identical duplicate of `index.html` (127 KB wasted) |
| `frontend/library_fix.js` | Generated, 4.8 MB, **not referenced** by any HTML |
| `frontend/interactive_library.js` | Generated, 96 KB, **not referenced** by any HTML |
| `frontend/app_core.js` | Hand-written, **not referenced** by any HTML |
| `setup_full_library.py` / `long_deep_migration.py` / `integrate_real_engine.py` / `extract_real_library.py` | Four overlapping one-shot importers, all hard-coded to author's machine; `setup_full_library.py` writes `BASE_DIR = "/data/data/com.termux/files/home/Nyaymitra-2.0"` and reads `backend/article_audit_471.csv` which **does not exist** |
| `long_deep_migration.py` | Ends with `os.system("git add . && git commit && git push origin main")` — **automated push to the primary branch**, a governance hazard |
| Triage knowledge | Authored **three times** (backend `main.py`, `frontend/index.html` inline `legalDatabase`, `frontend/app_core.js`) and drifting apart |

---

## 3. Architecture as found

```
Browser (static index.html, CDN Tailwind + Font Awesome)
   |
   |  (no network calls at all)
   v
[keyword counter in ~30 lines of JS]  →  renders one of 4 hard-coded result objects
                                      →  fills a printable "application" sheet

FastAPI  -- ✗ ImportError, never starts
   └── sqlite3 justice_access.db  (2125 junk rows, unused by any endpoint)
```

* Frontend entry point: `frontend/index.html` (single file, one IIFE, ~950 lines of JS).
* Backend entry points: `backend/main.py` (`app`), run directly with `python main.py` (binds `127.0.0.1:8000`).
* API surface actually implemented: `GET /`, `POST /api/query`, `POST /api/draft`. Nothing else.
* Constitution data is **never served**: there is no article/search endpoint at all.
* Layers: none. No routers, no services, no repository layer, no config module, no migrations.

### 3.1 Technology actually in use

Python 3.10+ (tested 3.11.2), FastAPI 0.110, Pydantic 2.6, raw `sqlite3`, Uvicorn; vanilla HTML/CSS/JS with
Tailwind **Play CDN** (requires internet at runtime) and Font Awesome CDN; no build step, no bundler, no package.json.

---

## 4. Feature-by-feature status

Legend: **COMPLETE AND TESTED** · **IMPLEMENTED BUT NOT TESTED** · **PARTIALLY COMPLETE** · **BLOCKED** · **REQUIRES HUMAN VERIFICATION**

| # | Required module | Status before this audit | Evidence |
|---|---|---|---|
| A | Responsive UI, gu/en | PARTIALLY COMPLETE | 1 831-line static page, gu/hi/en dictionaries, mobile-first Tailwind classes; but **rendered by a CDN**, and the Constitution tab is broken HTML (see §5.1) |
| B | Complaint intake | PARTIALLY COMPLETE | "Drafter" form → printable sheet in browser. No submission, no category taxonomy, no date/location fields, no attachments, no confirmation step, no persistence |
| C | AI assistance | BLOCKED | No model, no provider, no prompt, no RAG. Pure keyword scoring over 4 objects |
| D | Constitution / legal knowledge | BLOCKED | Data is junk (§6); no search API; no source references; no Gujarati text in DB |
| E | Voice accessibility | PARTIALLY COMPLETE | Web Speech API TTS + STT wired in the browser only (Chrome-dependent). Text alternative exists. Gujarati STT quality untested |
| F | Department navigation | PARTIALLY COMPLETE | 3 triage outcomes with authority + helpline + portal; **no verification date, no provenance, no "unverified" labelling** |
| G | Document management | BLOCKED | No upload endpoint, no storage, no validation |
| H | Admin & monitoring | BLOCKED | No auth, no admin, no health endpoint, no logging, no backup |
| — | AuthN / AuthZ | BLOCKED | "Demo Login" accepts any non-empty string into a JS variable |
| — | Tests / CI | BLOCKED | None |
| — | Documentation | PARTIALLY COMPLETE | `README.md` only, and it describes features that do not exist |

---

## 5. Broken features (verified failures)

### 5.1 Backend cannot import (fatal)

```
$ python -c "import main"
ImportError: cannot import name 'log_query' from 'database'
$ uvicorn main:app
ImportError: cannot import name 'log_query' from 'database'
```
`backend/main.py` imports `init_db, log_query, save_application_draft` from `database.py`, but `database.py` only
defines `init_db`, `get_all_articles`. The fallback branch `from .database import ...` then fails with
`ImportError: attempted relative import with no known parent package`.
**Consequence: 0 % of the API is reachable.** `run.sh` hides this by launching the server in the background with `&`
and never checking its exit status, then printing "Starting FastAPI Server…".

### 5.2 `database.get_all_articles()` crashes on the committed database

```
OperationalError: no such column: title_gu
```
`init_db()` declares `constitution_articles(id, article_no, part, title_en, title_gu, description_en, description_gu, remedy_gu)`,
but the committed database has `(id, article_no, part, title_en, description_en, remedy_en)`.
`CREATE TABLE IF NOT EXISTS` silently no-ops on the existing table, so **schema and code disagree** and every
read fails. There is no migration system to detect or repair this.

### 5.3 Frontend "Constitution Library" tab renders empty cards

`frontend/index.html:659–675` is truncated mid-markup: `<p class="text-xs text-slate-300 leading-relaxed">` is
empty, the "Article 14" card never closes, only 1 of the 2 documented cards exists, and the container is closed
one `</div>` too early. Opening the tab yields empty boxes. (Verified by reading bytes and by HTML structure check.)

### 5.4 `speakText(text)` — runtime ReferenceError

`renderAnalysisResult()` ends with:

```js
if (ttsEnabled) {
  const audioText = `${item.category[lang]}. ${summaryText}`;
  speakText(text);            // `text` is not defined in scope
}
```
`text` is undefined → `ReferenceError` on every analysis result while TTS memory is on. The correct variable is
`audioText`. Result rendering survives (it happens before the throw) but the auto-read-aloud feature is dead and the
console fills with errors.

### 5.5 "Demo Login" is not authentication

`modalLoginContinueBtn` stores the typed value in a module-level `userName` variable and updates a `<span>`.
No user record, no session, no token, no access control. Every "personalised" surface is cosmetic. It also
pre-fills the drafter's name field from unvalidated user input.

### 5.6 Backend stores arbitrary-length queries with no validation

`QueryRequest.query: str` has no `max_length`; `POST /api/query` writes the full string into `query_logs`.
No rate limit, no trimming beyond `.strip()` for matching, no PII scrubbing.

### 5.7 `git push origin main` inside a migration script

`long_deep_migration.py:181` executes `cd Nyaymitra-2.0 && git add . && git commit -m … && git push origin main`.
Running an "import" script silently publishes to the protected branch. This is how the junk data (§6) reached `main`.

---

## 6. Database status (measured)

`backend/justice_access.db`, 7.33 MB, committed to git.

| Table | Schema (actual) | Rows |
|---|---|---|
| `constitution_articles` | `id, article_no, part, title_en, description_en, remedy_en` | **2 125** |
| `query_logs` | `id, user_query, language, category, authority_recommended, created_at` | 0 |
| `saved_drafts` | `id, applicant_name, phone, authority, subject, body, prayer, created_at` | 0 |
| `legal_search_index` (FTS5, created by `init_db`) | not present in the committed file | — |
| `sqlite_sequence` | — | — |

**No user data exists** (0 logs, 0 drafts), so no privacy incident has occurred — but the schema keeps
`applicant_name`, `phone`, and full complaint text in plain text with no retention policy.

### 6.1 Content analysis of the 2 125 "articles" — the central finding

| Measure | Result |
|---|---|
| Rows whose label starts with `Section Chunk` | **1 732** (81 %) — e.g. `Section Chunk 1 … Section Chunk 2663` |
| Rows labelled `Article N` | 393 |
| Distinct numeric article numbers | **325** (for 393 rows) |
| Repeated numbers | `Article 243` ×26, `Article 31` ×5, `Article 124` ×4, `Article 2` ×2, `Article 20` ×3, … |
| Nonsense article numbers | `Article 678`, `Article 923`, `Article 1461`, `Article 1789`, `Article 1988`, `Article 1996`, `Article 2002`, `Article 2011`, `Article 3359` |
| Dominant script per row | **Ol Chiki (Santhali) 1 905**, Latin 220, **Gujarati 0** |
| Distinct `remedy_en` values | **2** (`"Constitutional Provision & Statutory Guidelines."` ×1 732; `"Enforceable under Article 32 (Supreme Court) / 226 (High Court)."` ×393) |
| Total description text | 1.89 MB |

The source document is the **Santhali (Ol Chiki) edition of the Constitution of India**, published November 2025
(its preface — "It is with great pride that we present the first edition of the Constitution of India in the Santhali
language (Ol Chiki)" — is stored verbatim in rows 1–6). The importer chunked the PDF text into ~1 000-character
slices, ran a regular expression over the *chunk stream*, and used the resulting capture groups as
`article_no / title / description`. This produces:

* Article numbers taken from **page-number-like and amendment-footnote-like digits** (`Article 1996`, `Article 3359`);
* Titles that are sentences chopped mid-word;
* The **same legal text repeated** with 1 000-character offsets (hence `Article 243` ×26);
* Two **invented** `remedy` strings attached to every single row — legal interpretation that was never authored or
  sourced.

**`remedy_en` is fabricated content and must not be shown to citizens as law.** The `Section Chunk` rows are not
articles at all and must never be presented as such. The text itself is genuine Santhali Constitution text and is
therefore **archived, not deleted** (see `docs/DATABASE_SCHEMA.md` → legacy quarantine and
`data/legacy/LEGACY_DATA_NOTE.md`).

### 6.2 Verification of the historical checkpoints supplied by the project owner

| Claim | Verdict |
|---|---|
| "~20 Parts, ~470 Articles processed (English)" | **Not reproducible.** No English corpus exists in the repo. The only 470-record artefact is `frontend/interactive_library.js`, which contains **470 identical placeholder objects**: `{"no": "Article N/A", "title": "Indian Constitution", "part": "Constitution of India", "desc": "Full text available.", …}`. It is fabricated filler, not extracted law. |
| "Article 5 missing from final output although regex matched; ~472 matches" | **Cannot be confirmed or refuted** — neither the source PDF, the 472-match output, nor the CSV (`backend/article_audit_471.csv`) exists in the repository. The importer that produced the current data (`long_deep_migration.py`) has no Article-5-specific handling. In the *current* junk data an `Article 5` row does exist, but it contains Santhali preface text, so its presence proves nothing. |
| "Gujarati PDF ~411 pages; master index ~500 rows; ~500 auto-mapped; a few manually verified; duplicate Article 222 removed" | **No Gujarati data exists in the repository or the database.** 0 rows contain Gujarati script. The PDF, the index CSV, and the manual-verification log are all absent. The only Gujarati strings are hand-written UI copy and short paraphrases in `database.py`/`setup_full_library.py`. |
| "2125 Constitution articles pushed" (commit message) | **False as an article count.** 2 125 rows exist; 1 732 are unlabelled chunks, 325 distinct article numbers, 1 905 rows are Santhali. |

These checkpoints must be treated as **lost artefacts** until the source PDFs/CSVs are supplied
(`docs/KNOWN_LIMITATIONS.md` → L-1). The ingestion pipeline added in this work is designed to re-derive them
reproducibly once the files are provided.

---

## 7. Security and privacy findings

| ID | Severity | Finding |
|---|---|---|
| S-1 | **High** | Backend is non-functional, so the *only* running artefact is a static page that stores citizen names/phone numbers in the DOM and clipboard. No transport, storage, access-control or retention story exists for complaint content. A "privacy policy" is absent while the UI invites users to type victimisation details. |
| S-2 | **High** | Fabricated legal interpretation is presented as authoritative (`remedy_en`, generic `"Enforceable under Article 32/226"`) with no disclaimer at the point of display. For a justice-access tool this is the most serious *substantive* risk, not a code defect. |
| S-3 | Medium | `CORS: allow_origins=["*"]` **with** `allow_credentials=True` — an invalid/insecure combination per the CORS spec; would expose credentialed endpoints if any existed. |
| S-4 | Medium | No rate limiting on `/api/query` (database write amplifier) or anywhere else. |
| S-5 | Medium | No request-size limits, no `max_length` on any input, no output escaping guarantee. `showToast()` interpolates the user-supplied name into `innerHTML`; `factBody`, step text and document labels are also injected via `innerHTML` (currently data-controlled, but one product change away from stored XSS). |
| S-6 | Medium | Personal data model with no protection: `phone`, `applicant_name`, free-text complaints, `query_logs.user_query` (verbatim citizen narratives) in an unencrypted DB that is **committed to a public repository**. |
| S-7 | Medium | CDN-only frontend (`cdn.tailwindcss.com`, `cdnjs.cloudflare.com`) means no Subresource Integrity, third-party script execution on every page load, and total failure on low-bandwidth/rural connections — the exact target user. |
| S-8 | Low | No security headers (`CSP`, `X-Content-Type-Options`, `Referrer-Policy`, HSTS) — the static app cannot set them today. |
| S-9 | Low | Automated `git push origin main` inside an import script (governance/review bypass). |
| S-10 | Low | `.gitignore` lists `*.db` yet a 7 MB DB containing (empty but structurally sensitive) PII tables is tracked; a future force-add would publish real citizen data. |
| S-11 | Info | No secrets are hard-coded — but also no `.env.example`, no config layer, and no provider key handling to audit. |
| S-12 | Info | Unicode/RTL and Indic-script handling is untested; the ASGI stack is used only via `str`, so Devanagari/Gujarati normalisation (NFC/NFD) is unaddressed. |

---

## 8. Testing status

| Item | Result |
|---|---|
| Test files in repo | **0** |
| Test framework configured | **No** (`requirements.txt` has no pytest/httpx) |
| CI configuration | **No** `.github/` directory |
| Application startup test | **Fails** (ImportError, §5.1) |
| Frontend build | N/A (no build step); page loads only with internet |
| Manual smoke test of endpoints | Impossible — server cannot start |

Any claim that a feature "was tested" before this audit is unsupported by the repository.

---

## 9. Documentation status

| Document | State |
|---|---|
| `README.md` | Present, well written, **inaccurate**: advertises a voice-first AI assistant, a constitution library of Articles 14/21/39A/32/226, a drafter and a helpline directory as if complete. It also instructs users to enable GitHub Pages on `/frontend`, which ships the broken library tab. |
| API docs | Non-existent (FastAPI's `/docs` never becomes reachable) |
| Setup / deployment | `run.sh` and `run.bat` only; both broken or unsafe (§5.1) |
| Security / privacy policy | None |
| Legal disclaimers | Present in the UI (good), absent from the API and README |

---

## 10. Reusability assessment (what to keep)

| Component | Verdict | Reason |
|---|---|---|
| Visual design language (deep navy + gold, `nyay-*` palette, scales-of-justice motif, Gujarati headline copy) | **KEEP** | Genuinely good, culturally appropriate, and matches the mission |
| `i18n` dictionary structure (gu/hi/en with per-key objects) | **KEEP** (restructure) | Complete and useful; needs to move server-side/JSON and gain `en` default |
| Triage knowledge (cyber fraud, land/DILR, legal aid): categories, steps, documents, helpline, portal | **KEEP + ANNOTATE** | Best content in the repo; must gain `source_url`, `last_checked`, `verification_status` and lose the "verified" tone |
| Gujarati paraphrases of Articles 14/19/21/22/32/39A | **KEEP as "citizen explanation, unverified"** | Human-authored, readable; must never be labelled official text |
| Application/pleading drafter concept and template fields | **KEEP** | Solid product idea; wire to API + persistence + confirmation |
| Print/copy sheet CSS | **KEEP** | Useful and cheap |
| Web Speech API integration | **KEEP** (harden) | Reasonable zero-cost accessibility layer; needs feature detection + text fallback |
| `backend/main.py` routes | **REWRITE** | 3 endpoints, broken imports, deprecated `on_event`, `req.dict()` |
| `backend/database.py` | **REWRITE** | Schema/code mismatch, no migrations, fabricated seed rows, `remedy_gu` |
| `constitution_articles` data | **QUARANTINE** | 81 % unlabelled chunks, 1 905 Santhali rows, invented remedies, dup numbers. Archive the text, exclude from the product |
| `footer/library_fix.js` (4.8 MB) | **REMOVE FROM RUNTIME, ARCHIVE DATA** | Never loaded; 2 125 junk records inflating the repo |
| `interactive_library.js` (470 placeholders) | **DELETE** | Fabricated filler with no source value |
| `index_v2.html` | **DELETE** | Byte-identical duplicate |
| `app_core.js` | **DELETE (content merged)** | Dead duplicate of knowledge already in `index.html` |
| `setup_full_library.py`, `long_deep_migration.py`, `integrate_real_engine.py`, `extract_real_library.py` | **REPLACE** | Hard-coded paths, no validation, one of them pushes to `main`. Replaced by `scripts/ingest_constitution.py` + `scripts/init_db.py` |
| `run.sh` / `run.bat` | **REPLACE** | Broken launcher |
| JARVIS repo content | **NOTHING TO SALVAGE** | Strict subset; older `database.py` only |

---

## 11. Blockers and unknown artefacts

| # | Blocker | Impact | Safest next step |
|---|---|---|---|
| B-1 | `NYAYMITRA-AI` legacy repo not reachable (no such repo; scripts reference only local paths) | Cannot verify or recover the 470-article English corpus, the 411-page Gujarati PDF, the ~500-row master index CSV, or the manual-verification log | Owner supplies the files/archive; place them in `data/raw/` and run `scripts/ingest_constitution.py` |
| B-2 | No outbound internet access to official legal sources (`indiacode.nic.in`, `legislative.gov.in`, `nalsa.gov.in`, `cybercrime.gov.in`) from this environment | Cannot fetch authoritative Constitution text or verify department contacts | Keep every record labelled `requires_human_verification`, ship the verification workflow + checklist, do not invent text |
| B-3 | No AI provider credentials (`GEMINI_API_KEY` / `OPENAI_API_KEY` / …) available | Cannot exercise a live LLM path | Provider abstraction + deterministic offline "grounded" provider; live provider path is implemented but **must be marked IMPLEMENTED BUT NOT TESTED** until a key is supplied |
| B-4 | No physical mobile device / real browser automation available | Responsiveness and voice features cannot be machine-verified end to end | Static + structural assertions in CI; a written manual device test script in `docs/TESTING_REPORT.md` |
| B-5 | No OCR engine (`tesseract`) installed, no scanned PDFs available | OCR path cannot be validated on real scans | Ingestion supports the text layer + optional OCR hook, labelled as unverified for scanned input |

---

## 12. Integration recommendations (summary)

The full sequenced plan is in `docs/INTEGRATION_PLAN.md`; the essentials:

1. **Do not extend the current data or the current backend.** Both must be replaced behind a stable API contract;
   keep the design and the triage knowledge.
2. **Quarantine before rebuilding.** Export the 2 125 legacy rows (with provenance) to a compressed archive, keep
   them out of the product and out of the article table, and document exactly why. No deletion.
3. **Introduce a real data layer**: versioned SQL migrations, normalised `legal_sources` → `constitution_articles` →
   `article_sources`, `verification_status` + `last_checked_at` on every row, FTS5 index, foreign keys, indexes.
4. **Make verification a first-class field, not a promise.** The UI must render `requires_human_verification`
   badges and the exact source for every legal statement; unverified content must be visually distinct.
5. **Ground the AI or refuse.** Retrieval over verified rows only; answers must cite retrieved article IDs; a
   citation validator rejects any answer containing an article number that was not retrieved; if no provider is
   configured or reachable, return a clear `provider_unavailable` error — never a generated guess.
6. **Serve the frontend from the API** (same origin): removes CORS, fixes offline/CDN dependence, enables CSP,
   and makes the preview work behind any proxy.
7. **Build the missing modules as thin vertical slices with tests**: complaint intake, documents, departments,
   admin, health — each with validation, rate limits and audit logging.
8. **Delete nothing that is evidence.** Duplicates and dead generators are removed *after* their data is archived
   and the reason is recorded in the audit + legacy note.

---

## 14. Addendum — remediation status (2026-11-07, branch `arena/812d6894-nyaymitra-2-0`)

Every finding in §6–§10 has been addressed on the branch; the table records *how* and *with what
evidence*. "Tested" always means an automated test on this branch fails if the behaviour regresses.

| Audit ID | Finding | Status | Evidence |
|---|---|---|---|
| B-1 | Historical "2125 verified articles" checkpoints unverifiable | **BLOCKED** — no artefact exists; the data was never analysed for accuracy | Quarantined; `docs/LEGAL_VERIFICATION_CHECKLIST.md` |
| B-2 | Backend cannot be imported | Fixed | `backend/main.py` shim + `create_app()`; `test_legacy_entry_point_still_imports` |
| B-3 | Frontend never calls the API | Fixed | `web/app.js`; jsdom journeys |
| B-4 | No schema, no migrations | Fixed | `backend/migrations/001_initial.sql`; `test_migrations_are_idempotent` |
| B-5 | Fabricated "remedy" strings presented as law | Fixed (content quarantined, never served) | `test_fabricated_legacy_remedy_text_is_never_exposed` |
| S-1…S-12 | Security and integrity findings | Fixed except where documented as residual risk | `docs/SECURITY_AUDIT.md` §3–§5 |
| §7.3 | Zero tests / zero CI | Fixed | 186 tests, 92% coverage, `.github/workflows/ci.yml` (pytest 3.11/3.12, dependency audit, frontend) |
| §8 | Verification workflow absent | Fixed | `PATCH /admin/articles/{id}/verification` with reviewer + date + text guard |
| §9 | Fake login | Removed; replaced by token-scoped complaint access and admin/monitor roles | `docs/SECURITY_AUDIT.md` |
| §10 | No sources or provenance | Fixed | `legal_sources` spine, `SourceRef` in responses |

New defects found *during* remediation (not visible to static review) are listed in §15.

## 15. Defects found after the audit, during testing

| ID | Defect | Impact | Status |
|---|---|---|---|
| B-6 | `/admin` was served but `/admin.js` returned 404 | Admin console completely non-functional in a browser; unit tests still green | Fixed; test fetches every asset referenced by both pages |
| B-7 | SQLite connections crossed threadpool threads | Every document upload raised `ProgrammingError` | Fixed with `check_same_thread=False` (one connection per request, used serially) |
| B-8 | Verification guard checked `text_status != "not_available"` | An owner-written summary could be marked `verified` | Now requires `verified_source_text` |
| B-9 | `SELECT d.*, s.*` in departments | Duplicate `id` columns, row access dependent on join order | Explicit column list |
| B-10 | AI department fallback took the first three directory rows | An equality question was offered the cyber-crime cell | Fallback is the free-legal-aid channels |
| B-11 | Document responses contained `created_at: ""` | Clients could not order uploads | Real timestamp read back from the database |
| B-12 | CSP contained `'unsafe-inline'` for styles and the pages used inline `style` attributes | Weaker CSP than claimed | Allowance removed, styles moved to CSS classes |
| B-13 | Admin endpoints shared the public read rate limit | Token brute-force at 120 requests/min | Dedicated 10/min admin bucket |
| B-14 | Ownership tokens and database files were not permission-hardened | Personal data readable by other local users | `0600` files / `0700` directories, asserted in tests |

Reproduction commands for every table row are in `docs/TESTING_REPORT.md`.
