#!/usr/bin/env python3
"""Export the legacy SQLite database and generated frontend artefacts before migration.

Nothing is deleted by this script: it only *reads* legacy artefacts and writes a
compressed archive + provenance note into ``data/legacy/``.

Usage:
    python scripts/export_legacy.py [--db backend/justice_access.db]
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "backend" / "justice_access.db"
OUT_DIR = REPO_ROOT / "data" / "legacy"
STAMP = "2026-11-07"


def dominant_script(text: str) -> str:
    ol = sum(1 for ch in text if 0x1C50 <= ord(ch) <= 0x1C7F)
    gu = sum(1 for ch in text if 0x0A80 <= ord(ch) <= 0x0AFF)
    latin = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    best = max((("ol_chiki", ol), ("gujarati", gu), ("latin", latin)), key=lambda p: p[1])
    return best[0] if best[1] else "none"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive legacy NYAYMITRA data")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"[export_legacy] no database at {db_path} — nothing to archive (already archived?)")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    rows_exported = 0
    script_counts: Counter[str] = Counter()
    archive = OUT_DIR / f"constitution_articles_legacy_{STAMP}.jsonl.gz"

    with gzip.open(archive, "wt", encoding="utf-8") as out:
        if "constitution_articles" in tables:
            cols = [c[1] for c in conn.execute("PRAGMA table_info(constitution_articles)")]
            for row in conn.execute("SELECT * FROM constitution_articles ORDER BY id"):
                record = dict(zip(cols, tuple(row)))
                text = record.get("description_en") or record.get("description_gu") or ""
                record["_script"] = dominant_script(text)
                record["_provenance"] = {
                    "origin": "backend/justice_access.db (legacy, quarantined)",
                    "reason": (
                        "Rows were produced by a regex over ~1000-char chunks of the Santhali "
                        "(Ol Chiki) edition of the Constitution; article numbers are unreliable "
                        "and the 'remedy' field was generated, not sourced."
                    ),
                    "archived_at": datetime.now(timezone.utc).isoformat(),
                    "audit": "docs/REPOSITORY_AUDIT.md section 6",
                }
                script_counts[record["_script"]] += 1
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                rows_exported += 1

        for table in ("query_logs", "saved_drafts"):
            if table in tables:
                cols = [c[1] for c in conn.execute(f"PRAGMA table_info({table})")]
                for row in conn.execute(f"SELECT * FROM {table}"):
                    out.write(json.dumps(
                        {"_table": table, **dict(zip(cols, tuple(row)))}, ensure_ascii=False) + "\n")

    conn.close()


    note = OUT_DIR / "LEGACY_DATA_NOTE.md"
    note.write_text(
        f"""# Legacy data archive (quarantined)

**Created:** {datetime.now(timezone.utc).isoformat()} by `scripts/export_legacy.py`

## What this is

`{archive.name}` — gzip-compressed JSON Lines, one record per row of the legacy
`constitution_articles` table (`{rows_exported}` records), plus any `query_logs` /
`saved_drafts` rows (none existed at export time).

- **Source file:** `backend/justice_access.db`, sha256 `{sha256_file(db_path)}`
- **Archive sha256:** `{sha256_file(archive)}`
- **Rows exported:** {rows_exported}
- **Dominant script per row:** {dict(script_counts)}

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
""",
        encoding="utf-8",
    )

    print(f"[export_legacy] exported {rows_exported} rows -> {archive}")
    print(f"[export_legacy] note -> {note}")
    print(f"[export_legacy] scripts: {dict(script_counts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
