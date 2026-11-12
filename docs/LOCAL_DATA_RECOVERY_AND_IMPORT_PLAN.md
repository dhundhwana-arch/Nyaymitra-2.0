# Local Constitution Data Recovery and Import Plan

**Date:** 2026-11-12 (UTC) · **Branch:** `arena/08f8f3c5-nyaymitra-2-0`

## 1. Recovery result

**No Constitution dataset was recovered. The environment that ran this search cannot see the
owner's Android/Termux filesystem, and that device was not searched.**

### What was searched

| Location | Result |
|---|---|
| Working tree of this repository (all files, including git-ignored ones) | No English/Gujarati Constitution source, extraction, CSV index, mapping or OCR output |
| Git history of all 4 remote branches and PR #1 (every path ever added or deleted) | Same — done in the previous mission, re-checked |
| Whole sandbox filesystem (`/`, excluding system directories) for `*.pdf, *.csv, *.db, *.sqlite, *.jsonl, *.xlsx, *.zip` and names containing constitution / samvidhan / bandharan / gujarati / ocr / master_index | Only this repository's own files and temporary test files |
| `/mnt`, `/media` | Empty |
| `/sdcard`, `/storage`, `/data/data/com.termux`, `~/NYAYMITRA-AI` | **Do not exist in this environment** |
| Attachments to the conversation | None were provided |

### What was not searched (cannot be reached from here)

- The owner's phone: `/data/data/com.termux/files/home/…`, `~/NYAYMITRA-AI/`, `~/storage/shared/…`
- Any PC, SD card, Google Drive or other cloud storage
- Any private GitHub repository not visible to this session

The legacy scripts in this repository do point at where the earlier work lived — these are leads,
not findings:

- `~/NYAYMITRA-AI/database/nyaymitra.db`
- `~/NYAYMITRA-AI/database/nyaymitra_pre_constitution_backup.db`
- `~/NYAYMITRA-AI/database/nyaymitra_before_library.db`
- `~/NYAYMITRA-AI/backend/modules/constitution_library.py`
- `/data/data/com.termux/files/home/Nyaymitra-2.0/` (including `backend/justice_access.db`)

### Expected artifacts versus found

| Expected (owner's description) | Found | Path | Size | Suitable for import |
|---|---|---|---|---|
| English extraction, ~20 Parts / ~470 Articles | **No** | — | — | cannot be assessed |
| Gujarati Constitution PDF, ~411 pages | **No** | — | — | cannot be assessed |
| Gujarati master index CSV, ~500 rows | **No** | — | — | cannot be assessed |
| Gujarati article mapping and OCR outputs | **No** | — | — | cannot be assessed |
| Filtered / verified datasets | **No** | — | — | cannot be assessed |

Article counts, language distribution, duplicate and missing numbers and OCR quality **cannot be
reported for files that are not available**; no figures are given here.

One caution for when the files turn up: the only Constitution data ever committed was a
Santali–English edition whose page markers run to page 408, stored in a database also named
`nyaymitra.db`. A "~411-page" PDF and a "~470 article" extraction should be opened and checked to
confirm they are the Gujarati and English editions and not that Santali edition. The inventory
tool below reports the script mix (Gujarati / Latin / Ol Chiki) of every file for exactly this reason.

## 2. How the owner can produce the inventory (read-only, a few minutes)

On the device that holds the files (Termux or PC), from a checkout of this branch:

```bash
python scripts/inventory_local_data.py ~/NYAYMITRA-AI ~/storage/shared \
    --out data/reports/local-data-inventory.json
```

It needs only Python (PDF page counts additionally need `pip install pypdf`). It reads files and
writes one JSON report: path, size, SHA-256, format, CSV rows and columns, JSON record counts,
SQLite tables and row counts, PDF page count and whether a text layer exists, script mix, and for
any column that looks like article numbers: duplicates and missing numbers 1–395. It does not
modify, move, upload, OCR or import anything. Tested here against this repository's own data files.

Then send back **the JSON report and the files themselves** (attach them to the session, or push
them to a private location; PDFs in `data/raw/` are git-ignored on purpose).

## 3. The existing import pipeline — what it does today (verified from the code)

Entry point: `scripts/ingest_constitution.py --file F --source-key K --language en|gu [--apply] [--backup] [--replace-existing] [--force] [--report R]`
Logic: `backend/app/services/ingest.py`. Target: `constitution_articles` (migrations 001–004).

| Requirement | Today | Evidence |
|---|---|---|
| Dry-run by default | Yes | `--apply` is explicit |
| Backup before import | Only if `--backup` is passed | must be made mandatory in the runbook |
| Idempotent | Yes — identical text counts as unchanged; different text is a "conflict" and is not replaced without `--replace-existing` | `ingest_text` |
| Never overwrites human-verified rows | Yes | `articles_skipped_verified` |
| Official text separate from owner summaries | Yes — text goes to `text_en` / `text_gu`; `citizen_explanation_*` is never touched | UPDATE statement |
| English and Gujarati stored separately | Columns are separate, **but see gaps 3–5** | |
| Verification status | Stays `requires_human_verification` | INSERT/UPDATE |
| Part / Chapter / pages captured | English `PART`/`CHAPTER` headings and page range, from PDF or text | `PART_RE`, `CHAPTER_RE` |
| Run metadata | `ingest_runs` row with counts and full report | no file checksum |
| Santali legacy fragments | Cannot enter: the importer reads only the named file, accepts only `.pdf/.txt/.md/.json`, and `legacy_import_chunks` is a separate admin-only table | |

### Gaps that affect the expected files (each reproduced with synthetic input, not real text)

| # | Gap | Consequence |
|---|---|---|
| 1 | **No CSV or structured-JSON importer.** Only a PDF text layer or plain text is parsed. | A master-index CSV, an article-wise JSON, or OCR output already split by article cannot be imported as they are. |
| 2 | **Contents pages create duplicates.** A heading does not need the `.—` separator, so `14. Equality before law` in the contents and in the body both match. | A full PDF fails the quality gate; with `--force` the *contents line* would be kept and the real article dropped. |
| 3 | **Gujarati digits create separate rows.** `૧૪.` is accepted and stored as article number `૧૪`, which does not match the existing row `14`. | Gujarati text would not attach to its English article; duplicates of every article. |
| 4 | **Suffixes longer than one letter are not recognised** (`243ZA`, `239AA`). | Those articles are missing and their text is swallowed by the previous article. |
| 5 | **One source/page slot per article.** `source_id`, `source_locator`, `source_pages`, `part_title`, `chapter_title` are single columns. | Importing Gujarati after English overwrites the English page reference and replaces the English Part title with the Gujarati one. |
| 6 | **OCR text is labelled `verified_source_text`.** The only status values are `verified_source_text`, `owner_authored_summary`, `not_available`. | OCR output would carry a "verified" label in the UI badge even though `verification_status` says otherwise. |
| 7 | No Gujarati `ભાગ` / `પ્રકરણ` heading patterns. | Part/Chapter not captured from a Gujarati-only source. |
| 8 | No SHA-256 of the source file stored with the run. | Cannot prove later which file a row came from. |

## 4. Import plan (not executed — to be finalised after the files are inspected)

**Step 0 — Identify and inspect.** Inventory JSON + the files. Confirm for each: language/script,
edition and "amended up to" line, page count, whether it is a text-layer PDF or OCR output,
column meanings of the CSV, and how article numbers are written. Nothing below is fixed until then.

**Step 1 — Register sources.** Add one entry per file to `data/seed/sources.json`
(English and Gujarati separately; `source_type` `official` only for the government PDF itself,
and a distinct entry such as "owner OCR of <PDF>" for OCR output), with URL, edition, SHA-256 and
who supplied it. No Santali source is used.

**Step 2 — Close the gaps that the actual files require (small, tested changes; no new tables
unless listed):**

| Change | Addresses | Schema change |
|---|---|---|
| Per-language provenance: write one `article_sources` row per (article, source) with its own locator/pages, instead of overwriting the single slot | gap 5 | none — table already exists |
| Add `part_title_gu`, `chapter_title_gu` | gap 5, 7 | migration 005 (two nullable columns) |
| Add a text status for machine-extracted text, e.g. `ocr_extracted_text`, shown as "OCR — not verified" | gap 6 | migration 005 (CHECK constraint) |
| Normalise Gujarati digits to the canonical number for matching, keep the printed label in the locator | gap 3 | none |
| Accept multi-letter suffixes; require the `.—` separator or skip the contents range | gaps 2, 4 | none |
| Structured importer for CSV/JSON with an explicit column mapping file reviewed by the owner | gap 1 | none |
| Store SHA-256 in `ingest_runs.report_json` | gap 8 | none |

**Step 3 — Dry run per file, per language** (`--report`), English first. Review: articles found,
duplicates, missing numbers, boundary issues, short bodies, text quality.

**Step 4 — Cross-language report.** Numbers present in one language only; suffixed articles are
listed for the owner to pair — never paired automatically.

**Step 5 — Owner sign-off** on the reports (omitted/repealed numbers explained).

**Step 6 — Backup, then apply.** `python scripts/backup_db.py`, then `--apply --backup`, English
then Gujarati. Re-run once to prove idempotence (expected: 0 written, all unchanged).

**Step 7 — Verify in the app.** `scripts/constitution_coverage.py`, `/api/v1/constitution/coverage`,
the end-to-end script, and a manual read of sample articles in both languages. All rows remain
`requires_human_verification` until a person changes them one by one in `/admin`.

**Rollback:** restore the backup taken in step 6 (`scripts/backup_db.py --list`).

## 5. Blockers

1. The files are not accessible from here — **owner action required**.
2. Formats and column layouts are unknown, so the importer changes in step 2 cannot be finalised.
3. Whether the OCR text is Unicode Gujarati (not a legacy font encoding) is unknown.
4. A legal reviewer is still needed before anything is shown as verified.


---

## Update 2026-11-12 — multilingual milestone

Section 3's gaps 3, 4, 5, 6, 7 and 8 are closed and two further defects found while fixing them (Part headings between articles; heading text left in the previous article) are fixed — see [MULTILINGUAL_IMPLEMENTATION_REPORT.md](MULTILINGUAL_IMPLEMENTATION_REPORT.md) §5. Gap 1 (no CSV/JSON importer) and gap 2 (contents pages) remain. Two findings from reading the official files' first pages change step 0: the "English" PDF is a Hindi–English diglot, and the Gujarati PDF's extracted text shows detached vowel signs — see [DATA_SOURCE_REGISTER.md](DATA_SOURCE_REGISTER.md). The owner's files are still not available; no import was run.
