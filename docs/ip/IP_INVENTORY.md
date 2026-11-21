# IP_INVENTORY.md

NYAYMITRA 2.0 — Intellectual-property inventory
================================================

## Status

**Self-assessed inventory.** Not a legal opinion and not a guarantee of ownership. It
lists components by origin so the owner and their legal counsel can determine the
eligible IP position.

## 1. Project-created components (candidate owner IP)

These files were created for NYAYMITRA 2.0 and are the primary candidate for owner-owned
copyright:

* `backend/app/` — FastAPI application: config, models, routers, services, middleware,
  AI provider abstraction, RAG pipeline, guard (prompt injection / answer validation),
  monitoring, seed.
* `backend/migrations/` — SQL migrations 001–004.
* `backend/tests/` — pytest suite.
* `web/app.js`, `web/admin.js`, `web/styles.css`, `web/index.html`, `web/admin.html`,
  `web/favicon.svg`, `web/manifest.webmanifest` — citizen and admin frontends.
* `scripts/` — backup, check_db, changeset verification, AI provider probe, ingest,
  license audit, smoke test.
* `docs/` — all documentation.
* `Dockerfile`, `render.yaml`, `deploy/nyaymitra.service`, `deploy/nyaymitra.env.example`
  — deployment configuration.
* `run.sh`, `run.bat`, `pytest.ini` — entry points.

## 2. Third-party components

### Runtime dependencies (`backend/requirements.txt`)

| Package | Version | Licence | Role |
|---------|---------|---------|------|
| fastapi | 0.162.2 | MIT | Web framework |
| uvicorn | 0.54.0 | BSD-3-Clause | ASGI server |
| pydantic | 2.10.3 | MIT | Data validation |
| httpx | 0.28.1 | BSD-3-Clause | HTTP client (provider calls) |
| pypdf | 7.0.0 | BSD-3-Clause | PDF text extraction |
| python-multipart | 0.0.33 | Apache-2.0 | Form/file upload parsing |
| starlette | 1.10.0 | BSD-3-Clause | ASGI toolkit (transitive, via fastapi) |

### Test dependencies (`backend/requirements-dev.txt`)

* pytest, pytest-cov — MIT-licensed test tooling.

### Frontend

* Vanilla JavaScript, no libraries, no CDN, no frameworks.
* `web/favicon.svg` — project-created.

### Data / seed

* `data/seed/constitution_seed.json` — owner-written plain-language explanations of
  9 Constitution of India articles (not the statute text).
* `data/seed/departments_seed.json` — 11 government-department entries (unverified).
* `data/seed/glossary.json` — 18 plain-language glossary terms.
* `data/seed/sources.json` — 15 source records.
* `data/seed/triage_seed.json` — 5 triage guides.
* `data/legacy/constitution_articles_legacy_2026-11-07.jsonl.gz` — 2,125 quarantined
  legacy PDF chunks (NOT articles; never served). See `docs/REPOSITORY_AUDIT.md` §6.

## 3. AI-generated code

Portions of the codebase were produced with AI assistance (this project is developed by
an autonomous agent). AI-generated contributions are treated the same as any other
contribution: ownership follows the project's contribution and licensing position, not
a blanket assignment to the AI provider. No claim is made that AI-generated code is free
of third-party IP.

## 4. External data sources

* No live external legal data is fetched at runtime. The Constitution content is
  owner-written explanation, not the statute.
* Department portal URLs and helplines are recorded as received; none have been
  independently confirmed against official sources (blocker B-2).

## 5. Licensing position

* All project-created code is under the repository `LICENSE` (MIT).
* Third-party dependencies are all permissive (MIT / BSD / Apache / Unlicense).
* No copyleft (GPL / AGPL / LGPL) dependencies.
* No model weights are included or downloaded.

## 6. Unclear ownership / missing permissions

* The 2,125 legacy rows are unlabelled PDF chunks of unknown origin — quarantined, never
  served. Their copyright status is unresolved.
* Department contact details come from unverified sources.

## 7. What this document does NOT do

* Does not guarantee that every line of code belongs to the project owner.
* Does not provide a freedom-to-operate opinion.
* Does not address model-licence questions (no model is bundled).

See also: `docs/ip/THIRD_PARTY_LICENSE_AUDIT.md`,
`docs/ip/SOFTWARE_BILL_OF_MATERIALS.md`,
`docs/ip/GOVERNMENT_LICENSING_READINESS.md`,
`docs/ip/OWNERSHIP_AND_CONTRIBUTION_REVIEW.md`.
