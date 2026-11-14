# NYAYMITRA 2.0 — Data Activation Report

**Date:** 2026-11-12 (UTC) · **Branch:** `arena/08f8f3c5-nyaymitra-2-0`
**Project owner:** Bambhaniya Divyesh Nonghanbhai

## 1. Summary

| Question | Answer |
|---|---|
| Does the application now show its stored data? | **Yes, locally.** Constitution, Legal Library and Assistant all display real database records (31/31 end-to-end checks, in both hosting layouts). |
| Is the deployed/live website fixed? | **Not yet, and not verified.** Nothing was deployed (no approval, and the sandbox cannot reach the live sites). The fixes take effect after the owner redeploys — see the connection report. |
| Was English Constitution text found? | **No.** No English source file, extraction or article dataset exists in any branch or in Git history. |
| Was Gujarati Constitution OCR / extracted text found? | **No.** No Gujarati PDF, OCR output, extracted text or article mapping exists in any branch or in Git history. |
| What Constitution data exists? | **9 owner-written summaries** (Preamble + 8 articles), bilingual, each marked `requires_human_verification`. They are explanations, not the official text. |
| Official-text articles in the database | **English 0 · Gujarati 0** |

The mission brief assumes English processing work and Gujarati OCR/extraction work are already in
the repository. They are not there. If that work exists, it is on a device or in a location that was
never pushed to GitHub (see §7). Nothing was fabricated to fill the gap.

## 2. Where the work was done

The session can only commit to `arena/08f8f3c5-nyaymitra-2-0`. To work on the rebuild rather than
beside it, both rebuild branches were **merged into this session branch** (history preserved, their
branches untouched, `main` untouched, PR #1 untouched):

- `feature/hackindia-deployment` @ `6de0f62` (rebuild + Cloudflare/PWA/Android deployment files)
- `arena/812d6894-nyaymitra-2-0` @ `6e8efd7` (rebuild + Docker seed fix + Phase 3B)

These two had diverged from each other; this branch is now the only one containing both. The
merge needed one trivial conflict resolution (`.gitignore`). As part of the merge
`backend/justice_access.db` left the tree (the rebuild had already removed it); its 2,125 rows are
preserved in `data/legacy/…jsonl.gz` and the file itself remains on `main`.

## 3. Phase 1 — every dataset found

Searched: all four remote branches, PR refs, every path ever added or deleted in Git history,
unreachable objects, GitHub releases (0) and the owner's other public repositories
(`JARVIS-AI-Justice-Access`, `DIVU-AGI`, `rakshak-ai` — no Constitution data).

| # | Path | Format | Language | Records | Articles | Extraction | Mapping | Verification | Usable? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `data/seed/constitution_seed.json` | JSON | en + gu | 9 | 9 (Preamble, 14, 19, 21, 21A, 22, 32, 39A, 226) | n/a — hand-written | Part + number set by hand | `requires_human_verification`, `owner_authored_summary` | **Yes — as explanations only** |
| 2 | `data/seed/triage_seed.json` | JSON | en + gu | 5 guides | — | n/a | linked to departments | `requires_human_verification` | **Yes** |
| 3 | `data/seed/departments_seed.json` | JSON | en + gu | 11 offices | — | n/a | linked to sources | `requires_human_verification` | **Yes** |
| 4 | `data/seed/glossary.json` | JSON | en + gu | 18 terms | — | n/a | — | none recorded | **Yes** |
| 5 | `data/seed/sources.json` | JSON | en | 15 sources | — | n/a | — | `retrieved_on` null for official sources | **Yes** (registry) |
| 6 | `data/legacy/constitution_articles_legacy_2026-11-07.jsonl.gz` | gzip JSONL | Santali (Ol Chiki) 1,905 rows, Latin 220 | 2,125 | 0 confirmed (393 labelled, unreliable) | page-sliced, truncated at 1,200 chars | bogus numbers present | none | **No** — quarantined; admin-only |
| 7 | `backend/justice_access.db` (on `main` only) | SQLite | same as #6 | 2,125 | same | same | same | none | **No** — same data as #6 |
| 8 | `frontend/library_fix.js` (on `main` only) | JS array | same corpus as #6 | — | — | — | — | none | **No** |
| 9 | `data/raw/` | — | — | 0 files (README only) | — | — | — | — | Empty: no PDF was ever supplied |
| 10 | `data/sources/manifest.json` | JSON | — | 2 source entries | — | both `acquired: false` | — | claims unverified | Registry only — no content |
| 11 | `data/nyaymitra.db` | SQLite | — | runtime DB, git-ignored | — | built from #1–6 at start-up | — | — | Rebuilt on each machine |
| 12 | `GOVERNMENT_SUBMISSION_PACKAGE/*.pdf` (10) | PDF | en | project documents | — | — | — | — | Not legal content |

**Not found anywhere:** English Constitution PDF/text; Gujarati Constitution PDF; OCR output;
article-wise JSON/CSV; Gujarati or English article mappings; filtered datasets; Parts/Chapters
tables beyond the seed; any search index other than the SQLite FTS built at run time.
Files previously created and later removed from the tree: only #7 and #8 (both legacy Santali).

## 4. Phase 2 — database and data flow

**Database used by the application:** SQLite at `NYAYMITRA_DB_PATH` — `data/nyaymitra.db` locally,
`/data/nyaymitra.db` in the Docker image. Schema: `backend/migrations/001–004` (the rebuild schema).
No other schema is used: the separate `official_constitution_articles` table from Phase 3C was
**retired** (`ingestion/ingest.py` removed); `ingestion/` is now a download/quality tool that never
writes to a database.

```
data/seed/*.json  ──(seed_all, idempotent, at start-up or scripts/init_db.py)──▶  SQLite (rebuild schema)
data/legacy/*.gz  ──▶ legacy_import_chunks (admin-only, never public)
SQLite ──▶ /api/v1/constitution, /library, /departments, /ai ──▶ web/app.js
data/raw/*.pdf (none) ──(scripts/ingest_constitution.py, dry-run first)──▶ constitution_articles.text_en / text_gu
```

**Data imported (local run):**

| Table | Rows | Second run |
|---|---|---|
| `legal_sources` | 15 | unchanged |
| `constitution_articles` | 9 | unchanged |
| `departments` | 11 | unchanged |
| `triage_guides` | 5 | unchanged |
| `legacy_import_chunks` | 2,125 | skipped (already populated) |
| `ingest_runs` | 0 | — no official document has ever been ingested |

A verified backup was taken before re-running the import
(`backups/nyaymitra-20261112T123403Z.db`, git-ignored). No row carries `verified`.

**Why the deployed backend showed "Data Not Available" (root cause, from the files):**
on `feature/hackindia-deployment` the `.dockerignore` excluded the whole `data/` directory and the
`Dockerfile` never copied `data/seed`, so a deployed container started with **empty tables**. The
fix existed only on the other rebuild branch; it is now merged here.
This is the diagnosis from the repository — the live container was not inspected.

**Article counts by language**

| | English | Gujarati |
|---|---|---|
| Official text (`text_en` / `text_gu`) | 0 | 0 |
| Owner-written explanation | 9 | 9 |
| Title | 9 | 9 |

## 5. Phases 4–6 — what now works

**Constitution** (`#/library`): Parts shown as buttons with article counts (Preamble 1, Part III 6,
Part IV 1, Part VI 1) plus the existing Part dropdown; article list; search; article page with
number, title, explanation in English or Gujarati, source list, verification and content-type
badges. Where official text is absent the page says so in a notice — it does not show the summary
under "article text". Chapters: none are stored. A number that is not stored (e.g. 15, 300A) shows
"not found"; nothing is invented.

**Legal Library** (`#/legal`, new): one listing of everything stored — Constitution 9, Guides 5,
Offices 11, Glossary 18 = 43 items — with keyword search (Gujarati or English), category filter,
content-language filter, per-category counts, and an item page showing the stored text, content
type, verification status and source. Backed by `GET /api/v1/library` and
`GET /api/v1/library/{category}/{key}`, which only read existing tables.
*OCR document search is not available:* the only OCR-capable table (`documents`) holds private
citizen uploads (0 rows) and is not a public library; no OCR text of any legal document exists.

**Assistant** (`#/assistant`): unchanged architecture (triage → FTS retrieval → provider or
offline composer → validation → citations). Changes:

- A named article ("Article 21A", "અનુચ્છેદ ૧૫", "આર્ટિકલ ૩૨") is looked up exactly. If stored it is
  cited first; if not, the answer opens with "Article N is not available in the NYAYMITRA database".
- Each cited explanation is labelled "[explanation — not the official text]".
- Fixed: Latin triage keywords matched inside other words ("rti" inside "property"), attaching an
  unrelated guide.
- Fixed: every citation link in an answer led to a 404 (`#/library/Article14` instead of `#/library/14`).

It runs in offline rule-based mode unless an AI provider key is configured; no key was added.

## 6. Phase 7 — attribution

Exact text: **Created & Developed by Bambhaniya Divyesh Nonghanbhai**

| Place | How |
|---|---|
| Footer of every page (Home, Constitution, Library, Assistant, Complaint, Offices, Glossary, About) | `web/index.html` footer — the app is a single page, so one footer serves all |
| Homepage body | below the cards |
| About page (`#/about`, new) | with live data counts |
| Login page | The app has no citizen login. The only sign-in screen is the admin console (`/admin`); the line is in its footer. |

Styling reuses the existing colours; centred and wraps on narrow screens. Not visually reviewed in
a real browser (none is available in the sandbox).

## 7. Remaining issues

1. **No official Constitution text in either language.** Needed from the owner: the English and
   Gujarati PDFs (or the OCR/extraction output, if it exists on your device), placed in `data/raw/`.
   Then: `python scripts/ingest_constitution.py --file … --source-key … --language en|gu` (dry-run
   first; `--apply --backup` after review).
2. **Live deployment not updated or tested.** Requires your approval and the two site addresses.
3. Citizens currently see 9 articles out of 395; the app states this in its banner.
4. Seed content (articles, offices, helplines) is unverified by a legal reviewer.
5. No real-browser or mobile test was possible here; jsdom does not render layout.
6. Three branches now hold overlapping work (this one, and the two rebuild branches). A decision
   on merging to `main` is the owner's.

Test results are in `docs/NYAYMITRA_FRONTEND_BACKEND_CONNECTION_REPORT.md` §5.
