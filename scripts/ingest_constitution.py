#!/usr/bin/env python3
"""Ingest an official Constitution document into the article table.

The project owner must supply the source file (see data/raw/README.md). This script
validates before writing and is dry-run by default.

    # inspect first (writes nothing)
    python scripts/ingest_constitution.py --file data/raw/constitution-of-india.pdf \
        --source-key india-code-constitution --language en

    # write, with a verified backup taken first
    python scripts/ingest_constitution.py --file data/raw/constitution-of-india.pdf \
        --source-key india-code-constitution --language en --apply --backup

    # Gujarati edition
    python scripts/ingest_constitution.py --file data/raw/samvidhan-gu.pdf \
        --source-key india-code-constitution --language gu --apply

Exit codes: 0 success (or dry-run clean), 3 dry-run found blocking problems.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.config import load_settings  # noqa: E402
from backend.app.db import backup_database, get_db, init_database  # noqa: E402
from backend.app.services.ingest import ingest_text, read_source  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest the Constitution from an official document")
    parser.add_argument("--file", required=True, help="path to the .pdf / .txt source")
    parser.add_argument("--source-key", required=True, help="legal_sources.source_key for this document")
    parser.add_argument("--language", default="en", choices=["en", "gu"])
    parser.add_argument("--apply", action="store_true", help="write to the database (default: dry run)")
    parser.add_argument("--backup", action="store_true", help="take a verified backup before writing")
    parser.add_argument("--report", help="write the JSON report to this path")
    args = parser.parse_args()

    settings = load_settings()
    path = Path(args.file)
    if not path.exists():
        print(f"Source file not found: {path}", file=sys.stderr)
        return 2

    if args.apply:
        init_database(settings)
        if args.backup:
            print(f"Backup: {backup_database(settings.backup_dir, settings.db_path)}")

    text, kind = read_source(path)
    print(f"Read {len(text):,} characters ({kind}) from {path.name}")

    with get_db(settings.db_path) as conn:
        report = ingest_text(
            conn,
            text=text,
            source_key=args.source_key,
            source_file=path.name,
            language=args.language,
            dry_run=not args.apply,
        )

    payload = report.as_dict()
    print(json.dumps(payload, indent=2, ensure_ascii=False)[:4000])
    if args.report:
        Path(args.report).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Report written to {args.report}")

    blocking = report.duplicates or report.malformed
    if not args.apply:
        print("\nDRY RUN — nothing was written. Re-run with --apply to import.")
        return 3 if blocking else 0
    print(f"\nWrote {report.articles_written} articles "
          f"(skipped {report.articles_skipped_verified} already-verified rows).")
    print("Every imported row still has verification_status = requires_human_verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
