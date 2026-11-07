#!/usr/bin/env python3
"""Verified online backup / restore helper.

    python scripts/backup_db.py                 # create + verify a backup
    python scripts/backup_db.py --list          # list existing backups (size, mtime)
    python scripts/backup_db.py --restore backups/nyaymitra-....db
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.config import load_settings  # noqa: E402
from backend.app.db import backup_database, restore_database  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="NYAYMITRA database backup/restore")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--restore", metavar="FILE")
    parser.add_argument("--dest", metavar="DIR")
    args = parser.parse_args()

    settings = load_settings()
    dest = Path(args.dest) if args.dest else settings.backup_dir

    if args.list:
        files = sorted(dest.glob("nyaymitra-*.db"))
        if not files:
            print(f"No backups in {dest}")
            return 0
        for path in files:
            stamp = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
            print(f"{path.name:<44} {path.stat().st_size / 1024:>10.1f} KB  {stamp}")
        return 0

    if args.restore:
        target = Path(args.restore)
        if not target.exists():
            print(f"No such backup: {target}")
            return 2
        restored = restore_database(target, settings.db_path)
        print(f"Restored {target.name} -> {restored}")
        return 0

    created = backup_database(dest, settings.db_path)
    print(f"Backup created and integrity-checked: {created}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
