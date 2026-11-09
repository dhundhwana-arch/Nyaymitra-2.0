# NYAYMITRA 2.0 — Risk Register

| ID | Category | Risk | Likelihood | Impact | Mitigation | Status |
|----|----------|------|------------|--------|------------|--------|
| R-1 | Legal | Unverified legal content presented as if authoritative | Medium | High | Every answer labelled verification status + disclaimers; human review required before public use; 0 of 9 articles verified | BLOCKED (B-2) |
| R-2 | Legal | DPDP Act obligations not yet assessed as in force | Low | Medium | Main obligations commence 13 May 2027; product preparing (consent, retention, redaction) | Monitor |
| R-3 | Legal | IT Act §43A / §72A + SPDI Rules apply now to body corporates | Low | Medium | PII redaction, rate limiting, retention 180 days, purge tooling, secure defaults | Implemented |
| R-4 | Privacy | Citizen question transmitted to external AI provider unredacted (if configured) | Medium | Medium | Default offline (no data leaves); disclosure in package; consider redaction before provider send | Disclosed |
| R-5 | Privacy | Raw complaint PII (phone, email, contact) stored locally | Medium | Medium | Token-hashed access, redaction before logs, 180-day retention, purge tooling, no cookies | Implemented |
| R-6 | Security | No penetration test or certification | Medium | Medium | Self-assessed controls only; pip-audit clean; not certified | Disclosed |
| R-7 | Security | Dependencies could accumulate new advisories | Low | Low | Pinned versions; periodic pip-audit; production preflight | Implemented |
| R-8 | Operational | Single-process SQLite not for concurrent production load | Medium | Medium | Documented limit; scale only after re-architecture | Documented |
| R-9 | Operational | No real browser/device/screen-reader testing | Medium | Medium | jsdom only; B-3 requires devices and assistive technology | BLOCKED (B-3) |
| R-10 | Adoption | Citizens may mistake information for legal advice | Medium | High | Prominent disclaimers on every answer; "not a lawyer" framing; offline-first | Implemented |
| R-11 | AI | Model could hallucinate citations if live provider used | Medium | High | Answer guard rejects uncited articles; offline fallback preferred; real inference unverified | BLOCKED (B-4) |
| R-12 | Project | No owner approval to merge/deploy | Low | High | PR #1 kept draft; no merge or push beyond branch without owner | OWNER APPROVAL (B-5) |

## Overall

The highest-severity risks (R-1 unverified legal content, R-10 mistaken for advice, R-11 AI hallucination) are mitigated by disclaimers, the safety guard, offline-first default, and the requirement for human legal review before public use. None are retired until blockers B-1 through B-5 are resolved.

## Repository

https://github.com/dhundhwana-arch/Nyaymitra-2.0 | audited source snapshot `cc56d0e`
