# Phase 3B — Constitution Data Acquisition Report

**Generated:** 2026-11-12  
**Branch:** `arena/812d6894-nyaymitra-2-0`  
**Environment:** Sandbox (no outbound HTTPS to government domains — see §B)

---

## 1. Official Documents Acquired

| Item | Status | Notes |
|------|--------|-------|
| English Constitution text | **Not acquired** | No network access to India Code / Legislative Dept (SSL handshake failure on `indiacode.nic.in` and `legislative.gov.in`) |
| Gujarati Constitution text | **Not acquired** | Same network limitation; no Gujarati edition source located in `data/raw/` |
| Source manifest | Present | `data/seed/sources.json` — `india-code-constitution` entry exists but `retrieved_on` is `null` |

**Zero documents were downloaded.** No text was extracted. No files were placed in `data/raw/`.

---

## 2. Official Sources Identified (verification required)

Per `data/seed/sources.json`, the official English Constitution source is:

| Field | Value |
|-------|-------|
| `source_key` | `india-code-constitution` |
| Title | The Constitution of India (as amended up to the 106th Amendment Act, 2023) |
| Publisher | Legislative Department, Ministry of Law and Justice, Government of India |
| Source type | official |
| URL | `https://www.indiacode.nic.in/handle/123456789/15240` |
| Document ref | India Code — Constitution of India (full text, English) |
| Published on | not recorded |
| Retrieved on | **null** (never retrieved) |
| Licence note | Government of India publication; reproduced with attribution |

No separate Gujarati Constitution source entry exists in `sources.json`. The Gujarati edition (Legislative Department, Gujarati edition) referenced in `data/raw/README.md` as `samvidhan-gu.pdf`/`.txt` has no official URL recorded in the manifest.

### Network verification results

```
$ curl -sv --max-time 15 https://www.indiacode.nic.in/
* Connected to www.indiacode.nic.in (23.53.122.69) port 443 (#0)
* TLSv1.3 (OUT), TLS handshake, Client hello (1)
* OpenSSL SSL_connect: SSL_ERROR_SYSCALL in connection to www.indiacode.nic.in:443

$ curl -sv --max-time 15 https://legislative.gov.in/
* Connected to legislative.gov.in (164.100.220.71) port 443 (#0)
* TLSv1.3 (OUT), TLS handshake, Client hello (1)
* OpenSSL SSL_connect: SSL_ERROR_SYSCALL in connection to legislative.gov.in:443
```

Both government hosts accept TCP connections but the TLS handshake fails. **No HTTPS content can be retrieved in this environment.** This is an environment limitation, not a source-authenticity problem: the URLs are recorded as the correct official locations, but the documents cannot be fetched from here.

---

## 3. Required Source Manifest (data/raw/)

Per `data/raw/README.md`, the ingestion pipeline expects:

| File (in `data/raw/`) | Purpose | Language | Source | Status |
|----------------------|---------|----------|--------|--------|
| `constitution-of-india-en.pdf` or `.txt` | Fill `constitution_articles.text_en` | en | India Code / Legislative Dept | **Missing** |
| `samvidhan-gu.pdf` or `.txt` | Fill `constitution_articles.text_gu` | gu | Legislative Dept (Gujarati edition) | **Missing** |

The directory currently contains only `README.md`. No Constitution PDF or text files are present.

### Required SHA-256 checksums

When the project owner supplies the files, checksums must be recorded here:

| File | SHA-256 (to be recorded on receipt) | Retrieved on | Page count |
|------|--------------------------------------|--------------|------------|
| `constitution-of-india-en.pdf` / `.txt` | *(pending)* | *(pending)* | *(pending)* |
| `samvidhan-gu.pdf` / `.txt` | *(pending)* | *(pending)* | *(pending)* |

---

## 4. Text Extracted

**None.** No source documents are present, so no extraction has been performed.

The ingestion pipeline (`scripts/ingest_constitution.py`) supports:
- `.pdf` — via `pypdf.PdfReader` (requires a text layer; scanned PDFs report `low_text_quality` and zero articles)
- `.txt` / `.md` — plain text, single page

The parser expects the India Code heading style: `14. Equality before law.—The State shall not deny …`

Extraction quality signals recorded by the pipeline:
- OCR/text confidence (replacement characters + control noise ratio)
- Page boundaries (each article records `page_start` / `page_end`)
- Article number validity (1–500, optional letter suffix)
- Duplicate detection
- Missing number reporting (gaps never invented)
- Short-body and boundary-issue heuristics

---

## 5. Text Imported into the Database

**Zero articles imported.** Current database state:

| Table | Count | Source text present? | Human-verified? |
|-------|-------|---------------------|-----------------|
| `constitution_articles` | 9 | No (all `owner_authored_summary`) | No (all `requires_human_verification`) |
| `legal_sources` | 15 | N/A | N/A |
| `ingest_runs` | 0 | N/A | N/A |

The 9 existing articles carry `text_status = owner_authored_summary` and `verification_status = requires_human_verification`. They are project-owner summaries, **not** official constitutional text.

Coverage report confirms: 9 / 395 articles loaded (2.3%), 0 with authoritative source text, 0 human-verified, 388 missing numbers.

---

## 6. Text Awaiting Human Verification

All 9 currently loaded articles await human verification. When official documents are acquired and ingested:

- Every imported row receives `text_status = verified_source_text` (text came from the document)
- Every imported row receives `verification_status = requires_human_verification` (not checked by a legal professional)
- Rows already verified by a human are never overwritten
- A named reviewer must sign off each article in the admin console before it is described as verified law

---

## 7. Recommended Next Steps (project owner)

1. **Obtain the documents** from an official source:
   - English: download from `https://www.indiacode.nic.in/handle/123456789/15240` (India Code — Constitution of India)
   - Gujarati: obtain the Legislative Department Gujarati edition (`samvidhan-gu.pdf`/`.txt`) — no URL recorded in manifest yet; add one after confirming the official publication location
2. **Place files in `data/raw/`** with the exact filenames from `data/raw/README.md`
3. **Record SHA-256 checksums** for each file (see §3 table)
4. **Add the Gujarati source entry** to `data/seed/sources.json` (no Gujarati Constitution source currently exists)
5. **Run the ingestion pipeline in dry-run mode:**
   ```bash
   python scripts/ingest_constitution.py \
       --file data/raw/constitution-of-india-en.pdf \
       --source-key india-code-constitution --language en
   python scripts/ingest_constitution.py \
       --file data/raw/samvidhan-gu.pdf \
       --source-key <gujarati-source-key> --language gu
   ```
6. **Review the dry-run report** for duplicates, missing numbers, short bodies, boundary issues, and OCR quality
7. **Apply only after review:**
   ```bash
   python scripts/ingest_constitution.py --file ... --apply --backup
   ```
8. **Run coverage report:**
   ```bash
   python scripts/constitution_coverage.py --format both --out reports/coverage
   ```
9. **Human review:** a legal professional verifies each imported article in the admin console

---

## 8. Git Safety Notes

- No files in `data/raw/` were created or modified (directory is git-ignored)
- No deployment was performed
- No merge into any production branch
- The legal database is **not** claimed to be complete
- Working tree changes are limited to: new test file + acquisition report document

---

## Deliverables Status

| Deliverable | Status | Location |
|-------------|--------|----------|
| Official source acquisition report | Complete (this document) | `docs/PHASE_3B_ACQUISITION_REPORT.md` |
| Source manifest | Present (needs Gujarati entry added) | `data/seed/sources.json` |
| English/Gujarati extraction coverage report | Not possible (no documents acquired) | N/A |
| Article mapping and exception report | Not possible (no documents acquired) | N/A |
| Test results | 19 ingestion tests pass | `backend/tests/test_ingest_pipeline.py` |
| Remaining human-verification tasks | Documented (§6) | This document |
