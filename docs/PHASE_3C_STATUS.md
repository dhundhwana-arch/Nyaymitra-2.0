# Phase 3C — Official Source Integration: status

**Overall: NOT COMPLETE.** The pipeline and tests exist; the official PDFs could not be
downloaded from the build sandbox, so nothing has been extracted or imported.

## What happened (2026-11-12 UTC)

| Stage | Status |
|---|---|
| Acquire official PDFs | **FAILED** – both URLs, TLS connection closed before any HTTP response |
| SHA-256 / page counts / PDF metadata | not available (no file) |
| Gujarati text-layer inspection | not done (no file) |
| English / Gujarati article extraction | not done (no file) |
| Coverage / duplicate / missing / OCR reports | generated, but empty – see `data/reports/phase3c-report.json` |
| Cross-language numbering comparison | not run |
| Dry-run import | ran: 0 rows planned, 0 written |
| Applied import | not run; `--apply` was attempted once and was refused by the gates |

Exact errors:

    curl: (35) OpenSSL SSL_connect: SSL_ERROR_SYSCALL in connection to www.legislative.gov.in:443
    URLError: <urlopen error TLS/SSL connection has been closed (EOF) (_ssl.c:992)>

The sandbox only allows outbound traffic to GitHub, npm and PyPI, so this says nothing about
whether the URLs are valid. They are **unverified**.

## To finish, on a machine that can reach legislative.gov.in

    python -m venv .venv && .venv/bin/pip install -r requirements-ingestion.txt
    .venv/bin/python -m ingestion.pipeline acquire     # downloads, fills data/sources/manifest.json
    .venv/bin/python -m ingestion.pipeline run         # reports + dry-run only
    # review data/reports/*, then and only then:
    .venv/bin/python -m ingestion.pipeline run --apply # refused unless every gate passes

## Things a human must check

1. **Edition claims in the manifest are unverified** (`claims_verified_against_document: false`).
   Open each PDF and confirm the edition line and the "amendments up to" statement. Note the URL
   paths are dated 2025/08 and 2025/07, while the claimed editions are September 2026 and
   February 2026 – confirm against the title pages.
2. **The heading parser has never seen the real PDFs.** It was built against the usual
   `14. Heading.—Body` layout and synthetic fixtures. The Gujarati layout (digits, suffix
   letters, separator, the "પહેલી અનુસૂચિ" schedule marker) is an assumption. Expect to tune
   `ingestion/extract.py` once the files are available; until then gates fail closed.
3. **`text_raw` is a raw slice of the PDF text layer**, so it will include page headers and
   footnotes that fall inside an article's span. It is source material for review, not clean text.
4. **Omitted/repealed article numbers** will show as "missing". They block import until a person
   lists them in `data/sources/accepted_exceptions.json` with `reviewed_by` and `reviewed_at`.
5. **Suffixed articles (21A, 243ZA, …) are never paired across languages automatically.** They
   are listed under `suffixed_articles_needing_human_mapping`.
6. Every imported row is `requires_human_verification`; no code sets any other value.

## Pre-existing data issue found during inspection (not changed)

`backend/justice_access.db` → `constitution_articles` holds 2,125 rows, of which 1,732 are
`Section Chunk N` page fragments, and the column `description_en` contains Santali (Ol Chiki
script) text from a bilingual "As on November, 2025" edition, not English-only text. The table
also has no Gujarati columns although `backend/database.py` expects them. This table was left
untouched; official text is designed to go to a separate `official_constitution_articles` table.

---
**Correction (Phase 3D, 2026-11-12):** the Santali data issue above was *not* newly found in
Phase 3C. It was documented and quarantined on `arena/812d6894-nyaymitra-2-0` on 2026-11-07.
Phase 3C was built on a branch cut from `main`, which does not contain that work. See
`docs/PHASE_3D_DATABASE_AUDIT.md`.
