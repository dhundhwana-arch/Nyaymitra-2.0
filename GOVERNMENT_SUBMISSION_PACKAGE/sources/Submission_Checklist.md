# NYAYMITRA 2.0 — Submission Checklist

Intended for SSIP / Startup Srujan or similar government startup application portals. Confirm each field and supporting document before submitting.

## A. Applicant / project details

- [ ] Project name: NYAYMITRA 2.0
- [ ] Official description: AI-Powered Inclusive Justice Access & Navigation System
- [ ] Mission: make legal information and justice navigation easier to understand and access, particularly for ordinary citizens and rural communities
- [ ] Stage: functional software prototype / Proof of Concept (subject to independent evaluation)
- [ ] Repository URL: https://github.com/dhundhwana-arch/Nyaymitra-2.0
- [ ] Branch: `arena/812d6894-nyaymitra-2-0`
- [ ] Commit: `88e54a0`
- [ ] Pull request: #1 (open, draft) — owner approval required to merge

## B. Technical evidence

- [ ] Test suite: 226 passed, 0 failed (`pytest`)
- [ ] Coverage: 92% (`pytest --cov=backend/app`)
- [ ] Dependency audit: no known vulnerabilities (`pip-audit`)
- [ ] Database integrity: OK (`scripts/check_db.py`)
- [ ] Frontend syntax: pass (`node --check`)
- [ ] App startup verified: `/api/v1/ready` = 200
- [ ] Real AI model: NOT verified (exit 3) — blocker B-4; disclose honestly
- [ ] Human legal review: NOT complete (0 of 9 articles) — blocker B-2; disclose honestly

## C. Supporting documents (this package)

- [ ] Executive_Summary.pdf
- [ ] NYAYMITRA_2.0_Project_Report.pdf
- [ ] Technical_Architecture_Report.pdf
- [ ] Prototype_Progress_Report.pdf
- [ ] Legal_Privacy_Safety_Report.pdf
- [ ] Development_Roadmap.pdf
- [ ] Risk_Register.pdf
- [ ] Government_Pitch_Deck.pdf
- [ ] Demo_Script.pdf
- [ ] Submission_Checklist.pdf
- [ ] EVIDENCE_MATRIX.md
- [ ] README.md (package)
- [ ] Editable markdown sources in `sources/`

## D. Declarations (do not mark complete unless true)

- [ ] Legally certified — NOT COMPLETE (requires independent legal review)
- [ ] Government-approved — NOT COMPLETE
- [ ] AI inference verified — NOT COMPLETE (blocker B-4)
- [ ] Real-device/accessibility tested — NOT COMPLETE (blocker B-3)
- [ ] Official legal sources loaded — NOT COMPLETE (blocker B-1)

## E. Approvals required before submission

- [ ] Repository owner reviews and approves merge of PR #1 (no force push)
- [ ] Named human legal reviewer appointed and sign-off obtained
- [ ] Real AI model verification completed (blocker B-4)
- [ ] Real-device / screen-reader testing completed (blocker B-3)

## F. Size limit

Keep the combined submission PDFs within the portal's stated limit (e.g., 5 MB if applicable). Individual PDFs in this package are text-based and small; verify total before upload.

## G. What must NOT be claimed

- Not legally certified / compliant / government-approved without independent evidence.
- Not a replacement for courts, lawyers, police, or government.
- AI not verified with a live model; offline fallback is default.
- Legal content not traced to official authoritative sources.

## Repository

https://github.com/dhundhwana-arch/Nyaymitra-2.0 | commit `88e54a0`
