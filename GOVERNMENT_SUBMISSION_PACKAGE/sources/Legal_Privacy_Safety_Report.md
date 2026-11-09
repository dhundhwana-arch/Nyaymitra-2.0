# NYAYMITRA 2.0 — Legal, Privacy and Safety Readiness Report

## 1. Legal information vs legal advice

NYAYMITRA 2.0 provides **legal information only**, not legal advice. Every answer carries:

- A disclaimer: "NYAYMITRA is not a lawyer, a court or a judge, and does not decide cases."
- A disclaimer: "Answers are information built from the sources listed; they are not legal advice."
- A disclaimer: "Verify anything important against the official source or with free legal aid (15100)."
- Verification status (verified / requires human verification) and warnings when sources are insufficient.

The system never states guilt/innocence, never predicts outcomes, never claims the user will win, and never impersonates a lawyer (enforced by `guard.validate_answer`).

## 2. Human legal review requirements

Legal content awaiting qualified review:

| Content | Count | Verified |
|---------|-------|----------|
| Constitution articles | 9 | 0 |
| Departments | 11 | 0 (verification status tracked) |
| Triage guides | 5 | 0 |

A human legal reviewer must sign off using the review packet (`GET /api/v1/admin/review-packet`) and `docs/legal/HUMAN_LEGAL_REVIEW_CHECKLIST.md`. This is **BLOCKED** pending appointment of a named reviewer (blocker B-2).

## 3. Official source verification

- 9 constitution articles are owner-written explanations.
- **0 articles have authoritative source text loaded.**
- **0 articles are human-verified.**
- Official Constitution PDFs must be supplied by the repository owner and ingested via `scripts/ingest_constitution.py` (dry run, then `--apply --backup`), followed by `scripts/constitution_coverage.py`. (Blocker B-1)

## 4. Citizen data protection

| Practice | Implementation |
|----------|---------------|
| Data minimisation | Only fields needed for complaint routing are collected |
| PII redaction before logging/storage | `logging_utils.redact_and_truncate` applied to query text, answers, errors |
| Token-based access | Complaint access token stored as SHA-256 hash; never transmitted back |
| Constant-time comparison | Token lookup does not reveal whether a reference exists |
| Rate limiting | Per-end-class limits (read/write/AI/admin) |
| Retention | Default 180 days (`NYAYMITRA_PII_RETENTION_DAYS`) |
| Deletion | `scripts/purge_data.py` (dry-run default) removes old complaints/documents/query logs |
| No cookies | None set |
| Cache control | Personal-data responses carry `Cache-Control: no-store` |

## 5. External AI provider data flow

- **Default (offline):** No AI provider configured → `ai_configured` is False → deterministic offline composer → **no data leaves the application.**
- **If configured** (`NYAYMITRA_AI_PROVIDER=openai_compatible` + base URL + model + API key): the citizen question (up to 1,000 chars, fenced as data) and retrieved sources are sent to the external endpoint. **There is no PII redaction before transmission.** If a citizen includes phone/email in their question, it is transmitted. This is a disclosed limitation.
- API key is never hard-coded and never logged.
- Provider is optional; the system degrades safely to offline when unavailable.

## 6. Consent and transparency

- Complaint flow requires an explicit consent checkbox before submission (submit button disabled until ticked).
- Preview shown before any write; reference + token shown once after submission.
- Every answer lists its sources with verification status and carries disclaimers.
- Unverified content is labelled "requires human verification."

## 7. Data retention and deletion

- Default retention 180 days.
- `scripts/purge_data.py` (dry-run default) deletes old complaints, their documents/files, and old query logs; retains audit trail (counts only).
- Refuses any path outside the storage directory.
- No self-service deletion endpoint yet (planned).

## 8. DPDP-related obligations and commencement dates

| Provision | Status as of 2026-11-07 | Relevance |
|-----------|------------------------|-----------|
| DPDP Act 2023 framework sections | In force (13 Nov 2025) | Product is preparing |
| DPDP §6(9) / Consent Manager Rule 4 | Commences 13 Nov 2026 | Not yet applicable |
| DPDP main obligations (Sections 3–17, Rules 3, 5–16, 22, 23) | Commence 13 May 2027 | Not yet in force |
| IT Act 2000 §43A / §72A + SPDI Rules 2011 | Apply now to body corporates handling personal data | Security practices + no unauthorized disclosure |

The product prepares for DPDP (consent, minimal collection, redaction, retention, grievance-officer placeholder) but is **not yet subject to DPDP main obligations** (they commence 13 May 2027).

## 9. Risks and mitigation

See `Risk_Register.md` (technical, legal, privacy, security, operational, adoption). Key mitigations: offline-first default, PII redaction, safety guard, disclaimers, human legal review, no public deployment without owner approval.

## 10. Important disclaimer

This project is **not legally certified, not legally compliant, and not government-approved** without independent evidence. All legal assessments are self-assessed and require qualified legal review.

## 11. Repository

https://github.com/dhundhwana-arch/Nyaymitra-2.0 | commit `068cf9f`
