# GOVERNMENT_LICENSING_READINESS.md

NYAYMITRA 2.0 — Government technology licensing readiness
==========================================================

## Intended business model (owner's stated preference)

* Creator retains eligible intellectual-property rights.
* Government (or its appointed vendor) receives a negotiated **non-exclusive usage
  licence**.
* Government / appointed technical teams host and operate the infrastructure and
  perform ongoing maintenance.
* Licence fees and responsibilities are negotiated through a formal agreement.

This document prepares the technical material for that discussion. It is **not** a
legal agreement, does not create any licence, and does not represent government
approval or procurement eligibility.

## Technical architecture

* Single-process Python/FastAPI service (uvicorn).
* SQLite database (single file), document storage on local filesystem.
* Vanilla-JS citizen frontend and admin console (no framework, no CDN).
* Optional local AI provider via OpenAI-compatible endpoint (Ollama-compatible); offline
  grounded fallback when no provider is configured.
* Role-based admin API (monitor read-only, admin mutate).

## Product capabilities

* Plain-language legal information with source citations (9 owner-written articles;
  authoritative text not loaded).
* Government-department navigation (11 entries; unverified).
* Complaint drafting with preview/confirmation, reference + access-token retrieval.
* Document upload and owner-token download.
* Verification queue and review packet for human legal review.
* Token and usage tracking for the AI provider.
* Database migrations, backups, integrity checks, retention purge.

## Deployment requirements

* Host: any machine that runs Python 3.11+ and SQLite (Docker image or systemd unit
  provided).
* Database and storage directory outside the code checkout.
* TLS termination at the platform/reverse-proxy layer (not implemented in-app).
* Admin and monitor tokens (random, ≥24 chars).
* No AI provider required (offline mode); optional Ollama-compatible endpoint.

## Security responsibilities (operator)

* Protect admin/monitor tokens; rotate on compromise.
* Protect backups at rest (encrypted volume or filesystem encryption).
* Implement backup rotation.
* Apply OS and dependency security updates.
* Rate limiting is per-process; scale-out requires Redis.

## Maintenance responsibilities (operator)

* Run `scripts/check_db.py` periodically.
* Apply migrations; seed after schema changes.
* Review the verification queue; appoint a human legal reviewer (blocker B-2).
* Ingest authoritative Constitution documents (blocker B-1).
* Run retention purge per `docs/legal/DATA_RETENTION_POLICY.md`.

## Support requirements

* No vendor support is offered or implied.
* Documentation: this repository (`docs/`, `README.md`, `SECURITY.md`, `PRIVACY.md`).

## Data ownership and processing

* Complaint data belongs to the citizen who submitted it.
* The operator hosts and processes it solely for the complaint purpose.
* No third-party processing; no AI training on complaint data.

## Third-party restrictions

* All dependencies are permissive-licensed; no copyleft obligations.
* No model weights bundled; no paid API used.

## Procurement readiness

* Zero licence fee for the software itself (MIT-licensed project code).
* Negotiable non-exclusive government licence (to be agreed by the parties).
* Source available on GitHub: `https://github.com/dhundhwana-arch/Nyaymitra-2.0.git`.

## Not claimed

* Government approval or adoption.
* Compliance certification.
* Signed licence agreement.
* Exclusive ownership of third-party components.

## Legal agreements

No agreement for signature is created here. Any licence agreement requires qualified
legal review by the parties.

See also: `docs/ip/IP_INVENTORY.md`, `docs/ip/THIRD_PARTY_LICENSE_AUDIT.md`,
`docs/ip/SOFTWARE_BILL_OF_MATERIALS.md`, `docs/ip/OWNERSHIP_AND_CONTRIBUTION_REVIEW.md`.
