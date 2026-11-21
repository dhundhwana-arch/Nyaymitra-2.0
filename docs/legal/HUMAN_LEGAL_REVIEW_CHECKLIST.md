# HUMAN_LEGAL_REVIEW_CHECKLIST.md

NYAYMITRA 2.0 — Human legal review checklist
=============================================

## Purpose

This is the reviewer's work order. Every item below is **unverified** in the product and
must be signed off by a qualified Indian legal practitioner before the corresponding
content is presented to citizens as checked. Nothing in this checklist is a verification
record until a reviewer completes the sign-off fields.

## How to use

1. Open the source document at the locator given.
2. Compare the stored text against the source.
3. Record `checked_by`, `checked_on`, `source_consulted` and `notes`.
4. If an item cannot be checked, set its status to `unverified` with a note — do not
   leave it looking checked.
5. Export: `GET /api/v1/admin/review-packet?format=markdown` (monitor token required).

## Items requiring review

| # | Kind | Ref | Title / category | Stored status | Source locator | Sign-off |
|---|------|-----|------------------|---------------|----------------|----------|
| 1 | article | Preamble | Preamble of the Constitution of India | owner_authored_summary | not recorded | __________________ |
| 2 | article | Article 14 | Article 14 | owner_authored_summary | not recorded | __________________ |
| 3 | article | Article 19 | Article 19 | owner_authored_summary | not recorded | __________________ |
| 4 | article | Article 19A | Article 19A | owner_authored_summary | not recorded | __________________ |
| 5 | article | Article 21 | Article 21 | owner_authored_summary | not recorded | __________________ |
| 6 | article | Article 21A | Article 21A | owner_authored_summary | not recorded | __________________ |
| 7 | article | Article 22 | Article 22 | owner_authored_summary | not recorded | __________________ |
| 8 | article | Article 32 | Article 32 | owner_authored_summary | not recorded | __________________ |
| 9 | article | Article 39A | Article 39A | owner_authored_summary | not recorded | __________________ |
| 10 | department | nalsa-legal-aid | National Legal Services Authority | requires_human_verification | not recorded | __________________ |
| 11 | department | dlsa-district | District Legal Services Authority | requires_human_verification | not recorded | __________________ |
| 12 | department | tele-law-csc | Tele-Law / Common Service Centre | requires_human_verification | not recorded | __________________ |
| 13 | department | cyber-crime-portal | Cyber Crime Reporting Portal | requires_human_verification | not recorded | __________________ |
| 14 | department | land-records | Land records department | requires_human_verification | not recorded | __________________ |
| 15 | department | consumer-forum | Consumer forum | requires_human_verification | not recorded | __________________ |
| 16 | department | women-helpline | Women helpline | requires_human_verification | not recorded | __________________ |
| 17 | department | labour-office | Labour office | requires_human_verification | not recorded | __________________ |
| 18 | department | grievance-portal | Centralized Public Grievance Portal | requires_human_verification | not recorded | __________________ |
| 19 | department | dlsa-gujarat | Gujarat State Legal Services Authority | requires_human_verification | not recorded | __________________ |
| 20 | department | gujarat-high-court | Gujarat High Court | requires_human_verification | not recorded | __________________ |
| 21 | triage | cyber_fraud | Cyber fraud / financial fraud | requires_human_verification | not recorded | __________________ |
| 22 | triage | land_revenue | Land / revenue | requires_human_verification | not recorded | __________________ |
| 23 | triage | legal_aid | Free legal aid | requires_human_verification | not recorded | __________________ |
| 24 | triage | consumer | Consumer | requires_human_verification | not recorded | __________________ |
| 25 | triage | other | Other | requires_human_verification | not recorded | __________________ |
| 26 | glossary | — | 18 glossary terms (all) | not_reviewable_in_product | seed data | Report corrections to maintainer |

## Glossary note

Glossary entries are seed data with no per-row verification column in the database, so
they cannot be marked `verified` in the product yet. The reviewer should report
corrections to the maintainer instead of signing off here.

## Sign-off fields (per item)

* Checked by (name and qualification): ________________________
* Checked on (date): ________________________
* Source consulted (title + URL / page): ________________________
* Notes / corrections: ________________________

## Reviewer attestation

"I have compared each item above against the source cited and confirm the stored text
matches, or I have marked the item unverified with a note."

Reviewer name: ________________________   Signature: ________________________   Date: __________

## Disclaimer

Research prototype. Legal content has not been verified by a qualified reviewer. This
checklist is a work order, not a verification record.
