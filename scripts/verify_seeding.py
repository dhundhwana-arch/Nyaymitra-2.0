#!/usr/bin/env python3
"""Verify that database seeding succeeded and report per-table statistics.

Usage
-----
    python scripts/verify_seeding.py          # human-readable report
    python scripts/verify_seeding.py --json   # machine-readable JSON

Exits 0 if seeding is complete and consistent, non-zero otherwise.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.config import load_settings  # noqa: E402
from backend.app.db import get_db  # noqa: E402

EXPECTED_TABLES = (
    "legal_sources",
    "constitution_articles",
    "article_sources",
    "departments",
    "triage_guides",
    "legacy_import_chunks",
    "complaints",
    "documents",
    "query_logs",
    "ai_answers",
    "feedback",
    "audit_log",
    "error_log",
    "schema_migrations",
    "ingest_runs",
)

EXPECTED_COUNTS = {
    "constitution_articles": 9,
    "departments": 11,
    "triage_guides": 5,
    "legal_sources": 15,
}


def verify(conn: sqlite3.Connection) -> dict:
    report: dict = {"ok": True, "tables": {}, "errors": [], "warnings": []}

    # 1. Every expected table exists
    existing = {
        r["name"]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    for table in EXPECTED_TABLES:
        if table not in existing:
            report["ok"] = False
            report["errors"].append(f"missing table: {table}")
            report["tables"][table] = {"count": -1, "expected": "required", "present": False}
            continue

    # 2. Row counts for key tables
    for table in EXPECTED_TABLES:
        if table not in existing:
            continue
        count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        entry: dict = {"count": count, "present": True}
        expected = EXPECTED_COUNTS.get(table)
        if expected is not None:
            entry["expected"] = expected
            entry["matches_expected"] = count == expected
            if count != expected:
                report["ok"] = False
                report["errors"].append(
                    f"{table}: expected {expected} rows, found {count}"
                )
        report["tables"][table] = entry

    # 3. Articles with authoritative text
    verified_text = conn.execute(
        "SELECT COUNT(*) FROM constitution_articles WHERE text_status = 'verified_source_text'"
    ).fetchone()[0]
    owner_summaries = conn.execute(
        "SELECT COUNT(*) FROM constitution_articles WHERE text_status = 'owner_authored_summary'"
    ).fetchone()[0]
    report["tables"]["constitution_articles"]["verified_text"] = verified_text
    report["tables"]["constitution_articles"]["owner_summaries"] = owner_summaries
    if verified_text == 0:
        report["warnings"].append(
            "No articles have authoritative source text (verified_source_text). "
            "All articles are owner-authored summaries and require legal review."
        )

    # 4. All articles have a source_id
    articles_without_source = conn.execute(
        "SELECT COUNT(*) FROM constitution_articles WHERE source_id IS NULL"
    ).fetchone()[0]
    report["tables"]["constitution_articles"]["articles_without_source"] = articles_without_source
    if articles_without_source > 0:
        report["warnings"].append(
            f"{articles_without_source} articles have no source reference"
        )

    # 5. Departments with verification status
    unverified_deps = conn.execute(
        "SELECT COUNT(*) FROM departments WHERE verification_status != 'verified'"
    ).fetchone()[0]
    report["tables"]["departments"]["unverified"] = unverified_deps
    if unverified_deps > 0:
        report["warnings"].append(
            f"{unverified_deps} departments require human verification"
        )

    # 6. FTS5 index health
    try:
        fts_count = conn.execute(
            "SELECT COUNT(*) FROM constitution_fts"
        ).fetchone()[0]
        article_count = conn.execute(
            "SELECT COUNT(*) FROM constitution_articles"
        ).fetchone()[0]
        report["tables"]["constitution_fts"] = {"count": fts_count, "present": True}
        if fts_count != article_count:
            report["warnings"].append(
                f"FTS5 index has {fts_count} entries but {article_count} articles — index may be stale"
            )
    except sqlite3.Error:
        report["tables"]["constitution_fts"] = {"count": -1, "present": False}
        report["warnings"].append("FTS5 index not available")

    # 7. Integrity check
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    report["integrity"] = integrity
    if integrity != "ok":
        report["ok"] = False
        report["errors"].append(f"database integrity check failed: {integrity}")

    # 8. Migration check
    applied = [r["name"] for r in conn.execute("SELECT name FROM schema_migrations ORDER BY name")]
    report["migrations_applied"] = applied
    if not applied:
        report["ok"] = False
        report["errors"].append("no migrations applied")

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify NYAYMITRA database seeding")
    parser.add_argument("--json", action="store_true", help="machine-readable JSON output")
    args = parser.parse_args()

    settings = load_settings()
    with get_db(settings.db_path) as conn:
        report = verify(conn)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Database: {settings.db_path}")
        print(f"Integrity: {report.get('integrity', 'unknown')}")
        print(f"Migrations: {', '.join(report.get('migrations_applied', [])) or 'none'}")
        print()
        for table, info in sorted(report.get("tables", {}).items()):
            status = "OK" if info.get("present", False) else "MISSING"
            line = f"  {table:<30} {info.get('count', -1):>6} rows [{status}]"
            if "expected" in info:
                line += f" (expected {info['expected']})"
                if not info.get("matches_expected", True):
                    line += " MISMATCH"
            if "verified_text" in info:
                line += f" | verified_text={info['verified_text']} owner_summaries={info['owner_summaries']}"
            if "unverified" in info:
                line += f" | unverified={info['unverified']}"
            print(line)

        if report.get("warnings"):
            print()
            print("Warnings:")
            for w in report["warnings"]:
                print(f"  - {w}")

        if report.get("errors"):
            print()
            print("Errors:")
            for e in report["errors"]:
                print(f"  - {e}")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
