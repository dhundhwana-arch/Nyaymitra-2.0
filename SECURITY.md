# SECURITY.md

NYAYMITRA 2.0 — Security policy and controls summary
=====================================================

## Status

**Self-assessed. Not certified.** No independent penetration test or formal security
assessment has been performed. This document describes the controls that are implemented
and the limitations that remain. It is not a security guarantee.

## Threat model

See `docs/security/THREAT_MODEL.md`.

## Authentication and authorization

* Admin and monitor APIs are protected by bearer tokens (`NYAYMITRA_ADMIN_TOKEN`,
  `NYAYMITRA_MONITOR_TOKEN`) compared in constant time.
* Tokens are never hard-coded. Absence of a token disables the admin API rather than
  falling back to a default credential.
* Two roles exist: `monitor` (read-only) and `admin` (may update verification state and
  trigger database backups).
* Tokens are not sessions — there are no server-side sessions or cookies. Each request
  carries the token in the `X-Admin-Token` header.

## Rate limiting

* Fixed-window, in-memory rate limiter per client IP and endpoint class:
  * read endpoints: 120 requests / 60 s
  * write endpoints: 30 requests / 60 s
  * AI endpoints: 20 requests / 60 s
  * admin endpoints: 10 requests / 60 s
* The limiter is per-process. Multi-process deployment requires moving it to Redis.

## Input validation

* All request bodies are validated by Pydantic models; invalid input returns 422 with
  field-level detail.
* Complaint descriptions are capped at 5000 characters; questions at 1500.
* File uploads are capped at 10 MB and restricted to PDF, JPEG, PNG, WEBP by MIME type.
* Uploaded files are stored under random names; the original filename is never used on
  disk.
* Article identifiers are restricted to `[A-Za-z0-9\-]+`.

## Prompt injection and AI safety

* User input is scanned for instruction-like patterns before being sent to any provider.
* Retrieved sources are fenced in `<<SOURCE ...>>` blocks and the model is told to treat
  them as data, not instructions.
* Model answers are validated: any cited article that was not retrieved, or any unsafe
  advice pattern (guilt determination, outcome guarantee, impersonation), causes the
  answer to be discarded and replaced with the deterministic offline grounded response.
* The AI never files complaints, never decides cases, and never presents itself as a
  lawyer.

## SQL injection

* All database access uses parameterized queries through the `sqlite3` module. No
  string interpolation of user input into SQL.

## Cross-site scripting

* The frontend escapes all user-controlled text before inserting it into the DOM
  (`textContent`-only insertion, no `innerHTML` of user data).
* Document downloads set `X-Content-Type-Options: nosniff` and `Cache-Control: no-store`.

## Security headers

* `SecurityHeadersMiddleware` applies `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and a restrictive
  `Content-Security-Policy` (no inline scripts, no `eval`, no external origins except
  self).

## CORS

* No CORS origins are enabled by default. The app is served from a single origin. Set
  `NYAYMITRA_ALLOWED_ORIGINS` only if cross-origin access is genuinely needed.

## Secrets

* No API keys, tokens, or secrets are committed to the repository.
* `deploy/nyaymitra.env.example` contains placeholder values only — never copy it to a
  real `.env` without replacing every placeholder.
* Logs record request IDs and status codes, never question text, answer text, tokens, or
  IP addresses in plain text (IPs are SHA-256 truncated when recorded).

## Database

* SQLite WAL mode. Foreign keys enabled where the schema declares them.
* `scripts/check_db.py` verifies `PRAGMA integrity_check`, `PRAGMA foreign_key_check`,
  migrations, indexes, and orphan detection. It never prints complaint content.
* Database backups are created by `scripts/backup_db.py` (or `POST /admin/backup`) and
  are integrity-checked with `PRAGMA integrity_check`.

## Dependency vulnerabilities

* `pip-audit` is run in CI against `backend/requirements.txt`. Result at last run:
  **No known vulnerabilities found**.
* All runtime dependencies carry permissive licences (MIT / BSD / Apache / Unlicense).
  See `docs/ip/THIRD_PARTY_LICENSE_AUDIT.md`.

## Docker

* Container runs as a non-root user (`nyaymitra`, uid 10001).
* Single worker (SQLite does not support safe multi-process write access).
* Health check hits `/api/v1/ready`, which verifies database, migrations and storage.
* `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict` etc. in the systemd unit.

## Production preflight

* `create_app()` refuses to start in `production` mode when:
  * admin/monitor tokens are unset, short, placeholder-like, or low-entropy;
  * both tokens are identical;
  * the database path is inside the git checkout;
  * proxy-header trust is on without allowed origins.

## Limitations

* No independent penetration test.
* Rate limiter is in-memory only (per-process).
* No WAF, no external secret manager — tokens come from environment variables.
* Real-device and browser testing has not been performed (blocker B-3).
* The AI provider has not been tested with a real model (blocker: no model runtime in
  this environment — see `scripts/verify_ai_provider.py`).

## Reporting security concerns

Contact the repository owner through GitHub issues. Do not disclose potential
vulnerabilities publicly before they have been reviewed.
