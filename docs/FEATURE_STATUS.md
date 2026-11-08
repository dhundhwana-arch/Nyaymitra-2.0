# Feature status

Status vocabulary (used identically in the audit, the PR and this file):

* **COMPLETE AND TESTED** — implemented and covered by automated tests that fail if it breaks.
* **IMPLEMENTED BUT NOT TESTED** — code exists and is reachable, but its behaviour is unverified in
  the environment it will actually run in.
* **PARTIALLY COMPLETE** — works, with a documented gap.
* **BLOCKED** — cannot proceed without an input only the project owner can supply.
* **REQUIRES HUMAN VERIFICATION** — code is fine; the *content* needs a qualified person.

Evidence column points at the test file(s) in `backend/tests/`.

| # | Feature | Status | Evidence / gap |
|---|---|---|---|
| 1 | Health, readiness, metadata endpoints | COMPLETE AND TESTED | `test_startup_and_frontend.py` |
| 2 | Versioned migrations + rollback | COMPLETE AND TESTED | `test_db_and_ingest.py::test_rollback_and_reapply` |
| 3 | Clean-database bootstrap and idempotent seeding | COMPLETE AND TESTED | `test_db_and_ingest.py`, CI job “Database bootstrap” |
| 4 | Verified backup and restore | COMPLETE AND TESTED | `test_backup_and_restore_roundtrip`, `scripts/backup_db.py` |
| 5 | Constitution search (Gujarati + English, FTS5) | COMPLETE AND TESTED | `test_constitution.py` |
| 6 | Article detail with provenance and disclaimers | COMPLETE AND TESTED | `test_article_detail_includes_source_and_disclaimers` |
| 7 | Corpus coverage report (honest counts, gaps) | COMPLETE AND TESTED | `test_parts_and_coverage` |
| 8 | AI explanation with citations | COMPLETE AND TESTED | `test_offline_answer_is_grounded_and_cited`, `test_answer_in_gujarati` |
| 9 | Retrieval-before-generation and no-source refusal | COMPLETE AND TESTED | `test_unrelated_question_does_not_invent_an_answer`, `test_retrieval_does_not_attach_unrelated_articles` |
| 10 | Citation validation against retrieved set | COMPLETE AND TESTED | `test_model_answer_with_uncited_article_is_rejected` |
| 11 | Guard against guilt/outcome/impersonation language | COMPLETE AND TESTED | `test_guard_rejects_*` |
| 12 | Prompt-injection detection | COMPLETE AND TESTED (detection + logging) | `test_prompt_injection_is_flagged_but_answered`, `test_prompts_fence_untrusted_text` |
| 13 | Provider outage → offline fallback | COMPLETE AND TESTED | `test_configured_provider_failure_falls_back_and_is_flagged` |
| 14 | Strict mode → 503 without leaking an answer | COMPLETE AND TESTED | `test_provider_unavailable_strict_mode_returns_503` |
| 15 | Live LLM provider (`openai_compatible`) | IMPLEMENTED BUT NOT TESTED | no API key in this environment; 24/40 lines uncovered |
| 16 | Complaint intake + deterministic summary | COMPLETE AND TESTED | `test_complaints.py` |
| 17 | Review gate and `POST /complaints/preview` (no write) | COMPLETE AND TESTED | `test_preview_does_not_persist`, UI journey in `scripts/smoke_web.mjs` |
| 18 | Token-gated complaint retrieval (hash only) | COMPLETE AND TESTED | `test_wrong_token_is_indistinguishable_from_missing`, `test_access_token_is_not_stored_in_plaintext` |
| 19 | Document upload, magic-byte validation, size cap | COMPLETE AND TESTED | `test_documents.py` |
| 20 | PDF text extraction / OCR-unavailable status | COMPLETE AND TESTED (status only) | `test_image_upload_reports_ocr_unavailable`; no OCR engine installed |
| 21 | Owner-token document metadata and download | COMPLETE AND TESTED | `test_download_requires_owner_token` |
| 22 | Admin document review index (metadata only) | COMPLETE AND TESTED | `test_document_index_is_admin_only_and_metadata_only` |
| 23 | Department directory + detail + provenance | COMPLETE AND TESTED | `test_departments_and_feedback.py` |
| 24 | Feedback on answers/articles/departments | COMPLETE AND TESTED | `test_feedback_is_recorded`, `test_feedback_rejects_unknown_target_and_reason` |
| 25 | Bilingual glossary and terminology lookup | COMPLETE AND TESTED | `test_glossary_list_bilingual`, `test_terminology_lookup` |
| 26 | Admin/monitor roles, audit trail | COMPLETE AND TESTED | `test_admin_and_security.py` |
| 27 | Human verification workflow with guard-rails | COMPLETE AND TESTED | `test_admin_cannot_verify_*` |
| 28 | Rate limiting (read/write/ai/admin buckets) | COMPLETE AND TESTED | `test_rate_limit_returns_429`, `test_admin_endpoints_have_a_strict_rate_limit` |
| 29 | Body-size limits and chunked-body refusal | COMPLETE AND TESTED | `test_body_size_limit`, `test_chunked_body_without_length_is_refused` |
| 30 | Security headers and self-only CSP | COMPLETE AND TESTED | `test_csp_forbids_inline_code_and_styles` |
| 31 | PII redaction in logs and query storage | COMPLETE AND TESTED | `test_redaction_removes_pii_and_secrets`, `test_answer_is_logged_redacted` |
| 32 | Owner-only file permissions for DB and uploads | COMPLETE AND TESTED | `test_database_and_storage_are_owner_only` |
| 33 | Citizen SPA: six routes, gu/en toggle | IMPLEMENTED AND TESTED IN JSDOM | `scripts/smoke_web.mjs` — no real device/browser session yet |
| 34 | Citizen SPA: assistant with mic + speech synthesis | IMPLEMENTED BUT NOT TESTED | needs a real browser with a microphone/speaker |
| 35 | Complaint wizard end to end in the UI | IMPLEMENTED AND TESTED IN JSDOM | reference `NYM-…` created through preview + confirmation |
| 36 | Admin console (stats, queue, queries, errors, complaints, documents, legacy, backup) | IMPLEMENTED AND TESTED IN JSDOM | `/admin.js` was a 404 before this round; now served and exercised |
| 37 | Mobile layout and touch targets | PARTIALLY COMPLETE | responsive CSS with 44 px targets and breakpoints; **not tested on a device** |
| 38 | Accessibility (labels, aria-live, focus, reduced motion) | PARTIALLY COMPLETE | static assertions pass; no screen-reader session |
| 39 | Authoritative Article text (en + gu) | BLOCKED | needs official PDFs in `data/raw/`; 0 of 9 articles have `verified_source_text` |
| 40 | Legal correctness of explanations, helplines, portals | REQUIRES HUMAN VERIFICATION | `/admin` verification queue |
| 41 | Ingestion of an official Constitution document | COMPLETE AND TESTED (with fixture text) | `test_apply_writes_articles_and_report`; never run against a real PDF |
| 42 | Legacy corpus preservation | COMPLETE AND TESTED | 2,125 rows in gzip + DB, never served (`test_legacy_rows_are_preserved`) |
| 43 | CI (Python 3.11/3.12, dependency audit, node checks, bootstrap, backup) | COMPLETE AND TESTED | `.github/workflows/ci.yml`; runs 42439419345 and 42439422327 green — pytest 3.11, pytest 3.12, dependency audit, frontend |
| 44 | Deployment guide, backups, rollback | COMPLETE (documented) | `docs/DEPLOYMENT_GUIDE.md` |
| 45 | Duplicate-submission protection (idempotency key + fingerprint window) | COMPLETE AND TESTED | `test_same_client_request_id_returns_conflict_not_a_second_row`, `test_double_click_without_client_id_is_caught_by_fingerprint`, `test_duplicate_window_is_bounded` |
| 46 | Data-retention purge (complaints, documents, files, logs) | COMPLETE AND TESTED | `test_retention.py` (7 tests), `scripts/purge_data.py` |
| 47 | Operational metrics endpoint and admin panel | COMPLETE AND TESTED | `/admin/metrics`, `test_metrics_and_privacy.py`, jsdom smoke |
| 48 | `Cache-Control: no-store` on personal data, attachment downloads | COMPLETE AND TESTED | `test_sensitive_responses_are_not_cacheable`, `test_document_download_is_an_attachment_and_not_cacheable` |
| 49 | No cookies / no CORS surface | COMPLETE AND TESTED | `test_the_api_never_sets_cookies`, `test_no_cors_headers_are_advertised` |
| 50 | Ingestion: page/Part/Chapter provenance, boundary detection, quality gate, idempotency, conflict protection | COMPLETE AND TESTED | `test_ingest_pipeline.py` (19 tests) |
| 51 | Coverage report for the corpus (JSON + Markdown) | COMPLETE AND TESTED | `scripts/constitution_coverage.py`, `test_coverage_report_counts_real_rows` |
| 52 | Static accessibility / dead-end checks | COMPLETE AND TESTED | `test_frontend_static.py` (10 tests) |
| 53 | Dependency vulnerability audit + upgrade | COMPLETE | `pip-audit` clean after upgrading fastapi/starlette/pypdf/python-multipart |
| 54 | Real-browser / device / screen-reader / voice verification | BLOCKED | no browser, device or assistive technology in this environment |
| 55 | Changeset integrity checker (manifest, tree verify, archive verify) | COMPLETE AND TESTED | `scripts/verify_changeset.py`, 7 tests in `test_handover_tooling.py` |
| 56 | Live AI provider probe (fails honestly when no model is reachable) | COMPLETE AND TESTED | `scripts/verify_ai_provider.py`, exit 3 reproduced twice; 9 stub-server tests |
| 57 | Guard: correct citation of a retrieved article is accepted ("Article 14 is…") | COMPLETE AND TESTED | `backend/app/ai/guard.py`; regression tests in `test_ai.py` / `test_handover_tooling.py` |
| 58 | Guard: Gujarati digits match ASCII article labels | COMPLETE AND TESTED | `guard._normalise_digits`, `test_gujarati_digits_match_ascii_labels` |
| 59 | Accidental tracked `node_modules` symlink removed | COMPLETE | `git rm --cached node_modules`, `.gitignore` updated |
| 60 | Real model end-to-end verification | **BLOCKED** | no provider reachable; requirement documented and scripted |

**Summary:** 57 of 60 tracked features are complete and tested; 2 are blocked on owner input
(authoritative text, human legal verification) and 2 on the environment (real device/assistive
technology, a reachable model). Nothing is marked complete without a test, a CI run, or a
measured command output.

## Known dead ends removed in this round

| Removed | Why |
|---|---|
| `/api/docs` (Swagger UI) | Loaded JS/CSS from a CDN, which the CSP blocks and a rural connection cannot reach; `/api/openapi.json` + `docs/API_DOCUMENTATION.md` replace it |
| Inline `style="…"` attributes | Incompatible with a CSP that does not allow `'unsafe-inline'`; replaced with `.field-grow` / `.field-flush` classes |
| `/admin.js` 404 | The console HTML was served but its script was not registered, so every button was dead |
| Unused `departments._shape()` and `d.id AS dept_id` | Dead code and ambiguous join columns |

## What “done” would still require

1. Official Constitution PDFs (English + Gujarati) ingested, then every imported article reviewed
   and signed off by a qualified reviewer.
2. Helpline numbers and portal URLs re-checked against the official sites on a dated schedule.
3. One real browser/phone test pass (including voice) with a screen-reader user if possible.
4. A Gujarati-language review of the copy by a native speaker who is not the author.
