# PRIVACY.md

NYAYMITRA 2.0 — Privacy and data-protection summary
====================================================

## Status

**Self-assessed.** This document describes how personal data is handled and the
safeguards in place. It is not a legal opinion and not a compliance certification under
the Digital Personal Data Protection Act, 2023 or any other law. See
`docs/legal/LEGAL_COMPLIANCE_MATRIX.md` for the applicable-law review.

## What personal data is collected

Complaint intake is voluntary. A citizen may provide:

* category, title, description (free text)
* incident date, location, district, state
* person/office complained against (respondent)
* mobile number, e-mail address
* uploaded documents (PDF / photo)
* consent flag

None of these fields are mandatory except category, title and description (and consent).
Location, contact details and documents are explicitly optional.

## What is NOT collected

* No government ID numbers (Aadhaar, PAN, passport, voter ID, etc.) are requested or
  stored.
* No biometric data.
* No health data except what a citizen voluntarily writes in a complaint description.
* No tracking cookies, no analytics, no third-party trackers.
* The AI assistant does not require any personal data — it answers from the question
  alone.

## Purpose limitation

Complaint data is used only to:

* let the citizen draft, review and save a complaint summary;
* provide a reference number and one-time access token so the citizen can re-open their
  own draft;
* suggest the relevant government department and next steps.

Complaint text is never used to train any AI model, never shared with third parties, and
never shown to administrators (admins see metadata only: reference, status, created at).

## Consent

* A checkbox consent is required before a complaint can be saved.
* The consent text states that the information will be stored on the server.
* Withdrawal of consent: there is no automated deletion-on-request endpoint yet. A
  citizen who wants their data deleted must contact the operator; see
  `docs/legal/DATA_RETENTION_POLICY.md`.

## Data minimization

* Only fields needed for the complaint purpose are collected.
* The API returns complaint metadata (not full text or contact details) to anyone
  holding a valid reference + token pair.
* Admins cannot read complaint descriptions or contact details by design.
* Query logs store a redacted copy of the question text plus a hash — not the raw text.

## Access control

* Complaint retrieval requires both the reference number and the access token (shown
  once at save time). A wrong token returns the same response as "not found" — no
  enumeration oracle.
* Admin APIs require `NYAYMITRA_ADMIN_TOKEN` / `NYAYMITRA_MONITOR_TOKEN`.
* Document download requires the document owner token.

## Data retention

* Default retention: 180 days (`NYAYMITRA_PII_RETENTION_DAYS`).
* `services/retention.py` implements the purge: old complaints, documents and query logs
  are deleted; the audit trail is retained.
* `scripts/purge_data.py` runs the purge with a dry-run default and refuses to touch
  paths outside the storage directory.
* Retention has not yet been tested against real data — see blocker B-3.

## Data deletion

* No self-service deletion endpoint exists yet (planned, not implemented).
* Backups are taken periodically; deleted records may persist in backups until the
  backup rotation removes them. See `docs/security/BACKUP_AND_RECOVERY.md`.

## Data export

* Citizens can download their own saved complaint as a `.txt` file from the UI.
* No bulk export or portability endpoint exists yet.

## Logs

* Access/error logs record request ID, method, path, status code and latency — never
  question text, answer text, tokens or contact details.
* Client IP addresses are SHA-256 truncated when recorded for rate-limiting or audit.

## Backups

* Database backups are integrity-checked (`PRAGMA integrity_check`) before being
  accepted.
* Backup files are stored outside the git checkout (default: `NYAYMITRA_BACKUP_DIR` or
  `/data/backups`).
* Backups contain complaint data and must be protected at rest (filesystem permissions,
  encrypted volume) by the operator.

## AI provider data handling

* No AI provider is configured by default (`ai_provider=offline`).
* If a provider is configured, only the question and retrieved sources are sent — never
  contact details, complaint text, or personal data.
* The provider never sees the database.

## Children's data

* The service is not directed at children. No age verification is performed. If a child
  submits a complaint, the data is treated the same as any other personal data.

## Data breach response

* See `docs/security/INCIDENT_RESPONSE.md` (planned, not yet exercised).

## Data Flow Map

See `docs/legal/DATA_FLOW_MAP.md`.

## Data Retention Policy

See `docs/legal/DATA_RETENTION_POLICY.md`.

## Consent and Notice Review

See `docs/legal/CONSENT_AND_NOTICE_REVIEW.md`.
