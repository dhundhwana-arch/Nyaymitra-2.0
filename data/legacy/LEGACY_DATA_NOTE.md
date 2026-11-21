# Legacy data archive (quarantined)

**Created:** 2026-11-07T18:34:14.369315+00:00 by `scripts/export_legacy.py`

## What this is

`constitution_articles_legacy_2026-11-07.jsonl.gz` — gzip-compressed JSON Lines, one record per row of the legacy
`constitution_articles` table (`2125` records), plus any `query_logs` /
`saved_drafts` rows (none existed at export time).

- **Source file:** `backend/justice_access.db`, sha256 `da5ff06fdddb4b4912b1cc25e5b09cda5b59e65fc4dea649ad30f0f91297a53c`
- **Archive sha256:** `b59f00b8c10f7d6845c4e2e4d97dd493c8c02b99ab6edd43a38ea022e5a0107f`
- **Rows exported:** 2125
- **Dominant script per row:** {'latin': 220, 'ol_chiki': 1905}

## Why it is quarantined (not served, not deleted)

`docs/REPOSITORY_AUDIT.md` §6 documents the finding in full. In short:

1. 1 732 of 2 125 rows are labelled `Section Chunk N` — unlabelled PDF slices, not articles.
2. Article numbers are unreliable (`Article 1996`, `Article 3359`, `Article 243` repeated 26×).
3. 1 905 rows are in Ol Chiki (Santhali); **no Gujarati rows exist at all**, contradicting the
   project's language claim.
4. The `remedy` column contains exactly two generated strings repeated across every row. That is
   fabricated legal interpretation and must never be shown to a citizen as law.

The underlying Constitution text is genuine Santhali-language material, so it is preserved here
and mirrored into the `legacy_import_chunks` table (admin-only, never returned by the public API).

## How to re-use it

After the owner supplies the **official** source documents (see `data/raw/README.md`), re-run
`scripts/ingest_constitution.py`. Do not load this archive into `constitution_articles`; it is
evidence, not a corpus.
