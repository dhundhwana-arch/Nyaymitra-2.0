# NYAYMITRA 2.0 — Government Pitch Deck (8–10 slides)

Slide format: one section per slide. Intended for a 5–7 minute presentation.

---

## Slide 1 — Title

NYAYMITRA 2.0
AI-Powered Inclusive Justice Access & Navigation System
A functional software prototype / Proof of Concept
Presented for institutional mentorship and pilot support
Not legal advice; not a replacement for lawyers or courts

---

## Slide 2 — Problem

Many Indians face barriers to accessing or understanding legal information (scale to be validated by field research).
- Legal provisions are formal and English-heavy.
- Citizens do not know which article, statute, or department applies.
- Free legal aid (NALSA/DLSA, 15100) is under-used due to low awareness.
- Complaint drafting is intimidating and error-prone.

Result: constitutional rights (Article 39A) may remain theoretical for many.

---

## Slide 3 — Solution

NYAYMITRA 2.0 guides citizens to understand, navigate, and act:
- Plain-language legal answers with citations (English + Gujarati).
- Department directory, triage guides, glossary.
- Guided complaint drafting with consent, preview, and token retrieval.
- Offline-first — works with no AI key, no internet, no external model.

---

## Slide 4 — Innovation

- Offline-first deterministic grounding: answer guard rejects uncited article references (technical control; legal-source accuracy validation pending).
- Multilingual with Gujarati digit normalisation for article references.
- Data protection by design: token hashing, rate limiting, PII redaction, 180-day retention.
- Transparency: every answer shows sources, verification status, warnings, disclaimers.

---

## Slide 5 — Working prototype (evidence)

- 226 automated tests pass; 92% coverage; pip-audit clean.
- Database integrity OK; 4 migrations; 0 missing indexes.
- App starts; `/api/v1/ready` = 200; offline provider active.
- jsdom smoke test: all citizen journeys and admin console work.
- Legal content NOT yet verified (0 of 9 articles) — reviewer ready, appointment needed.

---

## Slide 6 — Architecture

Frontend: vanilla JS/HTML/CSS, no CDN, accessible.
Backend: FastAPI (Python 3.11), SQLite.
AI/RAG: FTS5 retrieval + citation guard + offline fallback.
Deployment: Docker, systemd, Render shape; .env.example (no secrets).

---

## Slide 7 — Evidence of progress

- Repository: https://github.com/dhundhwana-arch/Nyaymitra-2.0
- Branch `arena/812d6894-nyaymitra-2-0`, commit `cc56d0e`
- PR #1 open, draft, mergeable; CI green.
- Full documentation suite: security, privacy, IP, legal, setup, audit.

---

## Slide 8 — Social impact (projected, pending field validation)

- Potential for faster, cheaper first-level legal navigation (impact not yet measured).
- Potential to reduce load on legal-aid bodies for simple queries (pending pilot evidence).
- Greater rights awareness in rural/under-served communities (objective, not yet measured).
- Reusable open prototype for civic technology in India.

---

## Slide 9 — Roadmap and support

Needed: qualified legal reviewers, AI inference infrastructure, testing devices, secure hosting, pilot partners.
Milestones: legal review (M1), AI verified (M1–2), device testing (M2), pilot (M2–3), field-ready prototype (M3).

---

## Slide 10 — Closing request

Review PR #1; appoint a legal reviewer; support AI inference and device testing; consider a controlled pilot with a legal-aid body.
No guarantee of selection, funding, approval, or adoption is implied.

---

Repository: https://github.com/dhundhwana-arch/Nyaymitra-2.0 | commit `cc56d0e`
