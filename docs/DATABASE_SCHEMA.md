# Database schema

SQLite 3 (WAL, `foreign_keys=ON`, `busy_timeout=15000`). Three migrations ship today:
`001_initial`, `002_complaint_idempotency` (`client_request_id`, `fingerprint`, unique index) and
`003_article_source_pages` (`source_pages`). Schema is created by versioned SQL files
in `backend/migrations/`, applied in lexical order and recorded with a SHA-256 checksum in
`schema_migrations`. Each has a `NNN_name.down.sql` sibling used by
`python scripts/init_db.py --rollback-to N`.

```bash
python scripts/init_db.py --info                    # migrate + seed, print counts
python scripts/init_db.py --backup --migrate        # verified backup, then upgrade
python scripts/init_db.py --rollback-to 0           # drop everything from 001 (destructive)
```

File permissions are forced to `0600` for the database and `0700` for its directory on every
connect, because the file holds personal data (complaints, contact details, document hashes).

## Tables (15 + 1 FTS5 virtual table)

| Table | Rows after seeding | Purpose |
|---|---:|---|
| `schema_migrations` | 1 | Applied migration name, checksum, timestamp |
| `legal_sources` | 15 | Provenance spine: publisher, URL/document ref, retrieved_on, licence note |
| `constitution_articles` | 9 | Article identity, text (en/gu), explanation (en/gu), status, verification |
| `article_sources` | 9 | Many-to-many article ↔ source with locator and note |
| `departments` | 11 | Official channels: name/purpose (en/gu), helpline, portal, verification |
| `triage_guides` | 5 | Category → summary/steps/documents (en/gu) + default department |
| `complaints` | 0 | Citizen complaint, deterministic summary, status, token **hash** only |
| `documents` | 0 | Upload metadata, SHA-256, extraction status, owner token hash, FK to complaint |
| `feedback` | 0 | Citizen reports about an answer/article/department |
| `query_logs` | 0 | AI question (redacted) + hash, language, category, provider, latency, status |
| `ai_answers` | 0 | Answer text, provider, grounded/degraded, citations JSON, warnings |
| `error_log` | 0 | Request id, method, path, status, error type, redacted message |
| `audit_log` | 0 | Actor, action, target, detail, hashed IP for admin mutations |
| `ingest_runs` | 0 | Ingestion report: found/written, duplicates, missing numbers, JSON report |
| `legacy_import_chunks` | 2125 | Quarantined legacy rows (text + the removed fabricated "remedy"), audit only |
| `constitution_fts` | 9 | FTS5 virtual table over article labels/titles/text/explanations |

## Key columns

### `constitution_articles`

| Column | Notes |
|---|---|
| `article_key` | `article-14`, unique |
| `article_no` | `14`, `39A`, `21A` — unique per part (`uq_articles_no_part`) |
| `text_en`, `text_gu` | **Authoritative text only.** `NULL` until an official document is ingested |
| `citizen_explanation_en/_gu` | Plain-language explanation; never loaded into the text columns |
| `text_status` | `verified_source_text` \| `owner_authored_summary` \| `not_available` |
| `verification_status` | `verified` \| `requires_human_verification` \| `unverified` \| `outdated` |
| `checked_by`, `last_checked_at` | Required before `verified` is accepted |
| `source_id`, `source_locator`, `source_url` | Provenance for this row |
| `source_pages` | Page range in the supplied document (`12`, `12-14`; `1` for a text file) |

The separation of `text_*` from `citizen_explanation_*` is the schema-level guarantee that a
paraphrase can never be served as the article. `scripts/ingest_constitution.py` writes only
`text_*`; the API only falls back to `citizen_explanation_*` when `text_*` is `NULL`, and says so.

### `complaints` / `documents`

| Column | Notes |
|---|---|
| `reference` | `NYM-XXXXXX`, unique, derived from a random token, not sequential |
| `access_token_hash` | SHA-256 hex — the token itself is shown once and never stored |
| `consent_given` | Must be true; enforced by the API |
| `client_request_id` | Optional idempotency key; partial unique index prevents duplicates |
| `fingerprint` | SHA-256 of the substantive fields, used to detect an identical retry without a key |
| `documents.owner_token_hash` | Same pattern for uploads |
| `documents.extraction_status` | `extracted` \| `ocr_unavailable` \| `too_large` \| `extraction_failed` |
| `documents.complaint_id` | FK with `ON DELETE SET NULL`; attaching requires the owner token |

### `legacy_import_chunks`

Preserved, never served. 2,125 rows from the old database: 1,732 unlabelled PDF chunks, 1,905 in
Santhali (Ol Chiki) rather than Gujarati, and the fabricated `remedy_text` that was previously shown
as law. Kept for audit and honesty; the admin endpoint labels it as quarantined.

## Indexes

`idx_articles_no`, `idx_articles_part`, `idx_articles_verification`, `uq_articles_no_part`,
`idx_departments_key` (implicit unique), `idx_complaints_status`, `idx_complaints_created`,
`uq_complaints_client_request` (partial unique on `client_request_id`),
`idx_complaints_fingerprint`,
`idx_documents_complaint`, `idx_query_logs_created`, `idx_error_at`, `idx_audit_at`,
`idx_legacy_no`, plus FTS5's own structures.

## FTS5

`constitution_fts` uses the default `unicode61` tokenizer; `content='constitution_articles'` with
`content_rowid='id'` and insert/update/delete triggers. Gujarati is whitespace-tokenised, so the
query builder (`services/textsearch.py`) adds stopwords, AND-first matching and an overlap
threshold. Ranking uses `bm25(constitution_fts, 8, 5, 1, 1)` (label > titles > text > explanation).

## Retention and privacy

| Data | Policy |
|---|---|
| Complaints, documents | Personal data. Access-token hashes only; no listing without a token |
| Retention enforcement | `scripts/purge_data.py` (dry-run default) deletes complaints/documents/query logs older than `NYAYMITRA_PII_RETENTION_DAYS`; files are removed and the purge is audited |
| `query_logs` | Question text redacted on write (phone, email, Aadhaar-like numbers, tokens), plus a SHA-256 hash for dedup |
| `error_log` | Redacted message; no request bodies |
| `legacy_import_chunks` | Quarantined, admin-only, retained for audit |

## Backup and restore

```bash
python scripts/backup_db.py                       # sqlite3_backup + PRAGMA integrity_check
python scripts/backup_db.py --list
python scripts/backup_db.py --restore backups/nyaymitra-20261107T190000Z.db
```

Backups are consistency-checked and written with `0600` permissions. Restore copies the backup over
`NYAYMITRA_DB_PATH` after checking integrity, so a corrupt file cannot replace a working database.

## Migrations in practice

```bash
python scripts/init_db.py                      # apply pending migrations, then seed
python scripts/init_db.py --no-seed            # schema only
python scripts/init_db.py --rollback-to 0      # rollback everything
python scripts/init_db.py --info               # counts per table
```

Seeding is idempotent and **never overwrites a human decision**: an article marked `verified` with a
`checked_by` value survives re-seeding unchanged (test:
`test_seed_is_idempotent_and_preserves_human_decisions`).


---

## Update 2026-11-12 — multilingual milestone

Migration `005_article_texts.sql` adds `article_texts` — one row per (article, language) with title, body, source, pages, edition, `extraction_method`, `content_status` (`OFFICIAL_SOURCE`, `OCR_REVIEW_REQUIRED`, `MACHINE_TRANSLATED`, `HUMAN_REVIEWED`, `VERIFIED`), `verification_status` and SHA-256. No existing table is altered. Reversible with `005_article_texts.down.sql` (back up first). Details: [MULTILINGUAL_IMPLEMENTATION_REPORT.md](MULTILINGUAL_IMPLEMENTATION_REPORT.md) §4.

## Update 2026-11-13 — migration 006 (Phase 4)

`006_article_text_normalized.sql` (reversible with its `.down.sql`):

* `article_texts.body_normalized` — optional cleaned copy of OCR text. `body` always holds the text exactly as supplied.
* `article_texts.normalization_json` — list of the clean-up steps applied. Setting both columns to NULL undoes normalisation.
* `import_changes` — journal of every row an import run created or replaced (`run_id`, `article_id`, `article_no`, `language`, `created_article`, `prev_article_json`, `prev_text_json`, `new_sha256`). Used by `scripts/import_constitution_data.py rollback RUN_ID`.
* `ingest_runs.status` now also takes `running` and `rolled_back`.

Migrations are now 001–006.
