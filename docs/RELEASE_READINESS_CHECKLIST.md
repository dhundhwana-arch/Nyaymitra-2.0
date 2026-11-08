# Release readiness checklist

Three release stages are possible. Each gate is either satisfied today (with evidence) or it is
not — nothing here is aspirational.

Legend: ✅ done and evidenced · ⚠️ done with a documented limitation · ❌ not done (blocked)

---

## Stage A — Engineering release (merge the branch)

| Gate | Status | Evidence |
|---|---|---|
| Backend imports and starts from a clean checkout | ✅ | `uvicorn backend.app.main:app`, `/health` |
| Database bootstraps from nothing | ✅ | CI step + `scripts/init_db.py --info` |
| Migrations apply and roll back (3 migrations) | ✅ | `test_migrations_are_idempotent`, `test_rollback_and_reapply`, `test_migration_002_rolls_back_cleanly` |
| Full test suite green | ✅ | `187 passed in 23.73s` |
| Coverage ≥ 85 % | ✅ | 92 % (2306 statements, 189 missed) |
| Changeset manifest verified (tree + extracted archive) | ✅ | `scripts/verify_changeset.py`; see `docs/HANDOVER.md` §2 |
| Live model verified end to end | ❌ | `scripts/verify_ai_provider.py` exits 3: no provider available here |
| Frontend syntax checks | ✅ | `node --check` ×3 |
| Browser journeys (simulated) | ✅ | `scripts/smoke_web.mjs` — all routes + admin |
| Dependency audit clean | ✅ | `pip-audit --vulnerability-service pypi` → no known vulnerabilities |
| Security controls regression-tested | ✅ | `test_admin_and_security.py`, `test_metrics_and_privacy.py` |
| CI workflow present and green | ✅ | runs 42442829095 / 42442832288 on `bc919d3`: pytest 3.11, pytest 3.12, dependency audit, frontend |
| Documentation matches code | ✅ | 15 documents; audit §14–§15 and plan addendum updated |
| No secrets in the repository | ✅ | `test_no_secret_is_hardcoded_in_tracked_source`, `git grep` clean |
| Legacy data preserved | ✅ | 2,125 rows in gzip + `legacy_import_chunks` |
| PR opened, not merged | ✅ | PR #1, draft |

**Stage A verdict: READY.** Merge requires the owner's explicit approval.

---

## Stage B — Supervised evaluation (a help desk or a small trusted group)

Everything in Stage A, plus:

| Gate | Status | Required action |
|---|---|---|
| Authoritative article text loaded | ❌ | Owner supplies official PDFs (B-1) |
| Every legal statement human-verified | ❌ | Named reviewer signs off (B-2) |
| Retention period decided and scheduled | ⚠️ | `scripts/purge_data.py` exists; schedule it in cron |
| Admin token strong and private, monitor token separate | ⚠️ | Operator must generate both (command in deployment guide) |
| HTTPS at the proxy, HSTS on | ⚠️ | Operator must configure TLS |
| Backups scheduled and a restore rehearsed | ⚠️ | `scripts/backup_db.py`, cron example in deployment guide |
| Real-device test pass | ❌ | B-3 |
| Operator knows the "unverified" workflow | ⚠️ | `docs/LEGAL_VERIFICATION_CHECKLIST.md` |

**Stage B verdict: NOT READY** until B-1 and B-2 close. The app itself is stable; the *content* is
not yet fit to advise anyone.

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

- [x] `python -m pytest` → 187 passed
- [x] `python -m pytest --cov=backend/app` → 92 %
- [x] `node --check web/app.js web/admin.js scripts/smoke_web.mjs`
- [x] `node scripts/smoke_web.mjs <url>` → OK
- [x] `pip-audit --vulnerability-service pypi -r backend/requirements.txt` → clean
- [x] `python scripts/constitution_coverage.py` → reports 0 verified text (honest)
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
