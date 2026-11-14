# Phase 3D — Database Integrity & Repository Consistency Audit

**Date:** 2026-11-12 (UTC) · **Branch audited:** `arena/08f8f3c5-nyaymitra-2-0` @ `e606a92`
**Mode:** read-only. No database row, table or file was modified; nothing was merged, reset or rebased.
The database was opened with `mode=ro&immutable=1`; its SHA-256 was identical before and after.

Each statement below is tagged **[FACT]** (measured in this audit), **[ASSUMPTION]** (inferred, not
proven) or **[OPEN]** (unresolved; needs the owner).

---

## 0. Headline findings

1. **[FACT] Phase 3C was built on the wrong base.** This session's branch was created from `main`
   (`53df9ea`, the original 4 Nov prototype). The earlier rebuild — 31 commits, draft PR #1,
   branch `arena/812d6894-nyaymitra-2-0` — was never merged into `main`, so none of it is on this
   branch. Phase 3C therefore re-implemented an ingestion pipeline that already exists on the
   other branch, with a different, incompatible schema. In Phase 3C I noticed that `data/raw/`
   and the manifest were absent but did not investigate why; that was an error on my part.
2. **[FACT] The Santali finding is real, and it was already known.** The other branch documented
   and quarantined exactly this data on 7 Nov (`data/legacy/LEGACY_DATA_NOTE.md`), citing the same
   database checksum. Phase 3C's status file described it as newly found; it was not.
3. **[FACT] `backend/justice_access.db` contains no usable article corpus**, no Gujarati, no
   source attribution and no verification status. Details in §2.
4. **[FACT] No official PDF has been acquired, extracted or imported on any branch.**

---

## 1. Repository identity

| Item | Value | |
|---|---|---|
| Repository | `https://github.com/dhundhwana-arch/Nyaymitra-2.0` (public, not a fork, created 2026-11-04) | FACT |
| Default branch | `main` @ `53df9ea` — 1 commit: "Force push completed 2125 Constitution articles to repo" (2026-11-04) | FACT |
| Current branch | `arena/08f8f3c5-nyaymitra-2-0` | FACT |
| HEAD | `e606a921334947ecb09088b58a6fdda37fe69029` (Phase 3C) | FACT |
| Remote branch | `origin/arena/08f8f3c5-nyaymitra-2-0` @ `e606a92` — same commit. No upstream-tracking config is set locally. | FACT |
| Working tree | clean before this audit; this audit adds only files under `docs/` | FACT |

### Branches on the remote

| Branch | Tip | Commits | Merge-base with this branch | Files |
|---|---|---|---|---|
| `main` | `53df9ea` | 1 | — | 18 |
| `arena/08f8f3c5-nyaymitra-2-0` (this) | `e606a92` | 2 | — | 33 |
| `arena/812d6894-nyaymitra-2-0` (previous) | `6e8efd7` | 32 | `53df9ea` | 177 |
| `feature/hackindia-deployment` | `6de0f62` | 33 | `53df9ea` | 248 |

PR #1 (`arena/812d6894-nyaymitra-2-0` → `main`): **open, draft, mergeable, 31 commits, 181 files**,
last updated 2026-11-12 11:06 UTC. `feature/hackindia-deployment` shares the previous branch's
history up to `8b1e652` and adds 5 deployment commits; it has no PR.

### Why the branch changed

- **[FACT]** This session's branch was created from `main` @ `53df9ea`.
- **[FACT]** `main` does not contain the rebuild, because PR #1 is an unmerged draft.
- **[ASSUMPTION]** Each Arena session gets its own new branch cut from the default branch, so a
  new session started "empty". Nothing was lost or overwritten: the previous branch is intact on
  the remote at `6e8efd7`.

### Same project history?

**[FACT] No.** The two `arena/*` branches share only the root commit `53df9ea`. Phases 1–3B
(rebuilt backend, migrations, 226-test suite per the PR title, legacy quarantine, ingestion script)
exist only on `arena/812d6894-…`. Phase 3C exists only on `arena/08f8f3c5-…`.

### Is this the intended repository?

**[FACT]** It is the right GitHub repository. **[FACT]** It is not the right line of work: the
current branch sits on the pre-rebuild prototype. **[OPEN]** Which branch the owner regards as
canonical (`arena/812d6894-…` or `feature/hackindia-deployment`) — see the remediation plan.

### The two database names

| Name | Where | What it is | |
|---|---|---|---|
| `backend/justice_access.db` | committed in `main` and this branch (7,331,840 bytes, sha256 `da5ff06f…7a53c`) | the original prototype's SQLite file | FACT |
| `data/nyaymitra.db` | configured in `backend/app/config.py` on `arena/812d6894-…`; git-ignored, not committed | the rebuilt app's runtime database, created by migrations | FACT (config read); contents never inspected — the file is not in any branch |
| `~/NYAYMITRA-AI/database/nyaymitra.db` | referenced by the legacy scripts in the repo root | a database on the owner's phone/PC from an older project | FACT (reference); file not available |

On `arena/812d6894-…`, `backend/justice_access.db` is no longer tracked; its 2,125 rows are
archived in `data/legacy/constitution_articles_legacy_2026-11-07.jsonl.gz`, whose note records the
same source checksum `da5ff06f…7a53c`. **[FACT]** So both branches describe the same legacy data.

---

## 2. Database integrity audit — `backend/justice_access.db`

`PRAGMA integrity_check` = `ok`; `user_version` = 0 (no migration tracking). **[FACT]** throughout
this section unless marked.

### 2.1 Tables

| Table | Rows | Notes |
|---|---|---|
| `constitution_articles` | 2,125 | columns: `id, article_no (UNIQUE), part, title_en, description_en, remedy_en` |
| `query_logs` | 0 | |
| `saved_drafts` | 0 | |
| `sqlite_sequence` | 1 | `constitution_articles = 2125` |

There is no FTS table, no source table, no run-metadata table and no user data.

### 2.2 IDs, labels, titles

- `id` runs 1–2125 with no gaps. ID order is not article order (first "Article" row is id 22 =
  `Article 118`); article-labelled rows are interleaved with chunks in short runs.
- `article_no` takes exactly two forms:

| Form | Rows | `part` value | `remedy_en` value |
|---|---|---|---|
| `Section Chunk N` | 1,732 | `Constitution Repository` | `Constitutional Provision & Statutory Guidelines.` |
| `Article N[letters]` | 393 | `The Constitution of India` | `Enforceable under Article 32 (Supreme Court) / 226 (High Court).` |

- Chunk numbers span 1–2663 with 931 numbers absent. **[ASSUMPTION]** the importer numbered every
  slice and relabelled some as "Article N" when a slice began with a number.
- `title_en`: never empty; in 1,378 rows it equals the first ≤50 characters of the description;
  6 titles are literally `--- Page N ---`. Dominant script of titles: Ol Chiki 1,850 · Latin 232 ·
  Devanagari 11 · none 32.
- `description_en`: length 16–1,200 characters, median 1,000 (fixed-size slicing); 709 embedded
  `--- Page N ---` markers covering pages 2–408; one exact duplicate description.

### 2.3 Genuine articles versus fragments

- 1,732 rows (81.5 %) are explicitly page fragments.
- 393 rows are *labelled* as articles. **None can be confirmed as a genuine, complete article:**
  - 10 have impossible numbers (> 395): 678, 923, 1461, 1789, 1956, 1988, 1996, 2002, 2011, 3359;
    plus `Article 3359A`. Example: `Article 1996` is a sentence containing "field season 1996-".
  - 72 are under 100 characters, 200 are 100–499; only 121 reach 500. Short rows such as
    `Article 118` → "…55" are contents-page entries (heading + page number), not article text.
  - All bodies are capped at 1,200 characters, so long articles are truncated by construction.
- **Verified genuine article records: 0.** **[ASSUMPTION]** some of the 393 do begin at a real
  article heading, but that cannot be established without the source PDF and a Santali reader.

### 2.4 Language / script distribution (`description_en`)

| Script | Letters | |
|---|---|---|
| Ol Chiki (Santali) | 1,277,503 | 89.9 % |
| Latin | 138,076 | 9.7 % |
| Devanagari | 4,994 | 0.4 % |
| Gujarati | **0** | |

Rows by dominant script: **Ol Chiki 1,905 · Latin 220**. Rows containing any Ol Chiki: 1,909;
purely Latin: 216. Latin-dominant rows are 6 at the start (English foreword) and 214 in ids
1751–2125 (appendices). By label: chunks 1,636 Ol Chiki / 96 Latin; "articles" 269 Ol Chiki / 124 Latin.

**Is Santali stored in English-labelled fields? [FACT] Yes** — 1,905 of 2,125 `description_en`
values and 1,850 `title_en` values are predominantly Santali. The same holds for flagship rows:
`Article 14`, `Article 21` and `Article 32` have Ol Chiki titles and bodies.

### 2.5 Duplicate and missing article numbers

- Exact duplicate labels: 0 (enforced by the `UNIQUE` constraint — which is also why collisions
  were presumably renamed or dropped by the importer; **[ASSUMPTION]**).
- Plain numbers 1–395 present: 313; **missing: 82** — 27, 28, 33, 47, 71, 78, 90, 91, 92, 94, 95,
  96, 100, 104, 123, 135, 142, 167, 175, 179, 180, 181, 183, 184, 185, 186, 189, 193, 197, 218, 231,
  237, 238, 240, 247, 249, 250, 251, 252, 268, 272, 278, 284, 286, 288, 294, 295, 302, 303, 305, 306,
  307, 309, 311, 318, 319, 324, 325, 326, 330, 332, 334, 339, 340, 346, 347, 348, 354, 355, 357, 359,
  365, 369, 373, 374, 375, 379, 382, 385, 387, 390, 391.
- 71 suffixed labels exist, including implausible ones (`20A`, `20C`, `3B`, `36B`, `3359A`).
  **[ASSUMPTION]** these come from footnote digits/letters fused to numbers; not verified against a source.

### 2.6 Source attribution and verification status

- **No source column, URL, edition, checksum, page reference or import timestamp exists.**
- **No verification-status column exists.** No row is, or can be, marked verified or unverified.
- `remedy_en` holds exactly two strings, assigned purely by label type (table in §2.2). They are
  importer-generated boilerplate, not text from any source — and "Enforceable under Article 32 / 226"
  is asserted for every article-labelled row, which is not a statement the source makes.

### 2.7 Origin of the 2,125 rows

- **[FACT]** One corpus, not a mix: the first row carries the title page of a bilingual
  Santali–English edition, "THE CONSTITUTION OF INDIA [As on November, 2025]"; "Santhali" appears
  8 times and "first edition" 4 times; page markers run 2–408 continuously.
- **[FACT]** The repo-root scripts (`extract_real_library.py`, `long_deep_migration.py`,
  `integrate_real_engine.py`) read from `~/NYAYMITRA-AI/database/nyaymitra.db` and emit exactly the
  two label forms and two "remedy" strings found here.
- **[ASSUMPTION]** So the rows are a one-off legacy import (commit date 2026-11-04) from the
  owner's older NYAYMITRA-AI database, which had ingested the Santali edition PDF page by page.
- **[FACT]** They are not from the official English or Gujarati PDFs named in Phase 3C.
- **[FACT]** The 10 hand-written seed summaries in `backend/database.py` (Preamble, Articles 14,
  19, 21, 21A, 22, 32, 39A, two BNS entries) are **not** in this database: `init_db()` only seeds
  an empty table. `Preamble` and the BNS rows are absent; `Article 14` etc. are the Santali rows.

---

## 3. Ingestion architecture and schema conflicts

Four different shapes share the name or role of "constitution articles":

| # | Object | Where | Columns / role | State |
|---|---|---|---|---|
| A | `constitution_articles` (file) | `backend/justice_access.db`, this branch + `main` | 6 columns, English-only names | 2,125 legacy Santali rows |
| B | `constitution_articles` (code) | `backend/database.py`, this branch + `main` | 8 columns incl. `title_gu`, `description_gu`, `remedy_gu`; plus FTS `legal_search_index` | never created — A already exists |
| C | `constitution_articles` (migrations) | `backend/migrations/001`+`003` on `arena/812d6894-…` | ~24 columns: `text_en/gu`, `text_status`, `verification_status`, `source_id`, `source_pages` … | lives in `data/nyaymitra.db`, uncommitted |
| D | `official_constitution_articles` | `ingestion/ingest.py`, this branch (Phase 3C) | one row per language per article, raw text, `source_sha256`, `verification_status` | table does not exist yet — never applied |

Conflicts, all **[FACT]**:

- **A vs B:** tested on a throw-away copy in `/tmp` — `database.get_all_articles()` fails with
  `OperationalError: no such column: title_gu`. The prototype backend cannot read its own database.
- **C vs D:** two competing designs for official text. C stores both languages in one row keyed
  by article number; D stores each language separately and never pairs them. They also use
  different status vocabularies (C has `text_status` + a 4-value `verification_status`).
- **Seed data:** on this branch it exists only as Python literals in `backend/database.py` (B).
  On `arena/812d6894-…` it is `data/seed/constitution_seed.json`, labelled
  `owner_authored_summary`. Phase 3C's dry-run output key `existing_seed_rows_untouched: 2125` is
  **mislabelled** — those are the legacy Santali rows, not seed summaries.
- **Run metadata:** there is no `ingestion_run` table anywhere. The previous branch has
  `ingest_runs` (source key, file, counts, missing numbers, report JSON, status). Phase 3C records
  runs only as files: `data/sources/manifest.json` and `data/reports/phase3c-report.json`.
- **Source registry:** the previous branch has a `legal_sources` table and `data/seed/sources.json`
  (official URL recorded there is India Code, with no Gujarati entry). Phase 3C has
  `data/sources/manifest.json` with the two legislative.gov.in URLs. Two registries, different URLs.

---

## 4. Real-PDF readiness (no acquisition or extraction results exist)

| Question | Phase 3C pipeline (this branch) | Earlier pipeline (`arena/812d6894-…`) |
|---|---|---|
| Expected files | `data/raw/constitution-of-india-en.pdf`, `data/raw/samvidhan-gu.pdf` | same names (`.pdf` or `.txt`) |
| Manually supplied PDF accepted? | **No.** `run` only reads a file whose SHA-256 was written to the manifest by `acquire` (a download). A hand-copied file is refused with "not acquired". | **Yes**, via `scripts/ingest_constitution.py --file … --source-key … --language …` |
| `.gitignore` | `data/raw/*.pdf` and `*.part` ignored; root `*.db` rule also ignored but `backend/justice_access.db` stays tracked because it was committed before | all of `data/raw/*` ignored except `README.md`; `*.db` ignored |
| Checksum mandatory? | **Yes** — checksum gate must pass before extraction | **[FACT]** no `sha256`/`hashlib` reference in `backend/app/services/ingest.py`; not mandatory there |
| Source metadata mandatory? | URL/edition are recorded, but edition claims are *not* checked against the document | `--source-key` must be supplied |

Consequences: a PDF placed in `data/raw/` will not appear in `git status`, will not reach this
sandbox through Git, and — on this branch — will not be accepted by the pipeline either.
Both parsers have only ever run on synthetic fixtures. Current manifest state: both sources
`acquired: false`, checksum/page count/retrieval time `null`.

---

## 5. Tests

Command: `.venv/bin/python -m pytest tests -v` (Python 3.11.2, pytest 9.2.0)

**Result: 18 collected, 18 passed, 0 failed, 0 skipped, 0.46 s.** All in `tests/test_phase3c.py`.

Not run: the suite on `arena/812d6894-…` (PR title says 226 tests; its Phase 3B report cites 19
ingestion tests). It is not part of this branch, and no figure for it is asserted here.

---

## 6. Unresolved questions

1. Which branch is canonical going forward?
2. Is the Santali edition wanted at all (as a future language), or only as archived evidence?
3. Does the old `~/NYAYMITRA-AI/database/nyaymitra.db` still exist, and does it hold anything else?
4. Edition claims for the two official PDFs (Sept 2026 / Feb 2026 vs URL paths dated 2025/08 and
   2025/07) remain unverified.
5. Official source of record: India Code (previous branch) or legislative.gov.in (Phase 3C)?
6. How will the PDFs physically reach the environment that runs ingestion?
