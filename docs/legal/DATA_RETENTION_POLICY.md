# DATA_RETENTION_POLICY.md

NYAYMITRA 2.0 — Data retention policy
======================================

## Status

**Implemented in code; policy documented here.** Not a legal document. Retention periods
and the purge script exist; human legal review is required to confirm the periods are
appropriate for the jurisdiction and use case.

## Retention periods

| Record type | Retention | After retention |
|-------------|-----------|-----------------|
| Complaints | 180 days (`NYAYMITRA_PII_RETENTION_DAYS`) | Deleted by purge |
| Uploaded documents | 180 days | Deleted by purge (file + row) |
| Query logs (redacted) | 180 days | Deleted by purge |
| AI answers (metadata + citations) | 180 days | Deleted by purge |
| Audit log (admin actions only) | Retained indefinitely | Not purged |
| Constitution articles / departments / triage / glossary | Retained (reference data) | Not purged |
| Legacy chunks (quarantined) | Retained (quarantine) | Not purged |
| Backups | Operator-defined rotation | Operator deletes on rotation |

## Purge tooling

* `services/retention.py` — `purge_expired(retention_days)` deletes complaints, documents
  and query logs older than the retention window; audit trail is retained.
* `scripts/purge_data.py` — CLI wrapper with a **dry-run default**. Refuses to touch
  paths outside the storage directory.
* Run: `python scripts/purge_data.py --dry-run` (safe), then `--apply` to execute.

## What the purge does NOT delete

* Audit trail (admin verification updates, backups triggered).
* Reference data (articles, departments, triage, glossary).
* Quarantined legacy corpus.
* Backup files (operator-managed rotation).

## Backups and deleted data

Deleted records may persist in backups until the operator rotates backups. Backup
rotation is **not implemented** — see `docs/security/BACKUP_AND_RECOVERY.md`.

## Deletion on request

No self-service deletion endpoint exists yet. A data principal who wants their data
deleted must contact the operator, who can run the purge against a specific reference or
delete rows manually.

## Legal review required

* Confirm 180 days is appropriate (DPDP Act storage-limitation principles commence
  13 May 2027; DPDP Rule 8 retention/erasure commences same date).
* Confirm audit-trail retention is lawful.
* Design the deletion-on-request endpoint.
