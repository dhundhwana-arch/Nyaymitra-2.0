# THREAT_MODEL.md

NYAYMITRA 2.0 — Threat model
============================

## Status

**Self-assessed threat model.** Not produced by a qualified security reviewer. Treat it
as a working document for discussion, not as a security assessment.

## Assets

1. Citizen complaint text and contact details (personal data).
2. Complaint reference numbers and access tokens (capability to re-open a draft).
3. Uploaded documents (evidence, identity papers, legal notices).
4. Constitution articles and legal-navigation data (must remain accurate and traceable).
5. Admin/monitor tokens (capability to mutate verification state and take backups).
6. Service availability (citizens rely on it for legal-aid navigation).

## Threats and mitigations

| Threat | Target | Likelihood | Impact | Mitigation |
|--------|--------|------------|--------|------------|
| Complaint enumeration via guessed references | complaint data | Low | High | Reference + token both required; wrong token returns "not found" (no oracle) |
| Token leakage in logs or browser history | admin/complaint access | Medium | High | Tokens never logged; complaint tokens shown once, transmitted over HTTPS only |
| Prompt injection causing invented law | AI answers | Medium | High | Input scan, fenced source blocks, answer validation, offline fallback |
| Model hallucination of article numbers | AI answers | Medium | High | `validate_answer` rejects uncited references; falls back to offline grounded |
| SQL injection via API parameters | database | Low | High | Parameterized queries only; no string interpolation |
| File upload path traversal | filesystem | Low | High | Random stored names; `stored_name` resolved under `storage_dir` only |
| Large file denial of service | service | Medium | Medium | 10 MB upload cap; body size limit 512 KB |
| Rate-limiting bypass (shared IP) | service | Medium | Medium | Per-IP fixed window; note the per-process limitation |
| Admin token guessing | admin API | Low | High | Constant-time comparison; 24-char minimum; preflight rejects weak tokens |
| Backup exposure | complaint data | Medium | High | Backups outside checkout; integrity-checked; operator must protect at rest |
| XSS via rendered complaint text | citizen browser | Low | Medium | All output escaped; no `innerHTML` of user data |
| CSRF on state-changing endpoints | complaint submission | Low | Medium | No cookies/sessions; token-based auth; same-origin by default |
| Supply-chain dependency vulnerability | service | Medium | Medium | `pip-audit` in CI; pinned versions in `requirements.txt` |

## Out of scope (not mitigated here)

* Network-layer DDoS (no WAF).
* Physical access to the server.
* Compromise of the operator's environment variables.
* Real-device and browser compromise (blocker B-3).

## Assumptions

* Deployment is single-process on a host the operator controls.
* TLS is terminated at the reverse proxy or platform layer (not implemented in-app).
* The AI provider, when configured, is trusted to handle the question+sources it
  receives (it never receives personal data).

## Review required

A qualified security reviewer should validate this threat model before any public
deployment.
