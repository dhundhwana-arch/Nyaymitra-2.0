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

> **WARNING:** External AI mode must NOT be used with real citizen data until appropriate privacy controls, disclosures, consent mechanisms, and qualified legal/privacy review are completed. In external mode, the citizen's question (which may contain phone, email, location, or other personal details) is transmitted unredacted to the configured provider. The provider's retention, processing, and data-handling practices are unknown and outside NYAYMITRA's control. Do not enable external AI mode with real citizen data in any pilot or deployment until these risks are addressed.

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

## 8. DPDP-related obligations and commencement dates (position as of 9 November 2026)

The Digital Personal Data Protection Act, 2023 (Act No. 22 of 2023) received Presidential assent on 11 August 2023. Its sections come into force on dates appointed under Section 1(2) by the commencement notification **G.S.R. 843(E)** (Gazette of India, 13 November 2025); the DPDP Rules, 2025 were notified as **G.S.R. 846(E)** on the same date. Dates computed from the Gazette notification are presented as interpretation until officially confirmed.

| Provision | Legal position as of 9 November 2026 | Source / notification |
|-----------|--------------------------------------|------------------------|
| DPDP Act 2023 framework sections (definitions §2; Data Protection Board §§18–26; rule-making powers) | **In force** since 13 November 2025 | G.S.R. 843(E), 13 Nov 2025; DPDP Rules 2025 Rules 1, 2, 17–21 |
| DPDP §6(9) / Consent Manager registration — Rule 4 | **Commences 13 November 2026** (future; not yet in force on 9 Nov 2026) | G.S.R. 843(E); DPDP Rules 2025 Rule 4 |
| DPDP main obligations — Data Fiduciary duties & Data Principal rights (§§3–5, 6(1)–(8) & (10), 7–17; Rules 3, 5–16, 22, 23; penalties §§28–34; §44(2)) | **Commence 13 May 2027** (future; approx. 6 months away; not yet in force) | G.S.R. 843(E); DPDP Rules 2025 Rules 3, 5–16, 22, 23 |
| IT Act 2000 §43A / §72A + SPDI Rules 2011 | **Apply now** to body corporates handling personal data; remain operative until DPDP §44(2) commences on 13 May 2027 | IT Act 2000; SPDI Rules 2011 |

Note on dating: the G.S.R. 843(E) notification bears 13 November 2025; a small number of secondary sources cite Gazette publication on 14 November 2025, which would shift the 18-month computed date by one day. NYAYMITRA 2.0 plans around the notified date of 13 May 2027 and treats all forward dates as interpretation until officially confirmed.

The product prepares for DPDP (consent checkbox, minimal collection, PII redaction before logging/storage, 180-day retention, purge tooling, grievance-officer placeholder) but is **not yet subject to DPDP main obligations**, which commence on 13 May 2027. No claim of DPDP compliance is made; all legal assessments are self-assessed and require qualified legal review.

## 9. Risks and mitigation

See `Risk_Register.md` (technical, legal, privacy, security, operational, adoption). Key mitigations: offline-first default, PII redaction, safety guard, disclaimers, human legal review, no public deployment without owner approval.

## 10. Important disclaimer

This project is **not legally certified, not legally compliant, and not government-approved** without independent evidence. All legal assessments are self-assessed and require qualified legal review.

## 11. Repository

https://github.com/dhundhwana-arch/Nyaymitra-2.0 | commit `792b529`
