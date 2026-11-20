# MASTER PROJECT CONTEXT

**NYAYMITRA 2.0 — Bharat Multilingual Legal Access System**

**Created & Developed by Bambhaniya Divyesh Nonghanbhai**

---

| | |
|---|---|
| **Canonical repository** | `dhundhwana-arch/Nyaymitra-2.0` |
| **Canonical branch** | `arena/2497125a-nyaymitra-2-0` |
| **Pull request** | **#2** — open, not draft, `MERGEABLE`/`CLEAN`, **0 reviews**, not merged |
| **Latest commit at time of writing** | see §3 — re-verify with `git log -1` |
| **Product / API version** | 2.0 / `2.1.0` |
| **Licence** | MIT, © 2026 Bambhaniya Divyesh Nonghanbhai |
| **Deployment status** | **Nothing is deployed.** 0 deployments, 0 environments, no Pages site, 0 releases, 0 tags. |

**This document is the single source of truth for project state.** Where it conflicts with an older report, **this document wins** — it was written from direct measurement at the commit named in §3. Other documents are historical artefacts; several are stale (§10.3).

---

## 1. Project purpose and boundaries

NYAYMITRA 2.0 helps a citizen of India **understand** a legal problem and **navigate** to the right remedy: describe the problem in Gujarati or English, find the constitutional provision that applies, understand the official next step, prepare a complaint draft, and reach the correct department or free-legal-aid channel (NALSA/DLSA, helpline 15100).

**What it is:** legal *information* and navigation assistance.

**What it is not — and must never be described as:**
* Not a lawyer, not a court, not a judge.
* Not legal advice. It does not decide cases, predict outcomes or guarantee results.
* Not a system that presents unverified material as official law.

**The governing rule of the whole codebase:** every legal statement carries `requires_human_verification` until a qualified reviewer signs off, and the database enforces this by default. No legal text is invented, translated automatically, or silently upgraded.

---

## 2. Canonical repository and branch

```
dhundhwana-arch/Nyaymitra-2.0
  main                          53df9ea   unchanged since 2026-11-04 (original prototype)
  arena/2497125a-nyaymitra-2-0  510f62f   ← CANONICAL, PR #2 head
  arena/08f8f3c5-nyaymitra-2-0  5922fe4   superseded, ancestor of canonical
  arena/812d6894-nyaymitra-2-0  2b6ad10   superseded, ancestor (PR #1, draft)
  feature/hackindia-deployment 6de0f62   superseded, ancestor
```

**Verified ancestry property:** `git rev-list --count origin/<any-branch> ^510f62f` returns **0** for every branch. No commit exists in this repository that is not reachable from canonical. Nothing is stranded.

**`main` is a broken prototype** (19 files, fails at `ImportError`, raises `no such column: title_gu`). It is an ancestor of canonical, so promoting canonical is a **pure fast-forward** that rewrites nothing:

```bash
git push origin 510f62f9fdf4f8ea18062e8262bbbbfb7d8f1a83:main
```

This has **not** been run. It requires the owner's explicit approval, and the PR has 0 reviews.

---

## 3. Latest commit

**Recorded at writing:** `342103eca3e209e10bd705a2ac5c48225c9afe13` — the final-preservation commit that added `PROJECT_FINAL_STATUS.md`, `COMPLETED_WORK_INVENTORY.md`, `GEMINI_HANDOVER.md` and `docs/INDEX.md`.

**Always re-verify rather than trusting this line:**

```bash
git fetch origin && git log -1 --format='%H %s' origin/arena/2497125a-nyaymitra-2-0
```

**Recent history (most recent first):**

| SHA | Subject |
|---|---|
| `342103e` | docs: preserve the HackIndia readiness and project status audit |
| `23a4908` | docs: add master project context and conversation consolidation report |
| `510f62f` | docs: update the release checklist to the post-Phase-4A test counts |
| `ea82500` | Integrate Phase 4A read-only recovery tooling (5922fe4) |
| `a15bf7e` | docs: correct stale release-readiness and identity claims |
| `9ee6b8e` | Integrate Phase 4 Constitution importer (667fa78) |
| `93f70d5` | docs: record the AGPL-3.0 exposure of the optional ingestion dependency |
| `aba64e1` | docs: canonical build and branch reconciliation record |

---

## 4. Complete module inventory

Status labels: **1** COMPLETE AND VERIFIED · **2** IMPLEMENTED BUT NOT FULLY VERIFIED · **3** PARTIALLY IMPLEMENTED · **4** DOCUMENTATION ONLY · **5** NOT IMPLEMENTED · **6** BLOCKED

| Module | Status | Location | Actual functionality | Remaining work |
|---|---|---|---|---|
| Backend core | **1** | `backend/app/main.py` + 48 files | App factory, 10 routers, lifespan, structured logging, request IDs | none |
| Database & migrations | **1** | `backend/migrations/001…006` | 6 up + 6 down; apply clean to empty DB → 21 tables, 30 indexes; full `006→001` rollback verified | none |
| Constitution library | **1** mechanism / **6** content | `services/constitution.py`, `data/seed/constitution_seed.json` | Serves 9 articles w/ governance metadata; coverage endpoint reports 9 of 395 | **BLOCKED: 0 authoritative texts** |
| AI assistant (RAG) | **1** | `backend/app/ai/` (809 lines) | FTS5/`bm25` retrieval (max 4 rows), citation validation, refusal when ungrounded | none (offline path) |
| Live LLM provider | **2** | `ai/openai_compatible.py` | httpx client, timeout, retry/backoff on 429/5xx | **Never exercised** — no API key |
| Complaint drafting | **1** | `services/complaints.py`, `routers/complaints.py` | Preview → confirm → reference + one-time token; sha256 token storage; idempotency + fingerprint dedupe | none |
| Document management | **1** | `services/documents.py` | PDF/JPEG/PNG/WEBP upload, sha256, honest `extraction_status` | OCR never run (by policy) |
| Department navigation | **1** | `services/departments.py` | 11 departments | content unverified |
| Legal triage | **1** | `services/triage.py` | 5 guides | content unverified |
| Glossary | **1** | `services/glossary.py` | 18 terms, gu/en | content unverified |
| Legal Library | **1** | `services/library.py` | 43 items, search, category + language filters | none |
| Multilingual system | **1** architecture | `backend/app/languages.py`, `web/locales/` | 23 languages; per-language statuses; RTL for `ks`, `sd`, `ur` | 21 locales at 5–10 % (see §9) |
| Frontend SPA | **1** | `web/` (1,636 lines) | 8 routes; self-hosted, no CDN, CSP-compliant | no real-device test |
| Admin console | **1** | `web/admin.html`, `routers/admin.py` | Token-gated stats/metrics/verification-queue/review-packet | no MFA |
| Auth & security | **1** | `security.py`, `middleware.py` | Strict CSP, `X-Frame-Options: DENY`, sha256 tokens + `compare_digest`, hashed IPs, redacted audit log | shared operator tokens |
| Monitoring | **1** | `metrics.py`, `services/monitoring.py` | `/admin/metrics`, per-request IDs, AI usage/health | no external scraper |
| Backup & recovery | **1** | `scripts/backup_db.py`, `purge_data.py` | Integrity-checked snapshot; retention purge (dry-run default) | rotation/scheduling = operator job |
| Phase 4 importer | **1** | `services/structured_import.py` (867), `diglot.py`, `scripts/import_constitution_data.py` | CSV/TSV/JSON/JSONL/TXT/PDF/folder; header mapping; quality report; backup-then-apply; `rollback RUN_ID` | needs the owner's files |
| Phase 4A recovery tool | **1** | `scripts/inventory_local_data.py` (646) | Read-only inventory; secrets never packaged; SHA-256 manifest + archive; originals verified untouched; SQLite `mode=ro&immutable=1` | needs the owner's machine |
| PWA | **2** | `web/sw.js`, `manifest.webmanifest`, 10 icons | Offshore app-shell fallback, **no API caching** (privacy), installable | never tested on device |
| Voice I/O | **2** | `web/app.js:353,429` | `speechSynthesis` + `webkitSpeechRecognition` | **untested — do not demo** |
| Deployment config | **3** | `Dockerfile`, `deploy/`, `render.yaml`, `wrangler.toml`, `ci.yml` | Hardened systemd, non-root Docker, manual-gated Pages job | **nothing deployed** |
| Android (Capacitor) | **3** | `android/` (53 files) | Wrapper + assets, `appId: in.nyaymitra.app` | APK never built |
| Legacy Santali corpus | **1** quarantined | `data/legacy/*.jsonl.gz` | 2,125 rows, sha256 verified, 0 markers on public endpoints, admin-only | correctly inert — do not "fix" |
| Live LLM end-to-end | **5** | — | — | optional |

### 4.1 API surface

`/api/v1/` — `health` · `ready` · `meta` · `constitution/{articles,parts,coverage,articles/{id},articles/{id}/text}` · `departments` · `library` · `languages` (+`/detect`) · `ai/{explain,terminology,glossary}` · `complaints` (+`/preview`, `/{reference}`) · `documents` (+`/{id}`, `/{id}/content`) · `feedback` · `admin/*` (16 endpoints, token-gated).

**`/api/docs` is 404 by design** — Swagger's CDN assets would violate the self-only CSP. Use **`/api/openapi.json`**. Never re-add `/docs`.

### 4.2 Seed data (the entire legal corpus)

| Dataset | Count |
|---|---|
| Constitution articles | **9** (all `owner_authored_summary`, 0 with `text_en`/`text_gu`) |
| Legal sources | 15 |
| Departments | 11 |
| Triage guides | 5 |
| Glossary terms | 18 |
| Quarantined legacy rows | 2,125 |

---

## 5. Verified functionality

Measured on `510f62f`, isolated `/tmp` databases, **no API key, no network dependency**.

| Capability | Evidence |
|---|---|
| Starts from nothing | applies 6 migrations, seeds 2,165 rows, logs `app.started` |
| Gujarati question answered | `grounded: true`, cites Article 14, 677-char answer |
| Provenance labelling | answer carries `[સમજૂતી — સત્તાવાર લખાણ નથી]` ("explanation — not the official text") |
| Refuses nonsense | `zzz qqq` → `grounded: false`, `citations: []`, "I do not have verified information" |
| Complaint end-to-end | preview → confirm → reference; retrieval with token 200, **without token 422** |
| Document upload | PDF accepted, sha256 stored, `extraction_failed` reported honestly |
| Admin gating | all admin endpoints **401 without token, 200 with** |
| RTL | `root.dir` switching + `[dir="rtl"]` CSS; `ks`/`sd`/`ur` |
| PWA | valid manifest (10 icons, 2 shortcuts), SW registered |

---

## 6. Test results

**Provenance matters.** The rows marked **NEW** were executed during the final-preservation session on 2026-11-12 against the tree now at `342103e`. Rows marked **HIST** were executed in an earlier session and were **not re-run** during final preservation.

| Suite | Command | Result | Run |
|---|---|---|---|
| Backend | `pytest backend/tests -o addopts=""` | **460 passed** | **NEW** |
| Source tools | `pytest tests -o addopts=""` | **15 passed** | **NEW** |
| **Total** | | **475 passed**, 0 failed | **NEW** |
| Coverage | `--cov=backend/app` | **92 %** (3,932 statements, 328 missed) | **NEW** |
| DB bootstrap | `scripts/init_db.py` on empty `/tmp` DB | 22 tables, 30 indexes, seeds loaded | **NEW** |
| DB integrity | `scripts/check_db.py` | `RESULT: OK`, 30 indexes, 0 missing | **NEW** |
| Collection | `pytest --collect-only` | 460 collected (342 test functions + parametrisation) | **NEW** |
| E2E (jsdom) | `node scripts/e2e_activation.mjs <fe> <be>` | 43/43, 143 calls, 0 blocked | HIST |
| Smoke | `node scripts/smoke_web.mjs <url>` | OK | HIST |
| Dependency audit | `pip-audit -r backend/requirements.txt` | no known vulnerabilities | HIST |
| Frontend syntax | `node --check` ×5 | OK | HIST |
| CI | GitHub Actions | green on Python **3.11 and 3.12** | HIST |
| **Real device / AT test** | — | **NEVER PERFORMED** | — |

Re-run the HIST rows before any demo or submission. Their commands are in `GEMINI_HANDOVER.md` §6.

**Traps when reproducing:**
* `pytest.ini` sets `addopts = -q`; a second `-q` hides the summary. Always pass `-o addopts=""`.
* `pytest tests/` needs `pymupdf` from `requirements-ingestion.txt`.
* E2E and smoke share one per-IP rate-limit bucket (read 120, admin 10 per 60 s) — **run E2E first** or restart the server, else false "0 articles" failures appear.

---

## 7. Legal-data verification status

| Metric | Value |
|---|---|
| Articles in the corpus | **9** |
| Authoritative (official) texts | **0** |
| Human-verified statements | **0** |
| Owner-authored explanations | **9** |
| Articles with `text_en` / `text_gu` | 0 / 0 |
| Departments verified | 0 |
| Quarantined Santali rows | 2,125 (sha256 `b59f00b8…`) |

**Enforced by the schema, not by convention:** `article_texts.verification_status` defaults to `requires_human_verification` under a `CHECK` constraint, and ingestion never writes `verified`. A row cannot arrive as `VERIFIED` by accident.

**Never claim** that the Constitution is loaded, that the content is verified, or that this is legal advice.

---

## 8. Deployment status

**Nothing is deployed.** Verified: `deployments: []`, `environments: 0`, Pages site **404**, releases 0, tags 0. The Pages deploy job is gated to `workflow_dispatch` + `refs/heads/main` and has never run.

**Deployment is NOT recommended yet.** Per `docs/RELEASE_READINESS_CHECKLIST.md`:
* **Stage A (engineering merge): READY.**
* **Stage B (supervised evaluation): NOT READY** — B-1 (no authoritative texts) and B-2 (no human verification) are open.
* **Stage C (public release): NOT READY** — additionally needs legal review, DPIA, pen test, accessibility audit, load test, WAF, per-user accounts with MFA.

Before any deployment: set `NYAYMITRA_ENV=production`, generate two distinct 32-byte tokens, point `NYAYMITRA_DB_PATH` **outside** the checkout, terminate TLS at a proxy, install backup **and** retention cron. The app **refuses to start** with placeholders, weak/identical tokens, or a DB inside the repo.

---

## 9. Known limitations

1. **No authoritative legal text** (B-1) and **no human verification** (B-2) — the defining limitation.
2. **9 articles of 395** — the corpus covers a fraction of the Constitution.
3. **Localisation:** Gujarati **95 %**, English 100 %, **the other 21 languages 5–10 %** and machine-translated with `review: none`. Say *"23-language interface, Gujarati complete"* — never *"23 languages supported"*.
4. **Legal content exists only in Gujarati/English**; other languages see English with a notice. The Constitution is never machine-translated.
5. **No real-device or assistive-technology test** (B-3).
6. **Live LLM never exercised** (B-4).
7. **Voice I/O untested** — do not demo.
8. **Rate limits are tighter than the E2E scripts assume** (documented as `KNOWN_LIMITATIONS` #32).
9. **AGPL exposure:** `pymupdf` (AGPL-3.0) is in `requirements-ingestion.txt` only — **not** in `backend/requirements.txt`, **not** in the Dockerfile, **not** imported by `backend/app/**`. Absent from the runtime image. Review before distributing ingestion tooling.
10. **Shared operator tokens**, no MFA (residual risk R-7).
11. **Backup rotation not implemented** — operator responsibility.
12. **APK never built.**
13. **`GET /health` is 404** — use `/api/v1/health`.

---

## 10. Outstanding tasks

### 10.1 Owner actions (cannot be done from an agent session)

| # | Task | Why it matters |
|---|---|---|
| 1 | **Merge PR #2** (fast-forward) | 0 reviews is the only merge blocker |
| 2 | **Fix the GitHub repository description** | still reads *"…(Gemini Production Engine)"* — false; there is no Gemini engine and nothing is in production. `gh repo edit` → **403** from automation. Approved text: `NYAYMITRA 2.0 \| Bharat Multilingual Legal Access System` (recorded in `docs/REPOSITORY_IDENTITY.md`) |
| 3 | **Supply official Constitution PDFs (EN + GU)** | closes **B-1** |
| 4 | **Named human reviewer sign-off** | closes **B-2** |
| 5 | **Deploy** (Cloudflare Pages + backend host) | submission-critical; config already exists |

### 10.2 Engineering backlog

Translate the remaining 21 locales; native-speaker review of Gujarati copy; real-device PWA test; accessibility/AT audit; live-provider evaluation; load test; per-user accounts with MFA; backup rotation; build the APK.

### 10.3 Stale documents — treat as historical, not current

`FINAL_PROJECT_COMPLETION_REPORT.md`, `FINAL_VERIFICATION_REPORT.md`, `DEPLOY_MANUAL.md`, `HACKINDIA_SUBMISSION.md`, `GOVERNMENT_SUBMISSION_PACKAGE/README.md` describe an earlier snapshot (226 tests, commit `8b1e652`, PR #1). **This document supersedes their numbers.** `docs/RELEASE_READINESS_CHECKLIST.md` was corrected in `a15bf7e`/`510f62f` and is current.

---

## 11. Important historical decisions

| Decision | Rationale |
|---|---|
| **`arena/08f8f3c5` chosen as the reconciliation source** | Not because it had the most tests — it had 312 files and the most complete implementation. Chosen on ten criteria documented in `docs/CANONICAL_BUILD_AND_BRANCH_RECONCILIATION.md`. |
| **Nothing was rewritten or force-pushed** | `main` is an ancestor; promotion is a fast-forward. History is intact and auditable. |
| **Legacy Santali corpus quarantined, not fixed** | The 2,125 rows were produced by a regex over ~1,000-character chunks of the Ol-Chiki PDF — page fragments with page markers, not articles. Recovering them needs a proper diglot/OCR pass (Phase 4). Preserved twice: gzip (sha256 `b59f00b8…`) + `legacy_import_chunks`. **Do not "repair" them.** |
| **Swagger disabled (`/api/docs` → 404)** | Swagger UI loads JS/CSS from a CDN, which violates the self-only CSP. `/api/openapi.json` is the schema endpoint. |
| **Offline provider is the default** | Deterministic, template-composed, structurally incapable of inventing a provision. The live provider is optional and never tested. |
| **`pymupdf` (AGPL-3.0) kept out of runtime** | Ingestion tooling only; the shipped application and image contain no AGPL code. |
| **23 languages, statuses kept distinct** | `UI_READY`, `UI_PARTIAL`, `SAMPLE_CONTENT_AVAILABLE`, `OFFICIAL_TEXT_AVAILABLE`, `HUMAN_VERIFIED`, `ASSISTANT_SUPPORTED` are never collapsed into one claim. |
  | **Phase 4 / 4A integrated as separate reviewable commits** | Preserves provenance (`667fa78`, `5922fe4` remain reachable) and allows independent revert. |

### 11.1 Which document to read

| Question | Document |
|---|---|
| What state is the project really in? | [`PROJECT_FINAL_STATUS.md`](PROJECT_FINAL_STATUS.md) |
| What exactly has been built, with evidence? | [`COMPLETED_WORK_INVENTORY.md`](COMPLETED_WORK_INVENTORY.md) |
| How do I continue without rebuilding anything? | [`GEMINI_HANDOVER.md`](GEMINI_HANDOVER.md) |
| Where is every document? | [`docs/INDEX.md`](docs/INDEX.md) |
| How was canonical chosen, and what was lost? | [`CONVERSATION_CONSOLIDATION_REPORT.md`](CONVERSATION_CONSOLIDATION_REPORT.md) |

---

## 12. Instructions for future development

### 12.1 Branch and merge discipline

* Work on `arena/2497125a-nyaymitra-2-0` only, unless the owner opens a new branch.
* **Never force-push. Never rewrite history. Never delete a branch that carries a decision record.**
* `main` is promoted only by the owner, by fast-forward, after review.
* Keep commits small and separately revertible; keep third-party work as its own merge commit so `git show <sha>` still isolates it.

### 12.2 Before any commit

```bash
pytest backend/tests -o addopts="" -q     # must be 460+ passed
pytest tests -o addopts="" -q             # must be 15 passed
node --check web/app.js web/admin.js web/config.js scripts/smoke_web.mjs scripts/e2e_activation.mjs
```

### 12.3 Database and data rules

* **Never point the app at `backend/justice_access.db`.** Use a `/tmp` or external `NYAYMITRA_DB_PATH`.
* Every migration needs a matching `.down.sql`; prefer additive DDL; never `DROP`/`DELETE` in an up-migration.
* **Never set `verification_status='verified'`** without a named human reviewer.
* **Never import Constitution text** unless the owner supplied the source and the run is journalled and reversible.
* Treat the Santali corpus as read-only and inert.

### 12.4 Frontend rules

* No CDN, no external font, no inline script — the CSP is `default-src 'self'`.
* `web/config.js` ships with `apiBase: ""` (same-origin). For a separately hosted frontend use `scripts/configure_frontend.py --api-base <url>`, which also rewrites the `_headers` `connect-src`, and set `NYAYMITRA_ALLOWED_ORIGINS` on the backend.
* Do **not** cache API responses in the service worker — they may contain personal data.

### 12.5 Honesty rules (the project's core discipline)

* Never describe the system as legal advice, as production-ready, or as containing the Constitution.
* Keep the four statuses distinct: interface localisation ≠ machine translation ≠ official text ≠ human-verified.
* If a number is not measured, say "not measured" — do not estimate in a document that reads as fact.
* When a document becomes stale, correct it or mark it historical. Do not leave a false claim standing.

### 12.6 Environment

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
.venv/bin/pip install -r requirements-ingestion.txt   # only needed for pytest tests/
NYAYMITRA_DB_PATH=/tmp/demo/n.db NYAYMITRA_STORAGE_DIR=/tmp/demo/docs \
NYAYMITRA_AI_PROVIDER=offline \
  .venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

`pip install --no-save jsdom` is required for the E2E and smoke scripts.

---

**Created & Developed by Bambhaniya Divyesh Nonghanbhai**
