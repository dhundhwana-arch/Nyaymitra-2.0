#!/usr/bin/env python3
"""Create / migrate / seed the NYAYMITRA database.

Examples
--------
    python scripts/init_db.py                       # migrate + seed (idempotent)
    python scripts/init_db.py --info                # show what is in the database
    python scripts/init_db.py --backup --migrate    # safe upgrade with a verified backup
    python scripts/init_db.py --rollback-to 0       # destructive: drop everything from 001
    python scripts/init_db.py --no-seed             # schema only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.config import load_settings  # noqa: E402
from backend.app.db import (  # noqa: E402
    apply_migrations,
    backup_database,
    get_db,
    rollback_migrations,
    table_counts,
)
from backend.app.services.seed import seed_all  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="NYAYMITRA database bootstrap")
    parser.add_argument("--migrate", action="store_true", help="apply pending migrations (default)")
    parser.add_argument("--seed", dest="seed", action="store_true", default=None, help="load seed JSON")
    parser.add_argument("--no-seed", dest="seed", action="store_false", help="schema only")
    parser.add_argument("--backup", action="store_true", help="take a verified backup first")
    parser.add_argument("--rollback-to", type=int, default=None, metavar="N",
                        help="roll back until N migrations remain applied (destructive)")
    parser.add_argument("--info", action="store_true", help="print table counts and exit")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    settings = load_settings()
    report: dict = {"db_path": str(settings.db_path), "environment": settings.environment}

    if args.backup and settings.db_path.exists():
        report["backup"] = str(backup_database(settings.backup_dir, settings.db_path))

    with get_db(settings.db_path) as conn:
        if args.rollback_to is not None:
            report["rolled_back"] = rollback_migrations(conn, settings.migrations_dir, args.rollback_to)
        if args.migrate or args.rollback_to is None:
            report["applied"] = apply_migrations(conn, settings.migrations_dir)
        report["counts"] = table_counts(conn)

    should_seed = args.seed if args.seed is not None else True
    if should_seed and args.rollback_to is None:
        report["seeded"] = seed_all(settings)

    if args.info or args.rollback_to is None:
        with get_db(settings.db_path) as conn:
            report["counts"] = table_counts(conn)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Database: {report['db_path']}")
        if report.get("backup"):
            print(f"Backup:   {report['backup']}")
        if report.get("applied"):
            print(f"Applied:  {', '.join(report['applied'])}")
        if report.get("rolled_back"):
            print(f"Rolled back: {', '.join(report['rolled_back'])}")
        if report.get("seeded"):
            seeded = report["seeded"]
            print("Seeded:   imported={} skipped={} failed={} errors={}".format(
                seeded.get("total_imported", 0),
                seeded.get("total_skipped", 0),
                seeded.get("total_failed", 0),
                len(seeded.get("errors", [])),
            ))
            for table, stats in seeded.get("tables", {}).items():
                print(f"  {table}: imported={stats['imported']} skipped={stats['skipped']} failed={stats['failed']}")
            for err in seeded.get("errors", []):
                print(f"  ERROR: {err}")
        print("Tables:")
        for table, count in sorted(report["counts"].items()):
            print(f"  {table:<28} {count:>8}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
