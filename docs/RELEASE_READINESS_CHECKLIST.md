# Release readiness checklist

Three release stages are possible. Each gate is either satisfied today (with evidence) or it is
not — nothing here is aspirational.

**Revision note (2026-11-12):** the numbers below were re-measured on the reconciled branch after
the Phase 4 importer was integrated, and corrected where the previous revision had drifted (test
count, migration count, coverage, PR reference, deployment state). Every figure here is
reproducible with the command named beside it. Merging this branch is an *engineering* gate and
nothing more: **the software is not production-ready** — Stage B and Stage C remain blocked on
content and on independent review, as recorded below.

Legend: ✅ done and evidenced · ⚠️ done with a documented limitation · ❌ not done (blocked)

---

## Stage A — Engineering release (merge the branch)

| Gate | Status | Evidence |
|---|---|---|
| Backend imports and starts from a clean checkout | ✅ | `uvicorn backend.app.main:app`, `/health` |
| Database bootstraps from nothing | ✅ | CI step + `scripts/init_db.py --info` |
| Migrations apply and roll back (6 migrations) | ✅ | `test_migrations_are_idempotent`, `test_rollback_and_reapply`, `test_migration_002_rolls_back_cleanly`; a full `006 → 001` rollback was run and leaves only `schema_migrations` |
| Full test suite green | ✅ | `443 passed` backend (`389` canonical + `54` Phase 4) and `15 passed` source-tool tests — **458 total**; re-run on the integrated branch |
| Coverage ≥ 85 % | ✅ | 92 % (3932 statements, 328 missed) |
| Changeset manifest verified (tree + extracted archive) | ✅ | `scripts/verify_changeset.py`; see `docs/HANDOVER.md` §2 |
| Live model verified end to end | ❌ | `scripts/verify_ai_provider.py` exits 3: no provider available here |
| Frontend syntax checks | ✅ | `node --check` on 5 files: `web/app.js`, `web/admin.js`, `web/config.js`, `scripts/smoke_web.mjs`, `scripts/e2e_activation.mjs` |
| Browser journeys (simulated) | ✅ | `scripts/smoke_web.mjs` — all routes + admin |
| Dependency audit clean | ✅ | `pip-audit --vulnerability-service pypi` → no known vulnerabilities |
| Security controls regression-tested | ✅ | `test_admin_and_security.py`, `test_metrics_and_privacy.py` |
| CI workflow present and green | ✅ | PR #2 runs `43506947585` (push) and `43506970248` (pull_request) on `93f70d5`: pytest 3.11 ✅, pytest 3.12 ✅, dependency audit ✅, frontend syntax ✅; the Cloudflare Pages deploy job is manual-only and **skipped** |
| Documentation matches code | ✅ | 30 documents under `docs/`; this checklist was itself corrected against measured values |
| No secrets in the repository | ✅ | `test_no_secret_is_hardcoded_in_tracked_source`, `git grep` clean |
| Legacy data preserved | ✅ | 2,125 rows in gzip + `legacy_import_chunks` |
| PR opened, not merged | ✅ | PR #2 (`arena/2497125a-nyaymitra-2-0` → `main`), open, not draft, not merged, 0 reviews; PR #1 remains open as a draft |

**Stage A verdict: READY (engineering merge only).** Merge requires the owner's explicit approval
and, per the project's own gate, a recorded review. Stage A being ready says the *branch* is sound;
it does not say the *system* is fit to run for citizens.

---

## Stage B — Supervised evaluation (a help desk or a small trusted group)

Everything in Stage A, plus:

**Current deployment state: nothing is deployed.** 0 GitHub deployments, 0 environments, no Pages
site, 0 releases and 0 tags. The Pages deploy job has never run and is guarded to
`workflow_dispatch` on `refs/heads/main` only.

| Gate | Status | Required action |
|---|---|---|
| Authoritative article text loaded | ❌ | **B-1 open — 0 authoritative texts** (`article_texts` = 0; 0 of 9 articles carry official source text). Owner supplies official PDFs (EN and GU) |
| Every legal statement human-verified | ❌ | **B-2 open — 0 human-verified**; all 9 rows are `owner_authored_summary` / `requires_human_verification`. Named reviewer signs off |
| Retention period decided and scheduled | ⚠️ | `scripts/purge_data.py` exists; schedule it in cron |
| Admin token strong and private, monitor token separate | ⚠️ | Operator must generate both (command in deployment guide) |
| HTTPS at the proxy, HSTS on | ⚠️ | Operator must configure TLS |
| Backups scheduled and a restore rehearsed | ⚠️ | `scripts/backup_db.py`, cron example in deployment guide |
| Real-device test pass | ❌ | B-3 |
| Operator knows the "unverified" workflow | ⚠️ | `docs/LEGAL_VERIFICATION_CHECKLIST.md` |

**Stage B verdict: NOT READY** until B-1 and B-2 close. The app itself is stable; the *content* is
not yet fit to advise anyone. The Phase 4 importer is a tool that will load that content once the
owner supplies it — it does not itself close B-1 or B-2, and it imports no text by default.

---

## Stage C — Public release

Everything in Stage B, plus:

| Gate | Status | Notes |
|---|---|---|
| Legal review of the disclaimers and the complaint text | ❌ | Not performed |
| Privacy notice / DPIA for complaint personal data | ❌ | Not written; retention and access model are documented |
| Independent penetration test | ❌ | Never performed; `SECURITY_AUDIT.md` is a self-assessment |
| Accessibility audit with assistive technology | ❌ | B-3 |
| Load/performance test | ❌ | Not measured |
| WAF / DDoS protection | ❌ | Not configured |
| Per-user operator accounts with MFA | ❌ | Shared tokens today (residual risk R-7) |
| Monitoring/alerting wired to the metrics endpoint | ⚠️ | `/admin/metrics` exists; no scraper configured |
| Gujarati copy reviewed by a native speaker | ❌ | Not reviewed |

**Stage C verdict: NOT READY.** Do not expose this publicly.

---

## Pre-merge checklist (copy into the PR)

- [x] `python -m pytest backend/tests` → 443 passed
- [x] `python -m pytest tests` → 15 passed (needs `requirements-ingestion.txt`)
- [x] `python -m pytest --cov=backend/app` → 92 % (3932 statements, 328 missed)
- [x] `node --check web/app.js web/admin.js web/config.js scripts/smoke_web.mjs scripts/e2e_activation.mjs`
- [x] `node scripts/smoke_web.mjs <url>` → OK
- [x] `pip-audit --vulnerability-service pypi -r backend/requirements.txt` → clean
- [x] `python scripts/constitution_coverage.py` → 9/395 articles loaded, 0 authoritative texts, 0 human sign-offs (honest)
- [x] Fresh-database bootstrap + `scripts/check_db.py` → integrity ok, 6 applied, 30 indexes present
- [x] `python scripts/verify_changeset.py --verify <manifest>` → 0 missing / 0 extra / 0 modified, extracted archive also verified
- [ ] `python scripts/verify_ai_provider.py` → exit 0 (live model) — currently exit 3, no provider here
- [x] No file permissions wider than 0600/0700 for data
- [x] Documentation updated and cross-checked against the code
- [ ] **Owner approval to merge** (required)

## Pre-deployment checklist (operator)

- [ ] `NYAYMITRA_ENV=production`, strong distinct admin/monitor tokens
- [ ] TLS terminated at the proxy, HSTS confirmed
- [ ] `python scripts/init_db.py --info` on the server database
- [ ] Backup cron installed; one restore rehearsed on a copy
- [ ] Retention cron installed (after the retention period is decided)
- [ ] `/api/v1/ready` returns `ready: true`
- [ ] `/admin` reachable only by the operator
- [ ] `stat -c '%a' data/nyaymitra.db` → 600
- [ ] The banner about missing authoritative text is understood and acceptable for this deployment
