# Legacy one-shot migration scripts (do not run)

These are the scripts that produced the quarantined data described in
`docs/REPOSITORY_AUDIT.md` §6. They are kept as evidence and as a record of the intended
pipeline, **not** as supported tooling.

They are excluded from the served application and from CI.

| Script | Problem |
|---|---|
| `long_deep_migration.py` | Regex over PDF chunks → meaningless article numbers; writes two invented `remedy` strings; **ends with `git push origin main`** (removed from the supported path). |
| `setup_full_library.py` | Hard-coded `BASE_DIR = "/data/data/com.termux/files/home/Nyaymitra-2.0"`; reads `backend/article_audit_471.csv`, which does not exist in the repository. |
| `integrate_real_engine.py` | Depends on `~/NYAYMITRA-AI/backend/modules/constitution_library.py`, which is unavailable; injects `<script>` tags into HTML files. |
| `extract_real_library.py` | Same missing dependency; writes a 4.8 MB JS blob into the frontend. |

## Superseded by

| New script | Purpose |
|---|---|
| `scripts/ingest_constitution.py` | Parse an **official** source document, validate every article, detect duplicates/missing numbers, record OCR confidence, write a JSON report. Refuses to invent text. |
| `scripts/init_db.py` | Apply migrations and load the curated seed idempotently. |
| `scripts/export_legacy.py` | Archive legacy data with provenance (already run; see `data/legacy/`). |
| `scripts/backup_db.py` | Safe `sqlite3 .backup` with verification. |

## Why the old approach failed (short version)

The importer chunked the PDF into ~1 000-character slices, applied a single regular expression to
the chunk stream, and stored the capture groups directly. That produces article numbers taken from
page numbers and amendment footnotes (`Article 1996`, `Article 3359`), titles sliced mid-word,
the same text repeated at 1 000-character offsets, and no way to tell which row is a real article.
Validation (does the number exist? does the text repeat? is the script even the target language?)
was absent.
