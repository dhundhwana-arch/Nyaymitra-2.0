# BACKUP_AND_RECOVERY.md

NYAYMITRA 2.0 — Backup and recovery
====================================

## What is backed up

* The SQLite database (`NYAYMITRA_DB_PATH`, default `data/nyaymitra.db`).
* Uploaded documents (`NYAYMITRA_STORAGE_DIR`, default `storage/documents/`).
* The code changeset (`git` history plus `scripts/verify_changeset.py` manifest).

## Backup tooling

* `scripts/backup_db.py --dest <dir>` — copies the database, runs `PRAGMA integrity_check`,
  and writes a timestamped `.db` file.
* `POST /api/v1/admin/backup` — admin-triggered backup (requires `NYAYMITRA_ADMIN_TOKEN`),
  audited in `audit_log`.
* `scripts/verify_changeset.py` — manifest/verify/verify-archive for the 134 tracked
  code files; detects missing, extra, or modified files, including tampered archives.

## Backup verification

Every backup is integrity-checked before being accepted:

```
PRAGMA integrity_check   -> must return "ok"
```

A tampered copy of the archived code is detected by `verify_changeset.py --verify`
(exit 1, reports the modified file).

## Recovery procedure

1. Provision a host with Python 3.11+ and the repository at the release commit.
2. Restore the database file to `NYAYMITRA_DB_PATH` outside the checkout.
3. Restore documents to `NYAYMITRA_STORAGE_DIR`.
4. Set `NYAYMITRA_ADMIN_TOKEN` and `NYAYMITRA_MONITOR_TOKEN` (new random values — do
   not reuse tokens from a compromised environment).
5. Run `python scripts/check_db.py` to confirm integrity, migrations and indexes.
6. Start `uvicorn backend.app.main:app`.

## Retention of backups

* Backup rotation is **not implemented**. The operator must implement rotation
  (e.g. keep daily backups for 30 days, weekly for 90 days) based on their retention
  policy (`docs/legal/DATA_RETENTION_POLICY.md`).
* Old backups contain complaint data and must be deleted securely when rotated.

## Limitations

* No automated offsite backup.
* No point-in-time recovery (SQLite WAL is not archived).
* Backup/restore has not been tested in a production-scale incident.
* Backups are not encrypted by the application; at-rest encryption is the operator's
  responsibility (encrypted volume or filesystem encryption).
