# Known limitations

Honest list, in the order it is likely to bite.

## Legal content

1. **No authoritative Constitution text is loaded.** 9 articles exist as owner-written
   explanations only (`text_status = owner_authored_summary`). The API returns `text_en: null` and
   says the official text is missing. Fixing this needs the official PDFs (`data/raw/README.md`)
   and `scripts/ingest_constitution.py`.
2. **Corpus breadth is tiny.** 9 of ~395 articles, 5 triage categories, 11 departments. Questions
   outside those return “no related article found” — correctly, but unhelpfully.
3. **Nothing is human-verified.** Every row is `requires_human_verification`; helplines and portal
   URLs are unconfirmed (`docs/LEGAL_VERIFICATION_CHECKLIST.md`).
4. **Legacy content is not usable.** All 2,125 old rows are Santhali/unlabelled PDF fragments with
   a fabricated “remedy” field. They are preserved for audit and never served.
5. **Gujarati is not tokenised properly.** SQLite FTS5 `unicode61` splits on whitespace; the
   stopword list and overlap threshold compensate, but Gujarati search relevance is weaker than a
   language-aware analyser would give.
6. **Statute and case law are absent.** Only constitutional articles; no Acts, rules, notifications
   or judgments.

## AI

7. **No live model has been exercised.** There is no API key here and no local model server, and
   this sandbox cannot download weights. `scripts/verify_ai_provider.py` reproduces the gap
   (exit 3) and prints the exact requirement — Ollama, a pulled model, four environment
   variables — so the same command is the acceptance test once a model exists. The provider
   *wiring* is tested against a stub HTTP server, which is not the same thing. The offline
   grounded composer remains the tested path and the default.
8. **Answers are shallow by design.** The offline composer assembles retrieved explanations plus
   triage steps; it does not reason, summarise long documents or answer follow-ups.
9. **No conversation memory.** Each question is independent.
10. **Injection detection is pattern-based**, so it catches known phrasings, not novel attacks. The
    structural defence (retrieval-only grounding + citation validation) is the real control.
11. **No evaluation set.** Retrieval quality is covered by a handful of targeted tests, not by a
    labelled benchmark of real citizen questions.
12. **No multilingual input beyond Gujarati/English**, and no transliteration (“kayada samaksh
    samanta” in Latin script will not retrieve well).

## Documents

13. **No OCR.** Images and scanned PDFs are stored and returned by their owner, with
    `extraction_status = ocr_unavailable`; their text is never guessed.
14. **No document verification against an issuing authority.** The admin index shows metadata,
    SHA-256 and extraction status only; it cannot prove a PDF is genuine.
15. **No malware scanning** and no PDF sandboxing (extraction is bounded to 5 pages / 20 k chars /
    8 MB).
16. **Uploads are not shared with anyone.** There is no case file, no hand-off to a lawyer, no
    e-mail delivery of the complaint.

## Application

17. **No accounts, no login, no case tracking.** A complaint is retrieved with the reference +
    token; losing the token loses the complaint. There is no “forgot token” recovery by design.
18. **The summary is extractive**, not a legal analysis: it restates the citizen's words plus
    category and next steps.
19. **Single process.** SQLite + in-memory rate limiting assume one worker; multiple workers break
    the rate limits and can lock the database.
20. **Retention is implementable but not scheduled.** `scripts/purge_data.py` deletes old
    complaints, documents and query logs (dry-run by default, audited, 7 tests), but the retention
    period is an owner decision and no cron entry is installed. Until then, data is kept
    indefinitely.
21. **No e-mail/SMS notification**, so a citizen must keep the reference themselves.
22. **No admin UI for editing seed content** — articles/departments are changed through the seed
    files or SQL; only verification state is editable in the console.
23. **English copy is the developer's English.** The Gujarati UI strings have not been reviewed by
    a native speaker, and `docs/` is English-only.

## Testing and operations

24. **No real-browser or device test.** The jsdom smoke test needs jsdom installed
    (`npm install --no-save jsdom`); it is not vendored, and a tracked symlink to it was removed. jsdom journeys pass; layout, CSS breakpoints, font shaping,
    voice and screen readers are unverified (`docs/TESTING_REPORT.md` §4).
25. **No load test.** Throughput and latency under concurrent users are unmeasured.
26. **CI covers Linux only.** Runs 42404987197 / 42404988506 are green on Python 3.11 and 3.12
    plus the Node checks, and run 42439419345 includes a `pip-audit` job, but there is no
    Windows/macOS job, so `run.bat` and the `chmod` calls are untested on those platforms.
27. **Metrics exist, alerting does not.** `GET /api/v1/admin/metrics` exposes request, rate-limit
    and AI-fallback counters in-process, and the admin console shows them; there is no scraper,
    time series, or alert rule, and no external uptime check.
28. **No i18n framework** — translations are a dictionary in `web/app.js`; adding a language means
    editing code.

## Security

29. **Shared operator token**, no individual accounts or MFA; see `SECURITY_AUDIT.md` R-7.
30. **No encryption at rest**; rely on host/volume encryption.
31. **Rate limits are per-process** and reset on restart.

## What would change the headline

Loading the official texts and completing human verification (items 1–3) moves the project from
“legal-information prototype with honest gaps” to “usable legal information”. Nothing else on this
list is a release blocker for a supervised pilot; items 1–3 are.
