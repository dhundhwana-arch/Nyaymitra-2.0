# CONSENT_AND_NOTICE_REVIEW.md

NYAYMITRA 2.0 — Consent and notice review
==========================================

## Status

**Partially implemented; human legal review required.** Not a legal opinion.

Date: 2026-11-07.
DPDP Act Sections 5 (notice) and 6 (consent) commence 13 May 2027 — not yet in force.
This review prepares the product for those requirements.

## Consent

### Complaint intake
* A checkbox is required before a complaint can be saved: "I agree that this information
  may be stored on this server."
* Consent is stored as `consent_given = 1` in the `complaints` table.
* Consent is specific to storing the complaint on this server; it is not consent to AI
  training, third-party sharing, or marketing.
* Complaint text is never used to train any AI model.

### AI assistant
* No personal data is required to ask a question. No consent is needed for the assistant
  because no personal data is collected (the question itself may contain personal data if
  the citizen volunteers it — the disclaimer warns against this).
* No consent banner for cookies/tracking — none are used.

### Withdrawal
* No automated withdrawal mechanism exists yet. Manual deletion on request (operator).

## Notice

### What is disclosed to citizens (current)
* Hero and card copy state: "We do not decide cases", "information, not legal advice".
* Every AI answer ends with disclaimers:
  1. NYAYMITRA is not a lawyer, a court or a judge, and does not decide cases.
  2. Answers are information built from the sources listed; they are not legal advice.
  3. Verify anything important against the official source or with free legal aid (15100).
* Article and department views show `verification_status` badges (verified /
  requires_human_verification / unverified / outdated).
* The library shows a corpus warning when authoritative text is not loaded (0 of 9
  articles have source text).
* The offline banner states when no AI provider is configured.

### What should be added before public deployment (DPDP Section 5 / Rule 3 readiness)
* A standalone privacy notice linked from every page, covering:
  * what personal data is collected and why;
  * the purpose of collection;
  * how long it is retained;
  * who to contact (grievance officer — to be appointed);
  * Data Principal rights (access, correction, erasure, grievance redressal) once the
    DPDP Act commences.
* A statement that submission is voluntary and that contact fields are optional.
* A warning not to submit sensitive personal data (Aadhaar, PAN, bank details, health
  details) in free-text fields.

## Consent record quality

* Consent is captured as a boolean with a timestamp (`created_at`).
* No versioning of consent terms — if the notice changes, existing consent is not
  re-obtained. Re-obtain consent after any material notice change.

## Notices to avoid

* Do NOT state that the product is "DPDP compliant" — the Act's main obligations
  commence 13 May 2027 and the product has not been independently assessed.
* Do NOT state that legal content is "verified" unless a human reviewer has signed off
  (see `docs/legal/HUMAN_LEGAL_REVIEW_CHECKLIST.md`).
* Do NOT state that the product provides "free legal aid" — it refers to NALSA/DLSA and
  helpline 15100 but is not a Legal Services Authority.

## Human legal review required

* Confirm consent wording satisfies DPDP Section 6 (when in force).
* Confirm notice covers all DPDP Section 5 / Rule 3 elements.
* Appoint and publish a grievance officer (DPDP Rule 9).
