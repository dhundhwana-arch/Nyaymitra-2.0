# NYAYMITRA 2.0 — Project Report

## 1. Problem statement

Ordinary citizens, particularly in rural India and among those with limited digital or legal literacy, face significant barriers to accessing justice:

- Legal provisions are written in formal, English-heavy language that is difficult to understand.
- Citizens often cannot identify which constitutional article, statute, or government department applies to their situation.
- Free legal aid (NALSA/DLSA, helpline 15100) exists but is under-utilised because people do not know how to reach it or what to ask.
- Complaint drafting is intimidating; mistakes can weaken a case or lead to rejection.

## 2. Why the problem matters

Access to justice is a constitutional goal (Article 39A: equal justice and free legal aid). When citizens cannot understand their rights or reach the right authority, rights remain theoretical. A guided, multilingual, offline-capable navigation tool reduces this gap at low cost.

## 3. Proposed solution

NYAYMITRA 2.0 is an AI-powered inclusive justice-access and navigation system:

- **Information**: plain-language answers with citations, in English and Gujarati.
- **Navigation**: department directory, triage guides, glossary.
- **Action**: guided complaint drafting with consent, preview, and token-based retrieval.
- **Safety**: no legal verdicts, no outcome guarantees, offline-first by default, PII redacted before local storage.

## 4. Target beneficiaries

- Rural and semi-urban citizens seeking legal information.
- People with limited English proficiency (Gujarati support).
- Citizens unsure which department or legal-aid body to approach.
- Persons with disabilities (keyboard navigation, focus rings, aria labels — implemented, not yet screen-reader tested).

## 5. Innovation and uniqueness

- Offline-first deterministic grounding: answers are retrieved from a curated corpus and validated, so the system does not invent legal citations.
- Multilingual (English/Gujarati) with Gujarati digit normalisation for article references.
- Citizen data protection by design: role-based tokens (hashed), rate limiting, redaction before logging, 180-day retention, purge tooling.
- Transparency: every answer carries verification status, warnings, and disclaimers; unverified content is explicitly labelled.

## 6. Technology used

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.11), SQLite |
| Frontend | Vanilla JavaScript, HTML/CSS (no CDN, no inline scripts) |
| AI / RAG | Retrieval over constitution articles + triage guides; OpenAI-compatible provider optional; offline grounded fallback |
| Testing | pytest, pytest-cov, jsdom smoke test |
| Security | pip-audit, CSP, rate limiting, constant-time token comparison |
| Deployment | Docker, systemd, Render (free-tier shape) |

## 7. System architecture

The backend is a FastAPI application with routers for health, constitution, AI answers, complaints, documents, departments, feedback, and administration. Retrieval uses FTS5 full-text search over articles; triage matches questions to guides; an answer guard validates citations and rejects unsafe legal advice. The frontend is a self-hosted single-page app served from `/web`.

## 8. Current prototype status

| Area | Status |
|------|--------|
| Core features implemented | Verified complete (226 tests pass) |
| Tests | 226 passed, 92% coverage |
| Database | Migrated + seeded; integrity OK |
| AI with real model | Blocked (no model runtime) |
| Legal content verified | Blocked (0 of 9 articles verified) |
| Accessibility | Implemented, not screen-reader/device tested |
| Legacy corpus | 2,125 quarantined chains; source provenance/copyright unresolved; never served |

## 9. Demonstrable features

- Ask a legal question in English or Gujarati → answer with citations + disclaimer.
- Browse constitution articles and departments.
- File a complaint through preview → consent → confirmation → token receipt.
- Retrieve a saved complaint with reference + token.
- Admin console: stats, verification queue, metrics, backup.

## 10. Expected social impact (projected, pending field validation)

- Potential for faster, cheaper first-level legal navigation for citizens (impact not yet measured).
- Potential to reduce load on legal aid bodies for simple information queries (pending pilot evidence).
- Greater awareness of rights and available departments (objective, not yet measured).
- A reusable, open prototype for civic technology in India.

## 11. Future development plan

- Load official Constitution source documents (owner to supply PDFs).
- Complete human legal review of all articles, departments, triage guides.
- Verify AI inference with a live model (Ollama `llama3.2:3b`).
- Conduct real-device, browser, and screen-reader testing.
- Add self-service data deletion and export.
- Pilot with a DLSA or legal-aid NGO.

## 12. Repository

https://github.com/dhundhwana-arch/Nyaymitra-2.0
Branch: `arena/812d6894-nyaymitra-2-0` | Commit: `cc56d0e` | PR #1 (open, draft)
