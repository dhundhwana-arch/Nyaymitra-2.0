#!/usr/bin/env python3
"""Report what the Constitution database actually contains.

    python scripts/constitution_coverage.py                  # Markdown to stdout
    python scripts/constitution_coverage.py --format json
    python scripts/constitution_coverage.py --format both --out reports/coverage

The numbers come from the database, not from intentions: how many articles are loaded, how
many carry authoritative text, how many a human has verified, which numbers are missing
and where the gaps are. Missing articles are *reported*, never filled in.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.config import load_settings  # noqa: E402
from backend.app.db import apply_migrations, get_db  # noqa: E402

EXPECTED_ARTICLES = 395


def _ranges(numbers: list[int]) -> str:
    """Compress [1,2,3,7,9,10] into '1-3, 7, 9-10'."""
    if not numbers:
        return ""
    numbers = sorted(set(numbers))
    spans: list[tuple[int, int]] = [(numbers[0], numbers[0])]
    for value in numbers[1:]:
        start, end = spans[-1]
        if value == end + 1:
            spans[-1] = (start, value)
        else:
            spans.append((value, value))
    return ", ".join(f"{a}-{b}" if b > a else str(a) for a, b in spans)


def build_report(conn) -> dict:
    rows = conn.execute(
        """SELECT article_no, part_no, text_status, verification_status,
                  text_en, text_gu, source_pages, source_id
           FROM constitution_articles ORDER BY sort_order"""
    ).fetchall()

    # "21" and "21A" are different articles: duplicates are compared on the full label,
    # while "is number 21 present at all" only needs the numeric base.
    labels = [(row["article_no"] or "").strip().upper() for row in rows]
    duplicates = sorted({label for label in labels if label and labels.count(label) > 1})
    present_bases = {
        int(match.group(1)) for label in labels if (match := re.match(r"(\d+)", label))
    }
    missing = [n for n in range(1, EXPECTED_ARTICLES + 1) if n not in present_bases]
    with_text = [r for r in rows if (r["text_en"] or "").strip() or (r["text_gu"] or "").strip()]
    verified = [r for r in rows if r["verification_status"] == "verified"]
    parts: dict[str, int] = {}
    for row in rows:
        key = row["part_no"] or "unassigned"
        parts[key] = parts.get(key, 0) + 1

    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["text_status"]] = status_counts.get(row["text_status"], 0) + 1

    sources = [
        dict(r)
        for r in conn.execute(
            """SELECT s.source_key, s.title, s.publisher, s.url, s.document_ref,
                      (SELECT COUNT(*) FROM constitution_articles a WHERE a.source_id = s.id) AS articles
               FROM legal_sources s ORDER BY s.source_key"""
        )
    ]
    last_run = conn.execute(
        "SELECT source_file, finished_at, articles_found, articles_written, status"
        " FROM ingest_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "expected_articles": EXPECTED_ARTICLES,
        "loaded_articles": len(rows),
        "articles_with_source_text": len(with_text),
        "articles_human_verified": len(verified),
        "coverage_pct": round(100 * len(rows) / EXPECTED_ARTICLES, 1),
        "text_coverage_pct": round(100 * len(with_text) / EXPECTED_ARTICLES, 1),
        "missing_count": len(missing),
        "missing_ranges": _ranges(missing),
        "duplicate_numbers": duplicates,
        "by_part": dict(sorted(parts.items())),
        "by_text_status": dict(sorted(status_counts.items())),
        "sources": sources,
        "last_ingest_run": dict(last_run) if last_run else None,
        "note": (
            "Article numbers are only counted from rows that exist. Missing numbers are not "
            "invented, and an article is only 'human verified' when a named reviewer signed "
            "it off in the admin console."
        ),
    }


def to_markdown(report: dict) -> str:
    lines = [
        "# Constitution coverage",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Articles loaded | {report['loaded_articles']} / {report['expected_articles']} "
        f"({report['coverage_pct']}%) |",
        f"| Articles with authoritative source text | {report['articles_with_source_text']} "
        f"({report['text_coverage_pct']}%) |",
        f"| Articles signed off by a human | {report['articles_human_verified']} |",
        f"| Missing article numbers | {report['missing_count']} |",
        f"| Duplicate numbers in the database | {len(report['duplicate_numbers'])} |",
        "",
        "## Text status",
        "",
    ]
    for status, count in report["by_text_status"].items():
        lines.append(f"* `{status}`: {count}")
    lines += ["", "## Loaded articles by Part", ""]
    for part, count in report["by_part"].items():
        lines.append(f"* Part {part}: {count}")
    lines += ["", "## Missing numbers", ""]
    lines.append(report["missing_ranges"] or "none")
    if report["duplicate_numbers"]:
        lines += ["", "## Duplicate article numbers", ""]
        lines.append(", ".join(report["duplicate_numbers"]))
    lines += ["", "## Sources", "", "| source | publisher | articles |", "|---|---|---|"]
    for source in report["sources"]:
        lines.append(
            f"| {source['source_key']} | {source['publisher']} | {source['articles']} |"
        )
    lines += ["", "## Last ingestion run", ""]
    if report["last_ingest_run"]:
        run = report["last_ingest_run"]
        lines.append(
            f"* {run['source_file']} — {run['finished_at']} — found {run['articles_found']}, "
            f"wrote {run['articles_written']} ({run['status']})"
        )
    else:
        lines.append("No ingestion has been run against this database.")
    lines += ["", f"> {report['note']}", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Report Constitution coverage from the database")
    parser.add_argument("--format", choices=["json", "markdown", "both"], default="markdown")
    parser.add_argument("--out", help="write to <out>.json / <out>.md instead of stdout")
    args = parser.parse_args()

    settings = load_settings()
    with get_db(settings.db_path) as conn:
        # Reporting must not fail on an older schema: bring the schema up to date first
        # (schema only, no seeding, no data changes beyond the migrations themselves).
        apply_migrations(conn, settings.migrations_dir)
        report = build_report(conn)

    markdown = to_markdown(report)
    if args.out:
        base = Path(args.out)
        base.parent.mkdir(parents=True, exist_ok=True)
        if args.format in {"json", "both"}:
            base.with_suffix(".json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(f"Wrote {base.with_suffix('.json')}")
        if args.format in {"markdown", "both"}:
            base.with_suffix(".md").write_text(markdown, encoding="utf-8")
            print(f"Wrote {base.with_suffix('.md')}")
        return 0

    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
