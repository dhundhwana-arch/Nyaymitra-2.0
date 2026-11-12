#!/usr/bin/env python3
"""Database integrity and health check.

Runs the checks an operator actually needs before and after a deployment, and exits non-zero
when something is wrong, so it can be a cron job or a CI step:

    python scripts/check_db.py            # human report
    python scripts/check_db.py --json     # machine report
    python scripts/check_db.py --strict   # warnings also fail (use in CI)

Checks
  1. schema: which migrations have been applied, and is a newer code version asking for more?
  2. SQLite ``PRAGMA integrity_check`` and ``PRAGMA foreign_key_check``
  3. referential orphans that SQLite cannot express as constraints
  4. the indexes the admin and citizen queries depend on
  5. content sanity: article numbers, empty texts, duplicate labels
  6. personal-data hygiene: how many complaint rows exist and the oldest one

It never modifies the database and never prints complaint content.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.config import load_settings  # noqa: E402
from backend.app.db import applied_migrations, get_db  # noqa: E402

REQUIRED_INDEXES = {
    "idx_articles_no",
    "idx_articles_part",
    "idx_articles_verification",
    "uq_articles_no_part",
    "idx_complaints_status",
    "idx_complaints_created",
    "uq_complaints_client_request",
    "idx_complaints_fingerprint",
    "idx_documents_complaint",
    "idx_query_logs_created",
    "idx_audit_at",
    "idx_error_at",
    "idx_ai_answers_created",
}


def _scalar(conn, sql: str, params: tuple = ()) -> object:
    row = conn.execute(sql, params).fetchone()
    return None if row is None else row[0]


def check(conn, settings) -> dict:
    problems: list[str] = []
    warnings: list[str] = []

    integrity = _scalar(conn, "PRAGMA integrity_check")
    if integrity != "ok":
        problems.append(f"PRAGMA integrity_check returned: {integrity}")

    fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
    if fk_errors:
        problems.append(f"{len(fk_errors)} foreign key violation(s)")

    migrations = applied_migrations(conn)
    expected = sorted(p.name for p in Path(settings.migrations_dir).glob("*.sql")
                      if not p.name.endswith(".down.sql"))
    applied = set(migrations)
    missing = [name for name in expected if name not in applied]

    present = {
        row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'"
        ).fetchall()
    }
    missing_indexes = sorted(REQUIRED_INDEXES - present)
    if missing_indexes:
        problems.append("missing index(es): " + ", ".join(missing_indexes))

    orphans = {
        "documents_without_complaint": _scalar(
            conn,
            "SELECT COUNT(*) FROM documents d LEFT JOIN complaints c ON c.id = d.complaint_id"
            " WHERE c.id IS NULL",
        ),
        "answers_without_query_log": _scalar(
            conn,
            "SELECT COUNT(*) FROM ai_answers a LEFT JOIN query_logs q ON q.id = a.query_log_id"
            " WHERE a.query_log_id IS NOT NULL AND q.id IS NULL",
        ),
        "articles_without_source": _scalar(
            conn,
            "SELECT COUNT(*) FROM constitution_articles WHERE source_id IS NULL",
        ),
    }
    for name, count in orphans.items():
        if count:
            warnings.append(f"{name}: {count}")

    articles = _scalar(conn, "SELECT COUNT(*) FROM constitution_articles") or 0
    with_text = _scalar(
        conn,
        "SELECT COUNT(*) FROM constitution_articles WHERE text_status = 'verified_source_text'",
    ) or 0
    verified = _scalar(
        conn, "SELECT COUNT(*) FROM constitution_articles WHERE verification_status = 'verified'"
    ) or 0
    broken_numbers = _scalar(
        conn,
        "SELECT COUNT(*) FROM constitution_articles WHERE article_no = '' OR article_no IS NULL",
    ) or 0
    if broken_numbers:
        problems.append(f"{broken_numbers} article(s) with an empty article number")
    duplicate_labels = conn.execute(
        """SELECT article_no, COUNT(*) AS n FROM constitution_articles
           GROUP BY article_no HAVING n > 1 ORDER BY article_no"""
    ).fetchall()
    if duplicate_labels:
        warnings.append(
            "duplicate article numbers: "
            + ", ".join(f"{row['article_no']}×{row['n']}" for row in duplicate_labels)
        )

    complaints = _scalar(conn, "SELECT COUNT(*) FROM complaints") or 0
    oldest = _scalar(conn, "SELECT MIN(created_at) FROM complaints")
    legacy = _scalar(conn, "SELECT COUNT(*) FROM legacy_import_chunks") or 0

    db_path = Path(settings.db_path)
    size = db_path.stat().st_size if db_path.exists() else None

    return {
        "database": str(db_path),
        "size_bytes": size,
        "integrity": integrity,
        "migrations": {
            "applied": sorted(applied),
            "pending": missing,
        },
        "indexes": {"present": len(present), "missing": missing_indexes},
        "orphans": orphans,
        "content": {
            "articles": articles,
            "articles_with_authoritative_text": with_text,
            "articles_human_verified": verified,
            "legacy_quarantined": legacy,
        },
        "personal_data": {
            "complaints": complaints,
            "oldest_complaint_at": oldest,
            "retention_days": settings.pii_retention_days,
        },
        "problems": problems,
        "warnings": warnings,
        "ok": not problems,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NYAYMITRA database integrity check")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = parser.parse_args(argv)

    settings = load_settings()
    with get_db(settings.db_path) as conn:
        report = check(conn, settings)

    failed = bool(report["problems"]) or (args.strict and bool(report["warnings"]))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"database        : {report['database']} ({report['size_bytes']} bytes)")
        print(f"integrity       : {report['integrity']}")
        print(f"migrations      : {len(report['migrations']['applied'])} applied, "
              f"{len(report['migrations']['pending'])} pending")
        print(f"indexes         : {report['indexes']['present']} present, "
              f"{len(report['indexes']['missing'])} missing")
        print(f"articles        : {report['content']['articles']} "
              f"({report['content']['articles_with_authoritative_text']} with source text, "
              f"{report['content']['articles_human_verified']} human-verified)")
        print(f"legacy rows     : {report['content']['legacy_quarantined']} (quarantined)")
        print(f"complaints      : {report['personal_data']['complaints']} "
              f"(oldest {report['personal_data']['oldest_complaint_at'] or 'n/a'}, "
              f"retention {report['personal_data']['retention_days']} days)")
        for problem in report["problems"]:
            print(f"PROBLEM: {problem}")
        for warning in report["warnings"]:
            print(f"warning: {warning}")
        print("RESULT: OK" if not failed else "RESULT: FAILED")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
