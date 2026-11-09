# LEGAL_RISK_REGISTER.md

NYAYMITRA 2.0 — Legal risk register
====================================

## Status

**Self-assessed risk register.** Not a legal opinion. Risks are listed with severity and
the owner action required. All risks marked "human legal review" require confirmation by
a qualified Indian legal practitioner before any public deployment.

Date: 2026-11-07.

## Register

| # | Risk | Legal basis | Severity | Likelihood | Current control | Residual risk | Owner action |
|---|------|-------------|----------|------------|-----------------|---------------|--------------|
| R-1 | AI answer misstates the law or cites a non-existent article | Advocates Act 1961 (unauthorised practice); consumer-protection / misrepresentation risk | High | Medium | Source-grounded RAG, answer validation, offline fallback, disclaimers on every answer | A wrong answer could still reach a citizen | Human legal review of guardrails; appendix disclaimer review |
| R-2 | Product perceived as providing legal aid / legal advice | Legal Services Authorities Act 1987; Advocates Act 1961 | High | Medium | Disclaimers: "not legal advice", "not a lawyer/court/judge"; referral to 15100/DLSA | Citizens may rely on the AI instead of a lawyer | Human legal review of all user-facing wording |
| R-3 | Personal data breach of complaint records | DPDP Act 2023 (commences 13 May 2027); IT Act 2000 §43A/72A | High | Low | Role-based access, tokens, redaction, encryption-at-rest is operator's responsibility | Complaint text/contact details exposed | docs/security/INCIDENT_RESPONSE.md; appoint grievance officer before 13 May 2027 |
| R-4 | Department contact details are wrong / outdated | Misrepresentation; misleading a citizen seeking help | Medium | High | Entries marked `verification_status != 'verified'`; badges shown in UI | Citizen calls a wrong number | Human legal reviewer verifies 11 departments (blocker B-2) |
| R-5 | Constitution article explanations treated as authoritative law | Misrepresentation; unauthorised practice of law | High | Medium | All 9 articles marked `owner_authored_summary` / `not_available`; badges; disclaimers | Citizen relies on summary instead of statute | Human legal review before any article marked `verified_source_text` (blocker B-1) |
| R-6 | No formal grievance officer / breach notification | DPDP Rules 2025 Rule 7 / 9 (commence 13 May 2027) | Medium | Low | Incident response planned (not exercised); no grievance officer designated | Regulatory non-compliance when rules commence | Appoint grievance officer; test breach response |
| R-7 | Accessibility barriers for persons with disabilities | RPwD Act 2016; GIGW if government-hosted | Medium | Medium | Keyboard nav, focus rings, language toggle, ARIA labels | Some users cannot use the service | Accessibility audit (blocker B-3) |
| R-8 | No self-service data deletion | DPDP Act rights (Sections 11–15, commence 13 May 2027) | Medium | Low | Retention purge script exists; deletion on request is manual | Data Principal cannot easily erase data | Implement deletion endpoint or documented manual process |
| R-9 | Third-party dependency vulnerability | Contractual / security | Medium | Low | pip-audit in CI, pinned versions | Vulnerable dependency reaches production | Keep dependencies updated; re-audit before release |
| R-10 | Public deployment without owner approval | — | High | Low | PR #1 remains draft and unmerged; no public deployment performed | Unauthorized public service | Owner must approve merge and deployment |

## Severity definitions

* High: could cause legal liability, regulatory action, or serious harm to a citizen.
* Medium: could cause confusion, inconvenience, or regulatory friction.
* Low: limited direct impact.

## Review cycle

Review this register before every release and whenever a new legal instrument
commences (next DPDP milestone: 13 May 2027).
