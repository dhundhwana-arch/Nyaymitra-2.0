# Remaining blockers

Three blockers remain. None of them is an engineering task, and none can be closed honestly from
a development sandbox. Everything else that could be implemented has been.

---

## B-1 — No authoritative Constitution text (owner)

**Status:** BLOCKED. **Owner:** Divyesh Bambhaniya.

The repository contains **no** official Constitution document. `data/raw/` holds only a README.
Consequently 0 of the 9 loaded articles have `text_status = verified_source_text`; the other 9
are owner-written explanations.

The pipeline is ready and safe to use (`scripts/ingest_constitution.py`, dry-run by default,
quality-gated; `scripts/constitution_coverage.py` for reporting). It was tested against fixture
text, not against a real PDF.

**Required evidence to close:**
1. `data/raw/constitution-of-india-en.pdf` (or `.txt`) from India Code / Legislative Department.
2. `data/raw/samvidhan-gu.pdf` for the official Gujarati text, if Gujarati article text is wanted.
3. Output of the dry run committed to the PR (or pasted in the PR discussion):
   `python scripts/ingest_constitution.py --file … --source-key india-code-constitution --language en`
4. Then `--apply --backup`, and `python scripts/constitution_coverage.py` showing a non-zero
   "articles with authoritative source text".

**Safest next step:** run the dry run first and read `blocking_reasons`. If the gate fails
(`low_text_quality`, `duplicate_article_numbers`, `suspicious_article_boundaries`), fix the source
PDF or re-export its text layer — do **not** use `--force`.

---

## B-2 — No human legal verification (owner + qualified reviewer)

**Status:** BLOCKED. **Owner:** Divyesh to appoint; **reviewer:** an advocate, law academic, or
legal-aid officer who is willing to be named in `checked_by`.

Nothing is verified: 9 article explanations, 11 department/helpline entries, 5 triage guides and
18 glossary terms all carry `requires_human_verification` (the glossary explicitly says its
definitions are not statutory definitions). The admin console enforces the guard-rails: an article
cannot be marked verified without a named reviewer, a date, and authoritative text.

**Required evidence to close:** a completed sign-off table in
`docs/LEGAL_VERIFICATION_CHECKLIST.md` (§5) **and** the corresponding rows in the admin verification
queue showing `verified` with `checked_by` and `last_checked_at`.

**Safest next step:** start with the five triage guides and the eleven department contacts, because
those are what a citizen acts on. Article explanations come after the official text is loaded.

---

## B-3 — No real-browser / device / assistive-technology testing (needs hardware)

**Status:** BLOCKED. **Owner:** Divyesh (or anyone with a phone).

The frontend is covered by jsdom journeys (`scripts/smoke_web.mjs`: six routes, language toggle,
assistant, library, glossary, complaint wizard, admin console, focus management) and by static
accessibility assertions. jsdom has no layout engine, no media queries, no speech APIs and no
accessibility tree. So the following are **unverified**:

* responsive layout at 360 px / 414 px / tablet widths,
* Gujarati font shaping and line breaking on Android/iOS,
* microphone input (Web Speech) and speech synthesis,
* screen-reader navigation (TalkBack / NVDA),
* real rendering of the CSP-restricted pages (no inline styles/scripts),
* the admin console on a small screen.

**Required evidence to close:** screenshots (or a short screen recording) at 360 px, 414 px and
desktop for home / assistant / complaint / library / admin; one voice attempt on a real phone; one
screen-reader pass over the complaint form; and the manual test list in `docs/TESTING_REPORT.md` §5
executed and ticked.

**Safest next step:** install the app locally, open it on the phone over the LAN, and record the
result — even a "passes/fails" note per screen closes one blocker item.

---

## Not blockers, but decisions the owner must make

| Decision | Why it matters | Default today |
|---|---|---|
| Retention period for complaints + documents | Legal/ethical duty; the purge job exists but is not scheduled | `NYAYMITRA_PII_RETENTION_DAYS=180`, not scheduled |
| Whether to enable a live LLM provider | Sends question text to a third party | offline only |
| Public hosting vs supervised kiosk | Public release needs the legal content verified first | local evaluation |
| Who holds the admin vs monitor token | Shared tokens, no per-user accounts | operator sets both |
