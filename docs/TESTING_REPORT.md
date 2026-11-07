# Testing report

Everything below was executed on the branch `arena/812d6894-nyaymitra-2-0`. Nothing in this file is
projected or assumed; where something could not be tested, it says so.

Environment: Linux sandbox, Python 3.11.2, Node 22.22.3, SQLite 3.40, jsdom 25 (dev only).

## 1. Automated suite

```bash
python -m pytest
# 119 passed in 9.58s

python -m pytest --cov=backend/app --cov-report=term-missing
# TOTAL  2083 statements  204 missed  90%
```

| Module group | Tests | Result |
|---|---:|---|
| Startup, health, meta, static assets, a11y/CSP static checks | 15 | pass |
| Constitution search/detail/coverage/provenance | 13 | pass |
| AI: grounding, retrieval precision, guard, degradation, logging | 18 | pass |
| Complaints: validation, summary, preview, token gating | 12 | pass |
| Documents: type/size/name/token, attach, extraction status | 10 | pass |
| Admin & security: roles, audit, backups, limits, redaction, permissions | 24 | pass |
| DB, migrations, backups, seeding, ingestion | 14 | pass |
| Departments & feedback | 5 | pass |
| Frontend (jsdom journeys, separate script) | 12 checks | pass |

Coverage by area: `security.py` 89%, `middleware.py` 99%, `guard.py` 93%, `rag.py` 92%,
`textsearch.py` 96%, `routers/*` 78–100%, `openai_compatible.py` 40% (no API key — untested by
definition), `monitoring.py` 60% (hard-error paths).

### Proven-failing spot check

To make sure the suite is not vacuous, `guard.validate_answer` / `guard.scan_input` were temporarily
disabled and the AI tests re-run: **4 tests failed** (`test_model_answer_with_uncited_article_is_rejected`,
`test_guard_rejects_final_legal_decisions`, `test_guard_rejects_gujarati_outcome_guarantee`,
`test_guard_scans_input_patterns`). Restoring the guard turned them green again.

## 2. What the suite actually asserts

* **No invented law.** A model answer mentioning `Article 999` is rejected and replaced by the
  offline grounded answer (`degraded:true`, warning `model_rejected:*`).
* **No answer without sources.** `zzzz qqqq` returns `grounded:false` and `insufficient_sources`;
  a cyber-fraud question never cites Article 21A.
* **No verdicts.** “The accused is guilty…”, “you will definitely win”, “તમે ચોક્કસ જીતી જશો” are
  all rejected.
* **Unverified stays unverified.** `/meta` reports `verified_text: 0`; the verification endpoint
  returns 409 when an article has no authoritative text, 400 without a reviewer and date.
* **Authoritative text is never a paraphrase.** `/articles/14` returns `text_en: null` while the
  explanation is present, and the response carries the reason.
* **The fabricated legacy remedy text is unreachable.** Searches for “Constitutional Provision” /
  “Statutory Guidelines” never surface a `remedy` field.
* **Tokens are not recoverable.** Wrong token and unknown reference are indistinguishable (404),
  and the stored value is a 64-character SHA-256, not the token.
* **Uploads cannot lie about their type.** A `.pdf` containing plain text is rejected 415.
* **Admin cannot brute-force cheaply.** The admin bucket returns 429 after its limit.
* **Data survives.** Backup → integrity check → restore round-trip; seeding does not undo a human
  verification; all 2,125 legacy rows remain.

## 3. Frontend checks

Static (in pytest):

```bash
node --check web/app.js && node --check web/admin.js      # pass
```

* Every `src`/`href` referenced by `index.html` and `admin.html` returns 200.
  *This test was added because `/admin.js` was a 404: the admin page loaded with no JavaScript at
  all while every unit test passed.*
* No CDN/Google-Fonts/plain-HTTP references; no inline `<script>`; no inline `style` attributes.
* CSP has no `unsafe-inline` / `unsafe-eval`.
* 44 px minimum tap target, `prefers-reduced-motion`, media queries, `<html lang>`, viewport meta.
* Each dynamic control in `app.js` has a `<label for=…>`; `aria-live` and `aria-invalid` present.

Behavioural (jsdom, `scripts/smoke_web.mjs`, run against live `uvicorn`):

```
#/home           772 chars      #/assistant      409 chars
#/complaint      792 chars      #/library       2793 chars
#/departments   3441 chars      #/glossary      2761 chars
language       toggled en <-> gu            (html[lang] updated)
assistant       2100 chars  citations + disclaimer
library          473 chars  search result shown
glossary       18 terms -> 1 after filtering "FIR"
complaint      NYM-KWTR3G created through preview + confirmation
complaint      saved lookup form present: true
admin          stats=205 chars, queue=1263 chars, documents=149 chars
OK — all citizen journeys and the admin console worked
```

The complaint journey verifies the gate in the UI: the submit button is **disabled** until the
review checkbox is ticked, the preview appears before any write, and a reference plus token are
shown afterwards.

`/health`, `/ready`, `/meta`, every API endpoint, the four complaint/document token paths and the
admin console were also exercised over HTTP with `curl` against the running server.

## 4. Not tested (and why)

| Area | Status | Reason / what is needed |
|---|---|---|
| Real browser (Chrome/Firefox/Safari) | **NOT TESTED** | No browser binary in this environment; jsdom only |
| Mobile layout on a phone | **NOT TESTED** | No device/emulator; CSS breakpoints are static-asserted only |
| Voice input (Web Speech API) and speech synthesis | **NOT TESTED** | Requires microphone/speaker permission in a real browser |
| Gujarati rendering (font shaping) | **PARTIAL** | Text presence asserted; visual rendering needs a browser |
| Screen reader (NVDA/TalkBack) | **NOT TESTED** | Requires a human with assistive technology |
| Live AI provider | **NOT TESTED** | No API key; the fallback and rejection paths *are* tested |
| Official Constitution PDF ingestion | **NOT TESTED** | No official PDF supplied; parser tested on fixture text |
| GitHub Actions workflow | **COMPLETE** | Run 42404987197 (push) and 42404988506 (pull_request) both green: pytest on 3.11 and 3.12 plus the frontend job |
| Load/performance | **NOT TESTED** | No benchmark; single-process synchronous SQLite is the design limit |

## 4a. Continuous integration

`.github/workflows/ci.yml` ran on GitHub for this branch:

```
✓ pytest (python 3.11)       33s
✓ pytest (python 3.12)       39s
✓ frontend syntax checks (node 20)   9s
```

The pytest jobs run the full suite with coverage, then bootstrap a database from an empty
directory (asserting 9 articles, 2,125 quarantined legacy rows and the FTS5 table) and perform a
backup/restore round-trip. The frontend job runs `node --check` on both scripts and the smoke
script, and greps for external asset references and inline style attributes. The only annotations
were deprecation notices about the actions' Node runtime, not failures.

## 5. Manual test steps (for a reviewer with a browser)

1. `python scripts/init_db.py --info` then `uvicorn backend.app.main:app --port 8000`.
2. Open `/`. A red banner must say the official article text is not loaded.
3. Ask “કાયદા સમક્ષ સમાનતા શું છે?” → Article 14 with “requires human verification”.
4. Ask “મારા ખાતામાંથી પૈસા ઉપડી ગયા છે” → no article citations, explicit “no related article”
   line, and cyber-fraud guidance.
5. Switch to English; reload; the choice must persist.
6. Complaint route: short description → inline error; valid data → summary preview; untick/retick
   the confirmation box and watch the submit button state; submit; copy the reference and token.
7. Reopen the complaint with the token; a wrong token must show the same generic error.
8. Upload a PDF in the complaint form; check it is listed with `extracted`. Upload a `.txt`
   renamed `.pdf`; it must be rejected.
9. `/admin` with `NYAYMITRA_ADMIN_TOKEN`: stats, queue, redacted queries, errors, complaints
   metadata, documents, legacy rows; create a backup; check `backups/` has a new file.
10. Resize to 360 px wide and check no horizontal scrolling; tab through the form and confirm
    focus rings are visible.
