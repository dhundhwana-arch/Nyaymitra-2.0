# LEGAL_COMPLIANCE_MATRIX.md

NYAYMITRA 2.0 — Applicable-law review (India / Gujarat)
========================================================

## Status

**Self-assessed legal-readiness review.** Not a legal opinion, not a compliance
certification, not government approval. Every row below is marked with its confidence
and whether a qualified human legal reviewer must confirm it.

Review date: 2026-11-07 (local date in this environment).
Applicability assessed for the product as implemented (complaint drafting, document
upload, AI-assisted legal information, department navigation, no public deployment).

## How to read "Applicability"

* **Applies now** — the instrument is in force and arguably covers the product.
* **Commences <date>** — the instrument exists but the relevant provisions are not yet
  in force; planning should begin now.
* **Possibly applies** — uncertain; requires human legal review.

## Matrix

| # | Legal instrument | Provision | Applies to product? | Why / why not | Existing implementation | Missing / remediation | Human review required? |
|---|------------------|-----------|---------------------|---------------|-------------------------|----------------------|------------------------|
| 1 | Digital Personal Data Protection Act, 2023 (Act 22 of 2023) | Section 1(2), Section 2, Sections 18–26, 35, 38–43, 44(1),(3) — commenced 13 Nov 2025 | Applies now (framework) | Definitions, Data Protection Board of India, rule-making powers are in force; these establish the regime under which the product processes digital personal data. | None specific (framework sections create obligations indirectly). | Monitor further commencement notifications. | Yes — confirm which framework obligations bind the operator now. |
| 2 | DPDP Act, 2023 | Sections 3–17 (notice, consent, security, children, rights) — commence 13 May 2027 | Commences 13 May 2027 | Main data-fiduciary obligations not yet in force as of 2026-11-07. Product collects digital personal data (complaints, contact details, documents), so these will apply once commenced. | Consent checkbox, privacy notice (PRIVACY.md), minimal data collection, redaction in logs, retention policy (planned). | Implement formal notice (Section 5), consent record (Section 6), security safeguards (Section 8), Data Principal rights handling (Sections 11–15), breach response (Section 8 / Rules). | **Yes** — before 13 May 2027. |
| 3 | DPDP Act, 2023 | Section 6(9) — commences 13 Nov 2026 | Commences 13 Nov 2026 | Consent-manager provisions (not relevant unless the product becomes a consent manager). | None. | None unless role changes. | Yes — confirm non-applicability. |
| 4 | DPDP Rules, 2025 (G.S.R. 846(E), notified 13 Nov 2025) | Rules 1, 2, 17–21 — in force 13 Nov 2025 | Applies now (Board setup) | Definitions and Data Protection Board constitution; no direct fiduciary burden yet. | None. | Monitor. | Yes. |
| 5 | DPDP Rules, 2025 | Rules 3, 5–16, 22, 23 — commence 13 May 2027 | Commences 13 May 2027 | Consent notice form, security safeguards (Rule 6), 72-hour breach notification (Rule 7), retention/erasure (Rule 8), grievance officer (Rule 9), children's data (Rule 10), Data Principal rights (Rule 14). | Grievance channel not formally designated; breach response planned only (docs/security/INCIDENT_RESPONSE.md). | Appoint grievance officer; implement breach notice; document retention/erasure. | **Yes** — before 13 May 2027. |
| 6 | Information Technology Act, 2000 | Section 43A | Applies now | Body corporate handling sensitive personal data must maintain reasonable security practices; liable for compensation on negligence causing wrongful gain/loss. Product handles complaint descriptions that may include health/financial details. | Role-based access, parameterized queries, encrypted-in-transit not implemented (TLS at platform layer), no annual security audit. | Document reasonable security practices; consider ISO 27001-equivalent; annual audit. | **Yes**. |
| 7 | Information Technology Act, 2000 | Section 72A | Applies now | Criminal penalty for disclosing personal information obtained under a lawful contract without consent / in breach of contract. Admin UI is designed not to expose complaint text to admins. | Access control (tokens), redaction, admin cannot read complaint text. | Formalize no-disclosure policy; staff/contractor confidentiality. | **Yes**. |
| 8 | IT (Reasonable Security Practices and Procedures and SPDI) Rules, 2011 | Rules under Section 43A | Applies now (if SPDI handled) | Defines SPDI (passwords, financial, health, biometric, sexual orientation) and reasonable security practices (ISO 27001 or equivalent, annual audit). Product does not request SPDI but may receive it in free-text descriptions. | No SPDI fields; data minimization; redaction in logs. | Explicitly tell users not to submit SPDI; consider field-level redaction. | **Yes**. |
| 9 | Legal Services Authorities Act, 1987 | Sections 12, 13 | Applies now (referral context) | Establishes NALSA/SLSA/DLSA and free legal aid; Section 12 lists eligible categories. Product refers citizens to 15100 / DLSA but is not itself a Legal Services Authority. | UI references free legal aid (15100), DLSA, NALSA in disclaimers and assistant answers. | Never claim the product provides legal aid or is empanelled with NALSA. | **Yes** — confirm referral wording. |
| 10 | Bharatiya Sakshya Adhiniyam, 2023 | Relevant sections on electronic records | Possibly applies | If complaint documents or AI answers are ever tendered as evidence, admissibility of electronic records applies. Product makes no evidentiary claims. | Complaint drafts marked "information only"; downloadable .txt. | None in product; document limitation. | **Yes**. |
| 11 | Advocates Act, 1961 | — | Applies now (boundary) | Product must not practise law or hold itself out as a lawyer. | Disclaimers on every page and answer: "not legal advice", "not a lawyer/court/judge". | Keep disclaimers prominent; review wording periodically. | **Yes**. |
| 12 | Rights of Persons with Disabilities Act, 2016 | Accessibility provisions | Possibly applies | Government-facing digital services should be accessible. Product has keyboard navigation, focus rings, language toggle, screen-reader labels. | Partial implementation (no formal audit). | Accessibility audit by qualified reviewer (blocker B-3). | **Yes**. |
| 13 | Guidelines for Indian Government Websites (GIGW) | — | Possibly applies | If hosted on a government domain, GIGW would apply. Not currently government-hosted. | None. | None unless adopted by government. | Yes — if licensed to government. |

## Overall assessment

As of 2026-11-07:

* The DPDP Act's **main obligations commence 13 May 2027** — the product has time to
  prepare but must not claim DPDP compliance now.
* The IT Act 2000 (Sections 43A, 72A) and SPDI Rules 2011 **apply now** to any body
  corporate handling personal/sensitive data — security practices and no-unauthorized-
  disclosure are the relevant obligations.
* The Legal Services Authorities Act 1987 governs the referral target (NALSA/DLSA,
  helpline 15100); the product refers to it but is not part of it.

## Not a legal opinion

This matrix was produced by an automated review of public sources and the product's
implemented behaviour. A qualified Indian legal practitioner must confirm each row
before the product is relied on in any deployment.
