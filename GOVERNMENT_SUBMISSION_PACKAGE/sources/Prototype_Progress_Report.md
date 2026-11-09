# NYAYMITRA 2.0 — Prototype Progress and Evidence Report

## 1. What has been implemented

- Backend: FastAPI app factory, config, security, middleware, logging (PII redaction), models, routers, services
- AI/RAG: provider abstraction (openai_compatible + offline), retrieval, citation validation, safety guard, registry
- Frontend: citizen SPA + admin console (English/Gujarati, accessible)
- Database: SQLite, 4 migrations, seed data (9 articles, 11 departments, 5 triage guides, 18 glossary terms), 2,125 quarantined legacy rows
- Scripts: init_db, check_db, backup_db, purge_data, ingest_constitution, constitution_coverage, license_audit, verify_ai_provider, verify_changeset, smoke_web
- Deployment: Dockerfile, systemd unit, render.yaml, .env.example
- Documentation: security, privacy, IP, legal, setup, audit, architecture, API, schema, testing

## 2. What has been tested

| Test area | Result |
|-----------|--------|
| `pytest` full suite | 226 passed, 0 failed |
| Coverage `--cov=backend/app` | 92% (2,545 statements, 202 missed) |
| `pip-audit` dependencies | No known vulnerabilities |
| `scripts/check_db.py` | OK (integrity ok, 4 migrations, 0 missing indexes) |
| `node --check` frontend | Pass |
| `scripts/verify_ai_provider.py` | Exit 3 — no model runtime (BLOCKED) |
| jsdom smoke test (live server) | All citizen journeys + admin console OK |
| Frontend static checks | Pass |

## 3. What has been demonstrated

Against a live `uvicorn` server on `0.0.0.0:8000`:

- Home, assistant (answer + citations + disclaimer), library search, glossary filter
- Language toggle EN ↔ GU persists
- Complaint: preview → consent checkbox → submission → reference + access token (NYM-XXXXXX)
- Saved-complaint lookup by reference + token; wrong token → generic 404 (no oracle)
- Admin console: stats, verification queue, metrics, documents
- All routes return expected status; CSP/security headers present

## 4. What remains incomplete

| Item | Status | Blocker |
|------|--------|---------|
| Official Constitution source documents | Not loaded | B-1: owner must supply PDFs |
| Human legal review of articles/departments/guides | 0 of 9 verified | B-2: reviewer not appointed |
| Real AI model inference | Not available | B-4: no Ollama/model runtime |
| Real-device / screen-reader testing | Not done | B-3: no browser/device in sandbox |
| Public deployment | Not deployed | B-5: owner approval required |

## 5. Test outputs

```
226 passed, 1 warning in 19.09s
TOTAL  2545 statements  202 missed  92%
pip-audit → No known vulnerabilities found
PRAGMA integrity_check = ok; 4 migrations applied, 0 missing indexes
/scripts/verify_ai_provider.py → exit 3 (no provider configured)
```

## 6. GitHub commit references

- Repository: https://github.com/dhundhwana-arch/Nyaymitra-2.0
- Branch: `arena/812d6894-nyaymitra-2-0`
- Latest commit: `1e9fe61` (docs: complete legal, security, IP, privacy and handover documentation)
- Prior: `5a6dcb9` (AI reliability, usage tracking, review packet, deployment configs)
- PR #1: https://github.com/dhundhwana-arch/Nyaymitra-2.0/pull/1 (open, draft, mergeable)
- CI push run: `42567707008` | CI PR run: `42567711418` (both success on `1e9fe61`)

## 7. Screenshots

No screenshots are included. Behaviour was verified against a live server via the `scripts/smoke_web.mjs` jsdom test; all journey output is recorded above. No fabricated or invented screenshots are used.

## 8. Repository

https://github.com/dhundhwana-arch/Nyaymitra-2.0
