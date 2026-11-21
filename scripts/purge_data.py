#!/usr/bin/env python3
"""Delete personal data older than the retention window.

Dry-run by default: it prints what *would* be deleted and writes nothing. The purge
touches complaints, their uploaded documents (rows and files) and query logs; the audit
trail is kept and the purge itself is recorded.

    python scripts/purge_data.py                      # show what would go
    python scripts/purge_data.py --days 90            # different window
    python scripts/purge_data.py --apply               # actually delete
    python scripts/purge_data.py --apply --json

Schedule it (cron/systemd timer) only after deciding the retention period with the
project owner — see docs/DEPLOYMENT_GUIDE.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.config import load_settings  # noqa: E402
from backend.app.db import get_db  # noqa: E402
from backend.app.services.retention import purge  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Purge personal data past the retention window")
    parser.add_argument("--days", type=int, default=None,
                        help="retention window in days (default: NYAYMITRA_PII_RETENTION_DAYS)")
    parser.add_argument("--apply", action="store_true", help="actually delete (default: dry run)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    settings = load_settings()
    with get_db(settings.db_path) as conn:
        report = purge(conn, settings, days=args.days, dry_run=not args.apply)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        mode = "DRY RUN — nothing was deleted" if report["dry_run"] else "deleted"
        print(f"Retention window: {report['retention_days']} days (cutoff {report['cutoff']})")
        print(f"Complaints: {report['complaints']}  documents: {report['documents']}  "
              f"query logs: {report['query_logs']}  files: {report['files_deleted']}")
        print(mode)
        if report["dry_run"]:
            print("Re-run with --apply to delete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
