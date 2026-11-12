# Repository State and Production Readiness

**Date:** 2026-11-12 (UTC). Nothing was deployed and no live service was changed while preparing this.

## 1. Repository

| Branch | Commit | What it is | Status |
|---|---|---|---|
| `arena/08f8f3c5-nyaymitra-2-0` | see `git log -1` | **Current work**: rebuild + data activation + this report | pushed |
| `feature/hackindia-deployment` | `6de0f62` | Rebuild, deployment/submission variant | untouched |
| `arena/812d6894-nyaymitra-2-0` | `6e8efd7` | Rebuild, ingestion-test variant — **PR #1** (open, draft) | untouched |
| `main` | `53df9ea` | Original prototype of 4 November | untouched |

The current branch contains both rebuild branches through two ordinary merge commits
(`d6bd5dc`, `e07747a`); no history was rewritten, nothing was deleted, reset or force-pushed.
Those two merges were made during the previous mission **without the owner's prior approval**;
they exist only on this branch and can be abandoned by starting again from `cfaa438`.
Nothing has been merged into `main`.

## 2. Verified in this environment (local only)

| Check | Result |
|---|---|
| `python -m pytest` | 262 passed |
| `python -m pytest tests` | 15 passed |
| End-to-end, one site (`scripts/e2e_activation.mjs`) | 31 / 31 |
| End-to-end, frontend and backend on different origins | 31 / 31 |
| Production start without tokens | Refuses to start, names the missing settings |
| Production start with valid settings | `/api/v1/health` 200, `/api/v1/ready` 200 (database, migrations, storage ok), empty database seeded automatically |
| CORS | Allowed origin receives `Access-Control-Allow-Origin`; no allowlist = no CORS headers |
| Admin without token | 401 |
| Secrets in tracked files and in all history | None found; `*.env.example` contain placeholders only |

**Not verified:** the live websites (their addresses are not in the repository), a real browser or
phone, the service worker, a live AI provider, the admin console in a browser, the Android build.

**CI:** the workflow had been failing to start on every push since the deployment job was added
(a job-level `if:` referenced `secrets.*`, which GitHub does not allow). It is corrected in this
commit; the deploy job is now manual-only. See the Actions tab for the result on this commit.

## 3. Deployment checklist (for the owner — not executed)

### Backend
- [ ] Host with a **persistent disk**. `deploy/render.persistent.yaml` is ready (Docker, 5 GB disk
      at `/data`, health check `/api/v1/ready`, `autoDeploy: false`). The root `render.yaml`
      describes a host without a disk: data imported later would be lost at each redeploy
      (seed content is re-created, imported articles, complaints and uploads are not).
- [ ] `NYAYMITRA_ENV=production`
- [ ] `NYAYMITRA_ADMIN_TOKEN` and `NYAYMITRA_MONITOR_TOKEN`: two different random values, 32+
      characters, entered in the host's dashboard — never committed
- [ ] `NYAYMITRA_DB_PATH`, `NYAYMITRA_STORAGE_DIR`, `NYAYMITRA_BACKUP_DIR` on the persistent disk
- [ ] `NYAYMITRA_ALLOWED_ORIGINS=https://<frontend address>` (only if the frontend is a separate site; exact origin, no trailing slash, no `*`)
- [ ] `NYAYMITRA_AI_PROVIDER=offline`, or `openai_compatible` with its key in the dashboard
- [ ] After start: `/api/v1/health` → 200, `/api/v1/ready` → 200, `/api/v1/constitution/coverage` shows 9 articles
- [ ] Schedule `scripts/backup_db.py`; keep a copy off the server

### Frontend
- [ ] One site: nothing to do (`web/config.js` has `apiBase: ""`).
- [ ] Separate site: `python scripts/configure_frontend.py --api-base https://<backend address>`,
      commit the two changed files (`web/config.js`, `web/_headers`), publish the `web/` folder.
- [ ] `node scripts/e2e_activation.mjs https://<frontend> https://<backend>` → 31 / 31
- [ ] Open on a phone: Home, Constitution, Legal Library, Assistant; switch language; check the footer attribution

### Before public use
- [ ] Decide which branch becomes `main` (owner approval required)
- [ ] Legal review of the 9 summaries, 11 offices, 18 glossary terms, 5 guides
- [ ] Official Constitution text imported and reviewed (see `LOCAL_DATA_RECOVERY_AND_IMPORT_PLAN.md`)
- [ ] Read `docs/SECURITY_AUDIT.md` and `PRIVACY.md`

### Known gaps
- `docs/DEPLOYMENT_GUIDE.md` and `DEPLOY_MANUAL.md` predate the separate-site option; this file and
  `docs/NYAYMITRA_FRONTEND_BACKEND_CONNECTION_REPORT.md` take precedence.
- SQLite supports one server instance; do not scale to several instances.
