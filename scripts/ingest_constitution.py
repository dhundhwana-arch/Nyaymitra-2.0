#!/usr/bin/env python3
"""Ingest an official Constitution document into the article table.

The project owner must supply the source file (see data/raw/README.md). Validation runs
before anything is written, and the script is dry-run by default.

    # 1. inspect (writes nothing): duplicates, missing numbers, boundaries, OCR quality
    python scripts/ingest_constitution.py --file data/raw/constitution-of-india.pdf \
        --source-key india-code-constitution --language en

    # 2. write, with a verified backup taken first
    python scripts/ingest_constitution.py --file data/raw/constitution-of-india.pdf \
        --source-key india-code-constitution --language en --apply --backup

    # 3. report coverage afterwards
    python scripts/constitution_coverage.py --format both

Safety rules
------------
* Dry-run by default; ``--apply`` is explicit.
* ``--apply`` is refused when the extraction fails the quality gate (no articles, low text
  quality, duplicates, malformed titles, suspicious boundaries, many short bodies).
  ``--force`` overrides that — and the run is stored with status
  ``completed_with_warnings`` so the override is visible later.
* Existing non-empty text is never replaced on a re-run; identical text counts as
  unchanged. ``--replace-existing`` is the explicit opt-in, and it still refuses rows a
  human has verified.

Exit codes: 0 success, 2 file/source problem, 3 quality gate blocked the run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.config import load_settings  # noqa: E402
from backend.app.db import backup_database, get_db, init_database  # noqa: E402
from backend.app.services.ingest import ingest_text, read_pages  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest the Constitution from an official document")
    parser.add_argument("--file", required=True, help="path to the .pdf / .txt source")
    parser.add_argument("--source-key", required=True, help="legal_sources.source_key for this document")
    parser.add_argument("--language", default="en", choices=["en", "gu"])
    parser.add_argument("--apply", action="store_true", help="write to the database (default: dry run)")
    parser.add_argument("--force", action="store_true",
                        help="apply even if the quality gate failed (recorded as a warning run)")
    parser.add_argument("--replace-existing", action="store_true",
                        help="replace existing source text with different text from this document")
    parser.add_argument("--backup", action="store_true", help="take a verified backup before writing")
    parser.add_argument("--report", help="write the JSON report to this path")
    args = parser.parse_args()

    settings = load_settings()
    path = Path(args.file)
    if not path.exists():
        print(f"Source file not found: {path}", file=sys.stderr)
        return 2

    pages, kind = read_pages(path)
    characters = sum(len(page) for page in pages)
    print(f"Read {characters:,} characters from {len(pages)} page(s) ({kind}) in {path.name}")

    with get_db(settings.db_path) as conn:
        report = ingest_text(
            conn,
            text=pages,
            source_key=args.source_key,
            source_file=path.name,
            language=args.language,
            dry_run=True,
        )

    print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False)[:5000])
    if report.blocking_reasons:
        print("\nQuality gate: FAILED — " + ", ".join(report.blocking_reasons))

    if not args.apply:
        print("\nDRY RUN — nothing was written. Re-run with --apply to import.")
        if args.report:
            Path(args.report).write_text(
                json.dumps(report.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(f"Report written to {args.report}")
        return 3 if report.blocking_reasons else 0

    if report.blocking_reasons and not args.force:
        print(
            "\nRefusing to write: the extraction failed the quality gate. Fix the source "
            "document, or re-run with --force to import it anyway "
            "(the run will be marked completed_with_warnings).",
            file=sys.stderr,
        )
        return 3

    init_database(settings)
    if args.backup:
        print(f"Backup: {backup_database(settings.backup_dir, settings.db_path)}")

    with get_db(settings.db_path) as conn:
        report = ingest_text(
            conn,
            text=pages,
            source_key=args.source_key,
            source_file=path.name,
            language=args.language,
            dry_run=False,
            replace_existing=args.replace_existing,
        )

    if args.report:
        Path(args.report).write_text(
            json.dumps(report.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Report written to {args.report}")

    print(
        f"\nWrote {report.articles_written} articles; "
        f"{report.articles_unchanged} unchanged, {report.articles_conflicting} conflicting "
        f"(not replaced), {report.articles_skipped_verified} already verified (never touched)."
    )
    print("Every imported row still has verification_status = requires_human_verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
