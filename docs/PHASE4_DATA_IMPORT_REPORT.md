# Phase 4 — Constitution data recovery & import automation

Date: 2026-11-13 · Branch: `arena/08f8f3c5-nyaymitra-2-0` · Starting commit: `72e5139`

**State in one line:** the importer, the diglot separator, the OCR checks, the report, backup/rollback and
the locale audit are built and tested on synthetic data. **No Constitution text has been imported**, because
the owner's English and Gujarati files are still only on the owner's device. Official text in the database:
English 0, Gujarati 0 (unchanged).

## 1. Importer implementation

| Piece | File | What it does |
|---|---|---|
| Reader, field mapping, validation, report | `backend/app/services/structured_import.py` | Reads a file into rows, identifies fields, validates every record, builds the data-quality report, writes accepted records |
| Diglot separation | `backend/app/services/diglot.py` | Splits a two-language PDF page by layout and keeps one script |
| Write + journal + rollback | `backend/app/services/ingest.py` (`write_articles`, `rollback_run`) | One write path shared with the existing document importer; every change is journaled |
| Schema | `backend/migrations/006_article_text_normalized.sql` (+ `.down.sql`) | `article_texts.body_normalized`, `normalization_json`; table `import_changes` |
| Command | `scripts/import_constitution_data.py` | `inspect` · `check` (dry run) · `apply` · `rollback` · `runs` |
| Locale audit | `scripts/audit_locales.py` → `docs/LOCALE_QUALITY_AUDIT.md` | Report only |

The existing `scripts/ingest_constitution.py` (whole-document import) still works and now uses the same write path.

### Field identification — no guessing

1. Header names are matched against known names in English, Gujarati and Hindi (`Article No`, `અનુચ્છેદ`, `લખાણ`, `ભાગ`, `પાનું`, …) and language-suffixed columns (`text_en`, `text_gu`, or nested `{"text": {"en": …, "gu": …}}`).
2. If a required field can only be identified by looking at the *content* (headers such as `c1`, `c2`), or two columns compete for one field, the tool **stops** with `MAPPING REQUIRED` (exit code 4) and prints a `mapping_template` plus a profile of every column. Nothing is imported.
3. The owner then either passes `--mapping file.json`, or — after reading the report — `--accept-inferred`.

Fields handled: article number, Part, Part title, Chapter, language, title, text, PDF pages (single column, range, or start/end columns), source, edition, extraction method, verification claim.

Article numbers: English, Gujarati and Devanagari digits; `21A`, `243ZA`, `243-za`, `Article 21A`, `અનુચ્છેદ ૩૨`, `021`, `Preamble`/`આમુખ`. A number with a non-Latin letter suffix (e.g. `૨૧ક`) is **rejected, not converted** — the letter mapping is not known to this tool.

### Record rules

| Rejection reason | Meaning |
|---|---|
| `missing_article_number`, `invalid_article_number` | no usable number |
| `empty_text`, `longer_than_20000_characters` | nothing to store / would be cut |
| `mixed_language_content`, `wrong_script` | English record with more than 1% non-Latin letters; other languages with more than 35% foreign letters |
| `ocr_unusable` | too many detached vowel signs / broken conjuncts to be readable |
| `damaged_text_not_declared_as_ocr` | text shows OCR-type damage but was declared `text_layer`/`manual_entry` |
| `duplicate_identical` | same number, same text (first copy kept) |
| `duplicate_conflicting_text` | same number, different text — **both** rejected, import blocked |
| `unknown_extraction_method`, `template_placeholder` | bad per-row method / sample template row |

Import is blocked (exit code 3) by: `mapping_not_confirmed`, `no_importable_records`, `more_than_20_percent_rejected`, `conflicting_duplicates`, `unknown_source_key`, `source_not_registered_as_official`, `extraction_method_not_declared`, and for diglot PDFs `mixed_language_content`, `uncertain_column_extraction`, `no_text_in_wanted_language`.

### Status on import (never upgraded automatically)

| Declared method | `content_status` | `verification_status` |
|---|---|---|
| `ocr` | `OCR_REVIEW_REQUIRED` | `requires_human_verification` |
| `text_layer` (source registered as official) | `OFFICIAL_SOURCE` | `requires_human_verification` |
| `manual_entry` (source registered as official) | `OFFICIAL_SOURCE` (existing rule; typed text is only as good as the typing — review it) | `requires_human_verification` |

A `verified` value inside a file is ignored and counted (`claimed_verified_ignored`). Nothing in this tool can set `VERIFIED` or `HUMAN_REVIEWED`.

Judgement call to confirm: a CSV/JSON the owner declares as `text_layer` of an official PDF is labelled `OFFICIAL_SOURCE` (still unverified). If the owner's article files were produced by OCR, they must be declared `--extraction-method ocr`.

### Safety

* `check` never writes. `apply` first takes an integrity-checked backup, then writes in **one transaction**.
* Re-running the same file writes nothing (content hash). Existing text is not replaced unless `--replace-existing`.
* Each language is a separate row per article; importing Gujarati cannot touch English and vice-versa.
* Owner-written summaries/explanations in `constitution_articles` are never modified (tested).
* `rollback RUN_ID` restores exactly what that run changed, from the `import_changes` journal; text edited after the run is left alone and reported as a conflict (`--force` overrides). A backup is taken before rollback too.
* Paths under a `legacy` folder (the quarantined Santali fragments) and compressed archives are refused.
* Full log of every run: `ingest_runs.report_json` (the complete quality report + backup path + counters).

## 2. Supported file formats

| Format | How records are found |
|---|---|
| `.csv`, `.tsv` (delimiter detected; UTF-8, UTF-8 BOM, UTF-16) | one row per article |
| `.json` | list of objects; object with one list inside (`{"articles": [...]}`); object keyed by article number; nested per-language objects |
| `.jsonl` / `.ndjson` | one object per line |
| folder of `.txt` / `.md` | one file per article; number taken from the file name (`article_021A.txt`) |
| `.txt` / `.md` whole-document export (incl. OCR export) | article headings parsed; page markers `--- Page 45 ---`, `[Page 45]`, `<<Page 45>>` or form-feed characters give page references |
| `.pdf` with text layer | per page; damaged Indic text layers are detected and blocked as before |
| `.pdf` diglot (`--diglot`) | layout separation, needs `pip install pymupdf` (tool-only, not a server dependency) |

Not supported: legacy non-Unicode Gujarati fonts/encodings (rejected with a clear message, not converted), `.docx`, `.xlsx`, images (OCR is not run by this tool), archives.

## 3. Templates

`data/templates/articles_template.csv`, `articles_template.json`, `mapping_template.json`. The rows are marked `PLACEHOLDER`; the importer refuses them, so a template can never be imported by accident. The owner's files do **not** need to follow the template — any recognisable headers work.

## 4. Data-quality report format

`check`/`apply` print Markdown and can write `--report file.json` and `--markdown file.md`. JSON keys:

| Key | Content |
|---|---|
| `file` | name, SHA-256, format, pages in file, page-marker type |
| `language`, `source_key`, `extraction_method`, `content_status_on_import` | what will be stored |
| `mapping` | status, message, field → column (+ basis), ambiguous and unmapped columns |
| `totals` | `records_discovered`, `records_for_this_language`, `skipped` (other languages), `import_ready`, `rejected`, `unique_article_numbers` |
| `numbering` | lowest, highest, lettered articles, `gaps_in_sequence`, `duplicate_article_numbers`, optional `expected_list` (`missing`, `not_expected`) |
| `parts` | Part-wise count of import-ready records |
| `ocr_quality` | grades (clean / minor / poor / unusable), warning counts, 15 worst records, normalised copies prepared |
| `coverage` | with/without page reference, page range, page-order breaks, with title / Part / Chapter |
| `rejections` | count per reason + row and article number of each rejected record |
| `database` | already stored identical / stored with different text / new |
| `diglot` | (diglot PDFs) page modes, uncertain pages, per-page detail, numbering cross-check with the other language |
| `blocking_reasons`, `ready_to_apply` | the gate |

One report covers one file and one language; run it once for English and once for Gujarati.

**About totals:** the tool has no built-in "correct" number of articles. Gaps are listed with the note that omitted and repealed articles leave gaps in the publication itself. To check completeness, give `--expected numbers.txt` (one number per line) taken from the contents pages of the edition actually used.

## 5. English diglot extraction — status

**Built and tested on synthetic page layouts. Not run on the real PDF** (the sandbox cannot download it; the layout of the real pages is therefore unknown).

Per page the separator classifies: `single_language`, `other_language`, `columns`, `rows`, `other_language_lines_removed` (e.g. a Hindi running header), `interleaved`, `empty`. Rules:

* a word containing any Devanagari letter is never emitted into the English text;
* a page whose two scripts cannot be divided by one clean line, or where Hindi words sit inside the English area, is marked **uncertain**;
* any uncertain page, or any Devanagari letter in the output, **blocks the import** of the whole file — the PDF stays where it is and the report lists the pages;
* page numbers are kept per page; article base numbers found in the English and the Hindi text are compared and differences listed.

Known weak points until tried on the real file: English words printed inside the Hindi column (and the reverse) on many pages will mark those pages uncertain; footnotes and marginal notes may sit outside the main column; reading order inside a column relies on word positions. If the real file turns out to be blocked, the fallback is a manual page-range/column mapping or using the English-only edition — not a relaxed threshold.

## 6. Gujarati OCR validation — status

**Built and tested on synthetic samples. Not run on the owner's OCR output** (not available).

Checked per record: vowel signs detached from their consonant, broken conjuncts (virama followed by a space), stray combining marks, replacement characters, share of Gujarati letters, very short text, article-number validity, duplicates, missing text, page references (missing, out of order). Graded clean / minor / poor / unusable.

* The OCR text is stored **exactly as supplied** in `body`.
* With `--normalize-ocr` a cleaned copy (Unicode NFC, vowel signs re-attached, repeated spaces collapsed) goes to the separate column `body_normalized`, with the list of changes in `normalization_json`. Setting both to NULL undoes it. The API and the app still show the original; nothing reads the normalised copy yet.
* Wrong characters chosen by the OCR engine cannot be detected or repaired by rules — only by a reader.
* Every OCR record is `OCR_REVIEW_REQUIRED` + `requires_human_verification`.

Lead from the official Gujarati PDF (search snippet only): its text layer shows detached vowel signs ("ભારતન ું સુંવિધાન"), so a text-layer extraction of that PDF would be graded poor and must go through review like OCR.

## 7. Locale audit

`python scripts/audit_locales.py` → `docs/LOCALE_QUALITY_AUDIT.md`. Result: 23 catalogues, 0 structural errors (valid UTF-8/NFC, no broken marks, no placeholder mismatches, no empty values, direction metadata consistent; RTL = ks, sd, ur). English 157/157 strings; Gujarati 153/157 (4 shown in English); the other 21 languages have 4–12 strings each and show English for the rest. All 21 remain `MACHINE_TRANSLATED`, unreviewed, and labelled so in the app. No strings were added or changed. Correctness of the translations and visual RTL rendering are not something this audit can judge.

## 8. Test results (local, 2026-11-13)

| Suite | Result |
|---|---|
| `pytest` (backend) | **443 passed** (389 before + 54 new in `backend/tests/test_phase4_import.py`) |
| `pytest tests` | 15 passed |
| `scripts/e2e_activation.mjs` (jsdom simulation, same origin) | 43/43 |
| `scripts/smoke_web.mjs` (jsdom simulation) | OK |

New tests cover: CSV, JSON (nested, keyed, list), JSONL, TSV, folder, TXT with page markers; Gujarati/Devanagari numerals and suffixes; mapping report for unrecognisable headers; Hindi-in-English rejection; language isolation; OCR observation, separate normalised copy, original preserved; duplicates; idempotency; no overwrite of summaries; rollback and rollback conflict; failed import leaves nothing; missing numbers and expected list; Part/Chapter mapping; provenance fields; self-declared "verified" ignored; legacy and template refusal; diglot columns/rows/facing pages/interleaved/header; migration 006 down/up; CLI check → apply → rollback; locale audit.

Not tested: any real Constitution file; the real diglot PDF; real OCR output; a PDF containing Devanagari or Gujarati (no Indic fonts in the sandbox — the one real-PDF test is English-only and is skipped where PyMuPDF is not installed, as in CI).

## 9. Getting the data from the tablet (Termux)

```bash
# one-time
pkg update && pkg install -y git python gh
termux-setup-storage
gh auth login
git clone https://github.com/dhundhwana-arch/Nyaymitra-2.0.git ~/Nyaymitra-2.0
cd ~/Nyaymitra-2.0 && git checkout arena/08f8f3c5-nyaymitra-2-0

# 1. find what exists (reads only; writes one JSON file)
python scripts/inventory_local_data.py ~/NYAYMITRA-AI ~/storage/shared --out ~/local-data-inventory.json

# 2. look at a file before sending it (no database needed, nothing is changed)
python scripts/import_constitution_data.py inspect /path/to/gujarati_articles.json --language gu
python scripts/import_constitution_data.py inspect /path/to/english_articles.csv  --language en

# 3. pack the article files + the inventory (replace the paths with the real ones)
mkdir -p ~/nyaymitra-transfer
cp ~/local-data-inventory.json /path/to/english_articles.* /path/to/gujarati_articles.* ~/nyaymitra-transfer/
cd ~ && tar -czf nyaymitra-data.tar.gz nyaymitra-transfer && sha256sum nyaymitra-data.tar.gz

# 4. send it — private draft release (keeps large data out of git history)
cd ~/Nyaymitra-2.0
gh release create data-transfer-1 ~/nyaymitra-data.tar.gz --draft --title "Owner data transfer" --notes "sha256: <paste>"
```

Alternative to step 4: attach `nyaymitra-data.tar.gz` (or the files) to the chat. The paths in steps 2–3 are placeholders: the real file names are not known. Step 2 needs only Python's standard library plus the repository; if it reports an import error, run `pip install -r backend/requirements.txt` first. PDFs need not be sent if the article-wise files exist; send the PDF's file name, size and SHA-256 instead (the inventory records them).

After the files arrive:

```bash
python scripts/import_constitution_data.py check FILE --language gu --source-key <key> --extraction-method ocr \
       --normalize-ocr --report gu-report.json --markdown gu-report.md
python scripts/import_constitution_data.py apply FILE --language gu --source-key <key> --extraction-method ocr --normalize-ocr
python scripts/import_constitution_data.py rollback <RUN_ID>      # if needed
```

## 10. Remaining blockers

1. **The data.** No English or Gujarati article file, OCR output or inventory has been received; GitHub has none. Everything above is verified on synthetic data only.
2. **Source registration.** The exact editions (title page, "as on" date, file SHA-256) must be registered in `legal_sources` before import; the right `--source-key` depends on which PDFs the owner's data came from.
3. **Diglot PDF** cannot be fetched from the sandbox; real layout untested.
4. **How the owner's files were made** (OCR vs text layer vs typed) decides the status label; only the owner knows.
5. **Gujarati letter suffixes** in article numbers (if the Gujarati edition prints e.g. `૨૧ક`) need a mapping confirmed from the edition; currently rejected.
6. **Human verification** of imported text: no reviewer workflow exists beyond the status fields; nothing can become `VERIFIED` without one.
7. **Normalised OCR copy** is stored but not shown anywhere; whether to display it is an owner decision.
8. Unchanged from before: deployed URLs and deploy approval; decision on the two earlier unapproved merges into this branch (`d6bd5dc`, `e07747a`) and what becomes `main`; native-speaker review of 21 machine-translated catalogues.

Nothing was deployed. `main` was not modified. No branch was merged, deleted or force-pushed in this phase.

> Update 2026-11-14: the transfer procedure in §9 is superseded by `docs/PHASE4A_DATA_RECOVERY_GUIDE.md` (inventory tool 2.0 with Markdown report, privacy rules and a verified transfer package).
