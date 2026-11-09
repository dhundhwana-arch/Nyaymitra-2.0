# NYAYMITRA 2.0 — Development Roadmap

## A. Already completed work

- Rebuilt backend (FastAPI), database (SQLite + migrations), RAG layer, citizen UI, admin console
- 226 automated tests, 92% coverage, pip-audit clean
- Documentation: security, privacy, IP, legal, setup, audit, architecture
- Deployment config: Dockerfile, systemd, render.yaml, .env.example
- Backups created and integrity-checked
- PR #1 open (draft, mergeable) on `arena/812d6894-nyaymitra-2-0`, commit `068cf9f`

## B. Remaining work before submission

| # | Task | Dependency | Status |
|---|------|------------|--------|
| B-1 | Supply official Constitution PDFs; run ingestion dry run, `--apply --backup`, `constitution_coverage.py` | Repository owner | BLOCKED |
| B-2 | Appoint named human legal reviewer; review 9 articles, 11 departments, 5 triage guides | Qualified reviewer | BLOCKED |
| B-3 | Real-device, browser, screen-reader testing | Test devices | BLOCKED |
| B-4 | Install Ollama, pull `llama3.2:3b`, run `verify_ai_provider.py` to exit 0 | AI infrastructure | BLOCKED |
| B-5 | Owner reviews and merges PR #1 | Repository owner | OWNER APPROVAL REQUIRED |

## C. Work requiring institutional support

- Qualified legal reviewer(s) for blocker B-2
- AI inference infrastructure (Ollama or hosted endpoint) for blocker B-4
- Testing devices and assistive-technology access for blocker B-3
- Secure hosting and TLS termination for any deployment
- Pilot partners (DLSA / legal-aid NGO) for field validation

## D. Work after selection or support

- Load official Constitution sources; complete human legal review
- Verify live AI inference; tune retry/backoff/timeout
- Add self-service data deletion and export
- Add complaint e-signature / acknowledgment receipt
- Pilot with a legal-aid body; collect user feedback
- Harden for production (concurrency, monitoring, backups, TLS)

## Milestones (indicative, subject to support)

| Milestone | Target | Deliverable |
|-----------|--------|-------------|
| Legal review sign-off | Month 1 | Reviewed articles, departments, guides |
| AI inference verified | Month 1–2 | `verify_ai_provider.py` exit 0 |
| Device/accessibility testing | Month 2 | Test report |
| Controlled pilot | Month 2–3 | Pilot feedback report |
| Field-ready prototype | Month 3 | Hardened build, deployment guide |

## Resources required

- Qualified legal reviewers
- Technical mentorship
- Testing devices (Android/iOS/desktop) and screen readers
- AI inference infrastructure
- Secure hosting with TLS
- Pilot partners and user-feedback channel

No exaggerated budget is claimed; requirements are limited to mentorship, review, infrastructure, devices, and pilot access.

## Repository

https://github.com/dhundhwana-arch/Nyaymitra-2.0 | commit `068cf9f`
