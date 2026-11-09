# NYAYMITRA 2.0 — Executive Summary

**AI-Powered Inclusive Justice Access & Navigation System**
Government-facing overview | Functional software prototype / Proof of Concept

## 1. What NYAYMITRA 2.0 is

NYAYMITRA 2.0 ("Nyaymitra" = friend of justice) is an AI-enabled justice-navigation prototype with deterministic offline retrieval. It is an offline-first, multilingual (English and Gujarati) web application that helps ordinary citizens — especially in rural communities and among people with limited digital or legal literacy — understand legal information, locate relevant government departments, identify official sources, and find human legal assistance.

Live AI inference and legal-source accuracy validation remain pending.

It is a **functional software prototype / Proof of Concept**, subject to independent evaluation. It is not a substitute for courts, lawyers, police, government authorities, or qualified legal professionals.

## 2. Why it matters in India

- Legal information is hard to access and understand for citizens outside major cities.
- Free legal aid exists (NALSA / DLSA helpline 15100) but awareness and navigation are low.
- Citizens often do not know which constitutional provision, statute, or department applies to their problem.
- Existing portals are typically English-only, desktop-centric, and not built around guided complaint drafting.

## 3. What it does (prototype capabilities)

- Plain-language answers to legal questions in English and Gujarati, with citations to source articles.
- Retrieval-augmented generation (RAG) over a curated corpus: 9 constitution articles, 11 departments, 5 triage guides, 18 glossary terms.
- Deterministic offline fallback — works with no AI key, no internet, no external model.
- Complaint drafting with preview-before-submit, consent checkbox, idempotency, and access-token lookup.
- Admin console with statistics, verification queue, metrics, backup, and redaction.
- Data retention (180 days default), purge tooling, role-based tokens, rate limiting, CSP headers.
- A quarantined legacy corpus (2,125 chunks) is preserved but never served; its source provenance and copyright status are unresolved.

## 4. Verified status (commit `792b529`)

| Check | Result |
|-------|--------|
| Automated tests | 226 passed, 0 failed |
| Test coverage | 92% (2,545 statements, 202 missed) |
| Dependency vulnerabilities | None found (`pip-audit`) |
| Database integrity | OK (4 migrations, 0 missing indexes) |
| Application startup | `/api/v1/ready` returns 200 |
| Real AI model inference | Not available — blocked (no model runtime in sandbox) |
| Human legal review | 0 of 9 articles verified — blocked (reviewer not appointed) |

## 5. What is NOT claimed

- Not legally certified, government-approved, or legally compliant without independent review.
- Not a replacement for qualified legal professionals.
- AI inference is not verified with a live model; the offline grounded path is used by default.
- Legal content is not yet traced to official authoritative sources.

## 6. What is requested

Institutional mentorship, qualified legal review, AI inference infrastructure, secure hosting, testing devices, and controlled pilot partners — to mature the prototype toward a field-ready civic tool.

No guarantee of selection, funding, approval, or government adoption is implied or offered.

## 7. Repository

https://github.com/dhundhwana-arch/Nyaymitra-2.0 (branch `arena/812d6894-nyaymitra-2-0`, commit `792b529`)
