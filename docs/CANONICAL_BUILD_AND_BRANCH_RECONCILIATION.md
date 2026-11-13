# Branch Reconciliation and Canonical Build

**Date:** 2026-11-12 · **Branch:** `arena/2497125a-nyaymitra-2-0`
**Status:** reconciliation complete and verified · **nothing deployed** · **nothing force-pushed** · **no branch deleted**

This document ends the "which branch is the real NYAYMITRA 2.0?" ambiguity. It records what every
branch contained, why the canonical branch was chosen, exactly what was merged, and the evidence for
the result.

---

## 1. Canonical branch

| | |
|---|---|
| **Canonical branch** | `arena/08f8f3c5-nyaymitra-2-0` |
| **Canonical HEAD** | `72e5139` (2026-11-12T15:11:10Z) |
| **Reconciled branch** | `arena/2497125a-nyaymitra-2-0` → see `git log` for current HEAD |
| **Files tracked** | 315 |
| **Product version / API version** | 2.0 / `2.1.0` |

The canonical implementation was **not** chosen because it has the highest test count. It was
chosen because it is the only branch that is simultaneously (a) complete across every layer,
(b) integrated end to end, (c) schema-consistent, and (d) a **superset** of the other branches
rather than a competing variant. Section 3 gives the evidence.

---

## 2. Branch comparison (measured, not inferred)

All figures below were produced by inspecting the trees in this session, not from commit messages.

| | `main` | `arena/812d6894` | `feature/hackindia-deployment` | **`arena/08f8f3c5`** |
|---|---|---|---|---|
| HEAD | `53df9ea` | `2b6ad10` | `6de0f62` | `72e5139` |
| Commits | 16 | 48 | 48 | 61 |
| Files | 19 | 178 | 248 | **311** |
| Python files / test files | 7 / **0** | 77 / 17 | 77 / 17 | **97 / 21** |
| API routers | 0 | 9 | 9 | **11** |
| Migrations (`.sql`) | 0 | 8 | 8 | **10** (5 up + 5 down) |
| Frontend | `frontend/index.html` monolith, CDN Tailwind | `web/` SPA | `web/` SPA | **`web/` SPA + `web/config.js`** |
| — loads JS files? | none referenced (dead code) | yes | yes | **yes** |
| — calls backend? | **zero `fetch`/XHR** | yes | yes | **yes** |
| Database schema | committed DB contradicts `database.py` | 4 migrations | 4 migrations | **5 migrations (001–005)** |
| Constitution data | 2,125 Santhali PDF fragments (junk) | 9 summaries, 2,125 quarantined | same | **9 summaries, 2,125 quarantined** |
| Authoritative text records | 0 (and falsely labelled) | 0 | 0 | **0 (correctly labelled)** |
| Library module | none | `GET /library` | `GET /library` | **`GET /library` + `services/library.py`** |
| Assistant | client-side keyword counter over 3 objects | grounded offline composer + RAG | same | **same + requested-article recognition** |
| Multilingual | 3 hard-coded dicts in one HTML file | **en/gu only** | en/gu only | **`languages.py` (308 lines), 23 locales, `/languages` router, migration 005** |
| RTL (ks/sd/ur) | no | no | no | **yes** |
| Tests actually run | n/a (none) | **240 passed** | not run (branch already an ancestor) | **389 passed** |
| Tool tests | 0 | 15 | 15 | **15 passed** |
| CI | none | workflow exists but **deploy job fails to start** | same bug | **fixed (manual-only deploy), green** |
| `web/config.js` (separate-site) | – | **absent** | absent | **present** |
| Deployment configs | 0 | 5 | 7 | 7 |
| Android/Capacitor | no | no | yes | **yes** |
| Unique files | 0 | `docs/PHASE_3C_REPORT.md` | 0 | 134 vs 812d6894 |
| Ancestor of canonical? | **yes** | no (1 commit ahead) | **yes** | — |

### 2.1 The decisive structural fact

```
git merge-base --is-ancestor origin/main  origin/arena/08f8f3c5   -> TRUE   (main fully contained)
git merge-base --is-ancestor origin/feature/hackindia ...         -> TRUE   (fully contained)
origin/arena/812d6894..origin/arena/08f8f3c5                         14 commits ahead, 1 behind
```

- **`main` has 0 commits not already on the canonical branch.**
- **`feature/hackindia-deployment` has 0 commits not already on the canonical branch**, and the
  canonical branch removed **nothing** from it (file-level diff is purely additive).
- **`arena/812d6894` had exactly one commit the canonical branch lacked:** `2b6ad10`, which adds a
  single documentation file (`docs/PHASE_3C_REPORT.md`, 426 lines). Merged in §4.

There were therefore **no competing implementations to choose between** for `main` and `hackindia` —
the canonical branch already contained them. The only genuine delta was one document.

---

## 3. Why this branch is the canonical implementation

| Criterion | Evidence |
|---|---|
| **1. Functional completeness** | 41 API operations, 11 routers, 21 tables, 8 citizen routes + admin console, PWA, Android shell. No other branch has the library or languages layers. |
| **2. Frontend/backend integration** | `web/app.js` issues real requests through `web/config.js`; verified `/api/v1/*` returning 200 against a live server. `main` has **zero** network calls. |
| **3. Database consistency** | 5 migrations apply cleanly to an empty database; full rollback 001→005 verified to leave only `schema_migrations` with `integrity_check = ok`. `main`'s committed DB contradicts its own `database.py` (`no such column: title_gu`). |
| **4. Source-grounded assistant** | Retrieval-before-generation; out-of-corpus question returns `grounded:false`, `citations:[]`. `guard.py` is **byte-identical** to the 812d6894 version — the reconciliation did not weaken safety. |
| **5. Library functionality** | `GET /api/v1/library` returns `total: 43` (9 articles + 11 departments + 5 triage + 18 glossary). Absent as a unified endpoint on other branches. |
| **6. Test coverage** | **389 backend + 15 tool tests pass, 92% coverage** (3,158 statements, 265 missed). No test file or test function was removed relative to 812d6894 (checked function-by-function). |
| **7. Security** | admin 401 without token / 200 with; CSP self-only; PII redaction; owner-only file modes; rate + body limits. CI greps for external assets and inline styles. No secrets in tracked files (every `sk-`/`ghp_` hit is a test fixture or a PDF binary artefact). |
| **8. Deployment readiness** | Dockerfile, systemd unit, Render persistent-disk config, Cloudflare Pages, Android. **0 deployments executed.** |
| **9. Maintainability** | Routers → services → db layering; 5 reversible migrations with checksums; 27 documents; CI on Python 3.11 **and** 3.12. `main` is a 1,832-line single HTML file. |
| **10. Multilingual expansion** | The only branch with a language registry, 23 locale catalogues, script detection for 23 scripts, RTL, and per-language text storage with provenance. |

---

## 4. What was merged (exact commits)

| Step | Operation | Result |
|---|---|---|
| 0 | Tag `checkpoint/pre-reconciliation` at `53df9ea` | local checkpoint |
| 1 | `git merge --ff-only origin/arena/08f8f3c5-nyaymitra-2-0` | fast-forward `53df9ea → 72e5139`; +311 files; no new commit, no rewrite |
| 2 | `git merge --no-ff origin/arena/812d6894-nyaymitra-2-0` | merge commit `348d4a8`; brings `docs/PHASE_3C_REPORT.md`; **0 conflicts** |
| 3 | Preserve remaining `main` files into quarantine | commit `f03d276`; 3 files restored byte-identically + README addendum |
| 4 | Canonical-build record | this document |

**No conflict arose in any step**, so no judgement call about losing functionality was required.

### 4.1 Features preserved from each branch

| From | Preserved |
|---|---|
| `main` | `LICENSE` (identical). `frontend/index.html` → `frontend/legacy/index.html` (identical). `frontend/app_core.js`, `frontend/build_library_js.py` → `frontend/legacy/` (identical). `extract_real_library.py`, `integrate_real_engine.py`, `long_deep_migration.py`, `setup_full_library.py` → `scripts/legacy/` (identical). **This reconciliation added:** `backend/database.py` → `scripts/legacy/database.py`, `frontend/library_fix.js` → `frontend/legacy/data/library_fix.js`, `frontend/interactive_library.js` → `frontend/legacy/data/interactive_library.js` (all SHA-256 identical to `origin/main`). `frontend/index_v2.html` deliberately not restored — **byte-identical duplicate** of `index.html`, so restoring it would preserve a duplicate, not a file. |
| `arena/812d6894` | Everything (it is 47/48 shared); plus `docs/PHASE_3C_REPORT.md`. |
| `feature/hackindia-deployment` | Everything — PWA, Capacitor Android, Cloudflare config, submission package, independent verification report. Zero removals. |
| `arena/08f8f3c5` | Everything else: library, languages, migration 005, data activation, multilingual registry. |

### 4.2 Duplicate implementations deliberately **not** carried forward

| Duplicate | Resolution |
|---|---|
| Two `constitution_articles` schemas (`database.py` vs. committed `.db`) | Superseded by migration 001. Old file archived, never imported. |
| Triage knowledge authored 3–4 times (backend `main.py`, `index.html` inline, `app_core.js`) | Single source: `data/seed/triage_seed.json`. |
| `index_v2.html` (byte-identical twin) | Not restored. |
| `library_fix.js` vs `data/legacy/*.jsonl.gz` | Same 2,125 rows. Authoritative copy = gzip + `legacy_import_chunks`; the JS blob kept only as the shipped artefact. |
| Two databases | One committed DB on `main` (junk, removed from the served path). Canonical branch has **no** committed database; `NYAYMITRA_DB_PATH` is environment-configured. |

### 4.3 Conflicting schemas / incompatible migrations

**None.** The canonical branch has a single migration chain (001–005) with checksums recorded in
`schema_migrations`. The other branches share migrations 001–004; 005 is additive. No branch
defined a conflicting version of the same migration number.

---

## 5. Branch and `main` strategy

**Constraint:** this session may push **only** to `arena/2497125a-nyaymitra-2-0`. It cannot push to
`main` and cannot create branches. Therefore:

- The validated reconciliation lives on `arena/2497125a-nyaymitra-2-0`.
- `main` was **not** modified, force-pushed, or deleted.
- Promoting `main` requires an action this session is not permitted to take. Recommended, in order:

```bash
# Option A (recommended): fast-forward main to the verified reconciliation
git push origin arena/2497125a-nyaymitra-2-0:main          # fast-forward, no rewrite
# Option B: review it through a PR first
gh pr create --base main --head arena/2497125a-nyaymitra-2-0 \
  --title "Reconcile NYAYMITRA 2.0 into one canonical implementation"
```

Both are non-destructive: `main` is an ancestor of the reconciliation, so either is a
fast-forward. **Nothing was done automatically**; deployment also remains manual.

### 5.1 Pre-change gates for `main`

| Gate | Result |
|---|---|
| Canonical implementation passes tests | **PASS** — 389 + 15 |
| Migrations work on a clean database | **PASS** — 5 applied to an empty DB; rollback verified |
| Frontend/backend API integration | **PASS** — live server, real endpoints |
| No secrets committed | **PASS** — all hits are test fixtures / PDF binary |
| No false legal-data claims | **PASS** in tracked files. **FAIL in GitHub repository metadata** — the description still reads "Gemini Production Engine" and the API token lacks permission to change it. Owner action required (§7). |
| All useful features preserved | **PASS** — see §4.1 |

---

## 6. Verified state of the reconciliation

Run in this session on `arena/2497125a-nyaymitra-2-0`:

| Check | Result |
|---|---|
| `pytest backend/tests` | **389 passed**, 1 deprecation warning |
| `pytest tests/` | **15 passed** |
| Coverage (`--cov=backend/app`) | **92%** |
| Clean-DB bootstrap | 5 migrations applied, 21 tables, seeded 9/11/5/18/15 + 2,125 quarantined |
| Migration rollback 005→001 | leaves only `schema_migrations`, `integrity_check = ok` |
| 23 locale catalogues | all present, none missing, none extra |
| 23 scripts resolve + auto-detect | no failures; RTL = `ks`, `sd`, `ur` |
| Legacy quarantine intact | `constitution_articles_legacy_2026-11-07.jsonl.gz` sha256 `b59f00b8…`, 2,125 records |
| Legacy artefacts reachable from the app | **no** — only `web/` is served; zero references |
| Developer attribution | present in `LICENSE`, `README.md`, `web/index.html`, `web/admin.html`, and asserted by tests |

---

## 7. Remaining blockers (unchanged by reconciliation)

| ID | Blocker | Owner action |
|---|---|---|
| **B-1** | **0 authoritative Constitution texts** (`article_texts` = 0). 9 articles are owner-written summaries. | Put the official India Code / Legislative Department PDF in `data/raw/`, dry-run `scripts/ingest_constitution.py`, then `--apply --backup` |
| **B-2** | **0 human-verified records** (9 articles, 11 departments, 5 triage guides, 18 glossary terms). | Appoint a named reviewer; record `checked_by` + `last_checked_at` in `/admin` |
| **B-3** | **No real browser / device / screen-reader / microphone test.** | Open it on a phone over the LAN; record pass/fail per screen |
| **B-4** | **Live LLM never exercised** (no API key). | Run `scripts/verify_ai_provider.py` against a real endpoint |
| **B-5** | **`main` cannot be promoted by this session**, and its GitHub description still carries a false claim. | Owner runs one of the two commands in §5, and edits the repository description |

---

## 8. Multilingual status model (Phase 6)

Four independent statuses are kept distinct, and the API reports them separately:

| Status | Meaning today |
|---|---|
| **Interface localization** | 2 languages `PROJECT_AUTHORED` (gu, en); 21 `MACHINE_TRANSLATED` and explicitly labelled unreviewed |
| **Machine translation** | Never applied to the Constitution. Interface labels only. |
| **Official text** | **0 articles in every language.** `text_en`/`text_gu` are `NULL` by design until ingestion. |
| **Human-verified legal content** | **0 records in every language.** |

No branch, document, or API response in the reconciliation claims otherwise. The offline composer
now labels each citation `[સમજૂતી — સત્તાવાર લખાણ નથી]` / `[explanation — not the official text]`
or `[… human verification pending]`, so the distinction is visible in the answer itself.

---

## 9. What was **not** done

- No deployment, no release, no tag other than the local `checkpoint/pre-reconciliation`.
- No force-push, no history rewrite, no branch deletion.
- `main` unchanged.
- No legal content invented, translated, or marked verified.
- No test deleted or skipped to make the suite pass.
