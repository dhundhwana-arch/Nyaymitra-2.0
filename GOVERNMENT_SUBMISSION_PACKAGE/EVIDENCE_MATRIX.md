# EVIDENCE_MATRIX.md

NYAYMITRA 2.0 — Traceability matrix

Every claim in the government submission package is traced to evidence. Nothing is projected or assumed.

Status labels:

- **VERIFIED** — confirmed by direct test/inspection against commit `88e54a0`
- **COMPLETED** — implemented and committed
- **PARTIALLY COMPLETED** — implemented, not fully verified
- **BLOCKED** — requires an external dependency (model, reviewer, documents, devices)
- **OWNER APPROVAL REQUIRED** — requires repository-owner action (merge, deployment)

## 1. Technical test evidence

| # | Claim | Evidence | Location / URL | Verification status | Limitation |
|---|-------|----------|----------------|---------------------|------------|
| T-1 | Repository is `dhundhwana-arch/Nyaymitra-2.0` | git remote + GitHub PR #1 | https://github.com/dhundhwana-arch/Nyaymitra-2.0 | VERIFIED | None |
| T-2 | Branch is `arena/812d6894-nyaymitra-2-0` | `git branch` | local + `origin/arena/812d6894-nyaymitra-2-0` | VERIFIED | None |
| T-3 | Current repository commit is `88e54a0` | `git log --oneline -1` | commit `88e54a0874528f74d081686fc7ac9a0fa25248da` | VERIFIED | None |
| T-4 | PR #1 is open, draft, mergeable; head = `88e54a0` | GitHub API | https://github.com/dhundhwana-arch/Nyaymitra-2.0/pull/1 | VERIFIED | Merge requires owner approval |
| T-5 | CI push + PR green on `88e54a0` | GitHub runs `42586560990` (push) / `42586568746` (pull request) | GitHub Actions | VERIFIED | Runs reflect commit `88e54a0` only |
| T-6 | 226 automated tests pass | `pytest` output | `backend/tests/` | VERIFIED | Sandbox, Python 3.11, SQLite |
| T-7 | Coverage 92% | `pytest --cov=backend/app` | 2,545 statements, 202 missed | VERIFIED | Backend app package only |
| T-8 | pip-audit: no known vulnerabilities | `pip-audit --vulnerability-service pypi` | `backend/requirements.txt` | VERIFIED | PyPI advisory service at time of run |
| T-9 | Database integrity OK | `scripts/check_db.py` | `data/nyaymitra.db` | VERIFIED | Requires `init_db.py` migration first |
| T-10 | Frontend syntax valid | `node --check web/app.js web/admin.js` | `web/` | VERIFIED | Static syntax only, no browser |
| T-11 | App starts and `/ready` = 200 | `uvicorn` + `curl` | `backend/app/main:app` | VERIFIED | Localhost, offline provider |
| T-12 | Real AI model verified | `scripts/verify_ai_provider.py` exits 3 | `scripts/` | BLOCKED | No Ollama/model runtime in sandbox |

## 2. Legal verification

| # | Claim | Evidence | Location / URL | Verification status | Limitation |
|---|-------|----------|----------------|---------------------|------------|
| L-1 | Constitution articles in corpus | 9 articles | `data/seed/constitution_seed.json` | COMPLETED | Owner-written explanations only |
| L-2 | Articles with authoritative source text loaded | 0 of 9 | `backend/migrations/`, `data/seed/` | BLOCKED | Owner must supply official PDFs |
| L-3 | Articles human-verified | 0 of 9 | `docs/legal/HUMAN_LEGAL_REVIEW_CHECKLIST.md` | BLOCKED | Named reviewer not appointed |
| L-4 | Departments in corpus | 11 departments | `data/seed/departments_seed.json` | COMPLETED | Verification pending |
| L-5 | Triage guides in corpus | 5 guides | `data/seed/triage_seed.json` | COMPLETED | Verification pending |
| L-6 | Legacy corpus provenance | 2,125 quarantined chunks, unresolved origin/copyright | `data/legacy/`, never served | COMPLETED (as quarantined) | Not an authoritative legal corpus |

## 3. Privacy review

| # | Claim | Evidence | Location / URL | Verification status | Limitation |
|---|-------|----------|----------------|---------------------|------------|
| P-1 | Default mode is offline (no data leaves app) | `ai_provider` default = "auto"/"offline"; no key configured | `backend/app/config.py`, `backend/app/ai/openai_compatible.py` | VERIFIED | Config-dependent |
| P-2 | External AI provider mode transmits citizen question | Question + sources sent to configured endpoint unredacted | `backend/app/ai/rag.py`, `openai_compatible.py` | PARTIALLY COMPLETED | Disclosure: unredacted if external provider enabled |
| P-3 | PII redaction before local logging/storage | `redact_and_truncate` applied to queries/answers/errors | `backend/app/logging_utils.py`, `backend/app/services/monitoring.py` | VERIFIED | Local storage only |
| P-4 | Data retention and deletion | 180-day default; `purge_data.py` dry-run default; no self-service deletion | `config.py`, `scripts/purge_data.py` | PARTIALLY COMPLETED | No self-service deletion endpoint |
| P-5 | Warning: external AI mode not for real citizen data | Documented in Legal_Privacy_Safety_Report §5 | `sources/Legal_Privacy_Safety_Report.md` | COMPLETED (disclosure) | Requires controls/review before use |

## 4. AI inference verification

| # | Claim | Evidence | Location / URL | Verification status | Limitation |
|---|-------|----------|----------------|---------------------|------------|
| A-1 | Live AI inference verified | `verify_ai_provider.py` exits 3 | `scripts/` | BLOCKED | No Ollama/model runtime in sandbox |
| A-2 | Offline deterministic fallback | Used by default when no provider configured | `backend/app/ai/offline.py`, `backend/app/ai/rag.py` | VERIFIED | Not a live model |
| A-3 | Answer safety guard | `validate_answer` rejects uncited/unsafe advice | `backend/app/ai/guard.py` | VERIFIED | Tested against stubs, not live model |

## 5. Accessibility validation

| # | Claim | Evidence | Location / URL | Verification status | Limitation |
|---|-------|----------|----------------|---------------------|------------|
| V-1 | Accessibility features implemented | Focus ring, 44px tap targets, aria-live/invalid, EN/GU toggle, media queries | `web/app.js`, `web/styles.css` | COMPLETED (implementation) | Not real-browser/device tested |
| V-2 | Real-browser / screen-reader / device validation | Not performed | `docs/TESTING_REPORT.md` §4 | BLOCKED | No browser/device in sandbox |

## 6. Production readiness

| # | Claim | Evidence | Location / URL | Verification status | Limitation |
|---|-------|----------|----------------|---------------------|------------|
| R-1 | Production deployment | Not performed | — | OWNER APPROVAL REQUIRED | Requires owner approval, TLS, hosting |
| R-2 | DPDP main obligations in force | Commence 13 May 2027 (G.S.R. 843(E)); not yet applicable as of 9 Nov 2026 | `docs/legal/LEGAL_COMPLIANCE_MATRIX.md` | VERIFIED (date fact) | Legal interpretation not certified; not DPDP compliant |
| R-3 | IT Act §43A/§72A + SPDI Rules 2011 | Apply now to body corporates handling personal data | `sources/Legal_Privacy_Safety_Report.md` §8 | VERIFIED (legal position) | Self-assessed; requires qualified legal review |

## How to read

- "VERIFIED" means the claim was checked directly against the repository at commit `88e54a0` during this session; it is not projected or assumed.
- Items marked BLOCKED or OWNER APPROVAL REQUIRED are genuine outstanding dependencies and must not be represented as complete in any submission.
- Legal dates are drawn from Gazette notifications G.S.R. 843(E) and G.S.R. 846(E); forward dates are interpretation until officially confirmed.
