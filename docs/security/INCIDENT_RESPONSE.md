# INCIDENT_RESPONSE.md

NYAYMITRA 2.0 — Incident response plan (planned, not exercised)
===============================================================

## Status

**Planned, not exercised.** This document describes the intended response process. It
has not been tested in an actual incident and is not a substitute for a qualified
incident-response retainer.

## Severity levels

| Severity | Example | Response time | Who |
|----------|---------|---------------|-----|
| Critical | Confirmed exfiltration of complaint text or tokens | Immediate (24 h) | Operator + security reviewer |
| High | Admin token compromise; SQL injection exploited | 1 business day | Operator |
| Medium | Dependency vulnerability with known exploit | 5 business days | Operator |
| Low | Missing security header on one endpoint | Next release | Maintainer |

## Response process

1. **Contain.** Take the service offline or rotate credentials if credentials are
   suspected compromised. Preserve logs and backups for forensics.
2. **Assess.** Determine what personal data was accessed, by whom, and for how long.
   Do not delete logs or backups before assessment.
3. **Notify.** If personal data of Indian data principals is affected, assess
   notification obligations under the Digital Personal Data Protection Act, 2023 and
   notify the Data Protection Board as required by law. Legal review required before
   any notification.
4. **Remediate.** Patch the vulnerability, rotate all tokens, redeploy from a clean
   build.
5. **Review.** Post-incident review within 2 weeks; update this document and the threat
   model.

## Evidence to preserve

* Application logs (redacted — no question text or contact details).
* Database file and backups (before any purge or migration).
* Web server / proxy access logs.
* The exact environment-variable values in use (tokens rotated after the incident).

## What this document is NOT

* A legal opinion on breach-notification obligations.
* A certified incident-response plan.
* Tested in a real incident.
