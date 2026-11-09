# EVIDENCE_MATRIX.md

NYAYMITRA 2.0 — Traceability matrix

Every claim in the government submission package is traced to evidence. Status labels:

- **VERIFIED** — confirmed by direct test/inspection against commit `1e9fe61`
- **COMPLETED** — implemented and committed
- **PARTIALLY COMPLETED** — implemented, not fully verified
- **BLOCKED** — requires an external dependency (model, reviewer, documents, devices)
- **OWNER APPROVAL REQUIRED** — requires repository-owner action (merge, deployment)

| # | Claim | Evidence | Location / URL | Verification status | Limitation |
|---|-------|----------|----------------|---------------------|------------|
| 1 | Repository is `dhundhwana-arch/Nyaymitra-2.0` | git remote + GitHub PR #1 | https://github.com/dhundhwana-arch/Nyaymitra-2.0 | VERIFIED | None |
| 2 | Branch is `arena/812d6894-nyaymitra-2-0` | `git branch` | local + `origin/arena/812d6894-nyaymitra-2-0` | VERIFIED | None |
| 3 | Latest commit is `1e9fe61` | `git log --oneline -1` | commit `1e9fe616e7b629d2c0b019f93343cbbe48c39b8a` | VERIFIED | None |
| 4 | PR #1 is open, draft, mergeable | GitHub API | https://github.com/dhundhwana-arch/Nyaymitra-2.0/pull/1 | VERIFIED | Merge requires owner approval |
| 5 | CI push + PR green on `1e9fe61` | GitHub runs `42584356621` (push) / `42584362822` (pull request) | GitHub Actions | VERIFIED | Runs reflect this commit only |
| 6 | 226 automated tests pass | `pytest` output | `backend/tests/` | VERIFIED | Sandbox, Python 3.11, SQLite |
| 7 | Coverage 92% | `pytest --cov=backend/app` | 2,545 statements, 202 missed | VERIFIED | Backend app package only |
| 8 | pip-audit: no known vulnerabilities | `pip-audit --vulnerability-service pypi` | `backend/requirements.txt` | VERIFIED | PyPI advisory service at time of run |
| 9 | Database integrity OK | `scripts/check_db.py` | `data/nyaymitra.db` | VERIFIED | Requires `init_db.py` migration first |
| 10 | Frontend syntax valid | `node --check web/app.js web/admin.js` | `web/` | VERIFIED | Static syntax only, no browser |
| 11 | App starts and `/ready` = 200 | `uvicorn` + `curl` | `backend/app/main:app` | VERIFIED | Localhost, offline provider |
| 12 | Real AI model verified | `scripts/verify_ai_provider.py` exits 3 | `scripts/` | BLOCKED | No Ollama/model runtime in sandbox |
| 13 | Human legal review complete | 0 of 9 articles verified; reviewer packet ready | `docs/legal/HUMAN_LEGAL_REVIEW_CHECKLIST.md` | BLOCKED | Named reviewer not appointed |
| 14 | Official Constitution sources loaded | 9 articles, 0 with authoritative source text | `backend/migrations/`, `data/seed/` | BLOCKED | Owner must supply official PDFs |
| 15 | Real-device / screen-reader tested | Not tested; jsdom only | `docs/TESTING_REPORT.md` §4 | BLOCKED | No browser/device in sandbox |
| 16 | Personal data never leaves app | Default offline; external provider sends question unredacted if configured | `backend/app/ai/rag.py`, `openai_compatible.py` | PARTIALLY COMPLETED | Disclosure: unredacted if external provider enabled |
| 17 | DPDP obligations in force | Main obligations commence 13 May 2027 — not yet in force | `docs/legal/LEGAL_COMPLIANCE_MATRIX.md` | VERIFIED (date) | Legal interpretation not certified |
| 18 | No copyleft/unknown dependencies | `scripts/license_audit.py` — 60 packages, 60 permissive | `docs/ip/SOFTWARE_BILL_OF_MATERIALS.md` | VERIFIED | At time of audit |

## How to read

- "VERIFIED" means the claim was checked directly against the repository at commit `1e9fe61` during this session; it is not projected or assumed.
- Items marked BLOCKED or OWNER APPROVAL REQUIRED are genuine outstanding dependencies and must not be represented as complete in any submission.
