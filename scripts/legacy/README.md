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

---

## Reconciliation addendum — 2026-11-12 (`arena/2497125a-nyaymitra-2-0`)

When `main` (`53df9ea`) was reconciled into the canonical branch, every file from the old
prototype that had no archived counterpart was restored here **byte-for-byte** (SHA-256 verified
against `origin/main`). Nothing from `main` was discarded.

| Restored to | Source on `main` | Why it is here |
|---|---|---|
| `scripts/legacy/database.py` | `backend/database.py` | The superseded schema (`title_gu`, `description_gu`, `remedy_gu`) that **contradicted** the committed database. Kept as evidence for `docs/REPOSITORY_AUDIT.md` §5.2. Never imported by the application. |
| `frontend/legacy/data/library_fix.js` | `frontend/library_fix.js` | The 2,125-row Santhali-derived dataset as it was actually shipped (4.9 MB). The same rows are preserved as evidence in `data/legacy/*.jsonl.gz` and mirrored into the admin-only `legacy_import_chunks` table. **Not served.** |
| `frontend/legacy/data/interactive_library.js` | `frontend/interactive_library.js` | 470 placeholder records, every one `"Article N/A"`. Zero information value; kept only so the reconciliation loses nothing. **Not served.** |

`frontend/index_v2.html` was **not** restored: it is byte-identical to `frontend/legacy/index.html`
(md5 `95b0c137047691502d26a0d363219198`), so restoring it would preserve a duplicate, not a file.

### Containment

Only `web/` is mounted and served by `backend/app/main.py` (`_mount_web`). Nothing under
`frontend/legacy/` or `scripts/legacy/` is reachable over HTTP, imported by application code, or
collected by CI. Verified:

```
grep -rn "library_fix|interactive_library|legacy/data|app_core" web/ backend/app/   ->  no matches
```

The quarantine remains intact and unmodified: `data/legacy/constitution_articles_legacy_2026-11-07.jsonl.gz`
sha256 `b59f00b8c10f7d6845c4e2e4d97dd493c8c02b99ab6edd43a38ea022e5a0107f`, 2,125 records.
