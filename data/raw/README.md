# Supplied legal source documents (`data/raw/`)

This directory is where the **project owner** places official source documents for ingestion.
Its contents are git-ignored on purpose: the files are large, may be copyrighted, and must not
be republished from this repository.

## What is needed

| File | Purpose | Where to obtain it |
|---|---|---|
| `constitution-of-india-en.pdf` (or `.txt`) | Fill `constitution_articles.text_en` with the authoritative English text | India Code / Legislative Department, Ministry of Law and Justice |
| `samvidhan-gu.pdf` (or `.txt`) | Fill `constitution_articles.text_gu` with the official Gujarati text | Legislative Department (Gujarati edition) |

> **Nothing in this repository is a substitute for these files.** The shipped seed contains only
> human-written *explanations* marked `owner_authored_summary` + `requires_human_verification`.
> Zero articles currently carry `verified_source_text`.

## How to ingest

```bash
# 1. Inspect what the parser finds (dry run — writes nothing)
python scripts/ingest_constitution.py \
    --file data/raw/constitution-of-india-en.pdf \
    --source-key india-code-constitution --language en

# 2. Import with a verified backup first
python scripts/ingest_constitution.py \
    --file data/raw/constitution-of-india-en.pdf \
    --source-key india-code-constitution --language en --apply --backup

# 3. Check the report: duplicates, missing numbers, short bodies, OCR confidence
python scripts/ingest_constitution.py --file ... --report reports/ingest-en.json
```

The parser expects the India Code heading style `14. Equality before law.—The State shall …`.
Duplicates are reported (only the first occurrence is kept), missing numbers are reported
(never filled in), and short bodies are stored as-is and flagged — text is never invented.

## Scanned PDFs

A PDF without a text layer cannot be read without OCR. The ingester will report
`low_text_quality` and zero articles rather than guessing. Install an OCR tool and run it
yourself first, then ingest the resulting text file.
