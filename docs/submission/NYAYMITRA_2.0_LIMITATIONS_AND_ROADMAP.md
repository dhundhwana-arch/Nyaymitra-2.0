# NYAYMITRA 2.0 — Known Limitations & Future Roadmap

**Project:** NYAYMITRA 2.0  
**Developed by:** Divyesh Bambhaniya  
**Repository:** [dhundhwana-arch/Nyaymitra-2.0](https://github.com/dhundhwana-arch/Nyaymitra-2.0/tree/arena/2497125a-nyaymitra-2-0)  
**Canonical Branch:** `arena/2497125a-nyaymitra-2-0`  
**Verified Handover Commit:** `9b2ee1f49b70ca2cc8ebafa2f017f7e24cdeee4a`  

> **Honesty & Release Gate Summary:** Per [`MASTER_PROJECT_CONTEXT.md`](https://github.com/dhundhwana-arch/Nyaymitra-2.0/blob/arena/2497125a-nyaymitra-2-0/MASTER_PROJECT_CONTEXT.md), NYAYMITRA 2.0 is **Stage A (Engineering Merge): READY**, **Stage B (Supervised Evaluation): NOT READY** (blocked on B-1 & B-2), and **Stage C (Public Release): NOT READY**. The platform is a verified engineering prototype, not a finished legal-aid service.

---

## 1. Current Known Limitations & Blockers

### A. Unfinished Legal Corpus & Zero Human Verification (Release Blockers B-1 & B-2)
- **Constitution Coverage:** Only **9 of 395** Constitution articles are seeded as structural/explanatory records. **0 authoritative official Constitution texts** (English or Gujarati official PDFs from Legislative Department / India Code) have been ingested.
- **Human Legal Verification:** **0 entries** across Constitution articles, 11 departments, 5 triage guides, and 18 glossary terms have been signed off by a qualified human legal reviewer (`checked_by` / `last_checked_at`).
- **Quarantined Legacy Data:** 2,125 legacy Santali corpus rows (`data/legacy/constitution_articles_legacy_2026-11-07.jsonl.gz`, SHA-256 `b59f00b8...`) are intentionally quarantined and excluded from citizen retrieval due to unverified provenance.
- **No OCR Engine:** `tesseract` is not installed; scanned PDF ingestion has not been tested on real government PDFs.

### B. Multilingual & Voice Coverage Gaps
- **UI Locales:** Of 23 JSON locale catalogues under `web/locales/`, only **2 languages — English (`en`) and Gujarati (`gu`) — have full UI catalogues**. The remaining **21 locales are partial (5–10%, machine-translated)** and must not be represented as fully supported.
- **Script Rendering:** Real-device font rendering and Indic script shaping have not been visually tested on Android, iOS, or desktop browsers.
- **Voice I/O:** Web Speech API microphone input and speech synthesis are implemented in `web/app.js` but **untested on real browsers or audio hardware**.

### C. AI Provider & Runtime Limitations
- **Live LLM Untested:** `backend/app/ai/openai_compatible.py` has only been tested against a local stub HTTP server (`scripts/verify_ai_provider.py` exits `3` without credentials). All current demonstrations rely on `offline_grounded` fallback.
- **Single-Process SQLite Ceiling:** Synchronous SQLite + in-memory rate limiting are designed for single-process prototypes, not high-concurrency multi-worker production loads.

### D. Deployment, Mobile & QA Gaps
- **0 Live Deployments:** No public staging or production URL is live (`render.yaml`, `Dockerfile`, `wrangler.toml`, and `ci.yml` are configured, but earlier Render builds failed on 2026-11-09 and Cloudflare Pages is gated on the `CLOUDFLARE_API_TOKEN` secret).
- **Android APK Unbuilt:** `android/` (Capacitor wrapper `in.nyaymitra.app`, 53 files) is synced, but `./gradlew assembleRelease` is blocked by missing JDK 17+ and Android SDK.
- **No Real-Browser / Device / AT Testing:** All frontend E2E tests (`43/43`) ran in `jsdom` 25; PWA offline caching, mobile touch targets (`360 px`), and screen readers (NVDA/TalkBack) remain untested on real devices.
- **Operator Auth & DPDP Self-Service:** Admin console uses shared static tokens without MFA/RBAC; self-service citizen deletion and portability endpoints are not yet implemented.
- **Repository Housekeeping:** PR #2 is still open (branch `arena/2497125a-nyaymitra-2-0` is 62 commits ahead of `main`); several older root/submission docs reflect a superseded 226-test snapshot; GitHub repository description requires updating to reflect actual scope.

---

## 2. Phased Future Roadmap

| Phase | Target Gate | Concrete Engineering & Governance Milestones |
| :--- | :--- | :--- |
| **Phase 1: HackIndia Submission & Staging** *(Immediate — Before Nov 30, 2026)* | HackIndia Demo Ready | Merge PR #2 to `main` (with owner approval); fix GitHub repo description; re-run `scripts/e2e_activation.mjs` and `scripts/smoke_web.mjs` on commit `9b2ee1f`; configure `CLOUDFLARE_API_TOKEN` & Render persistent disk to bring up a live public demo URL; sync final code to `HackIndiaXYZ/ai-for-lawyers-hackathon-divyesh-innovation`. |
| **Phase 2: Authoritative Corpus & Legal Review** *(Stage B Gate)* | Supervised Evaluation Ready | Supply official English and Gujarati Constitution PDFs (Legislative Department / India Code); run `scripts/import_constitution_data.py` and diglot alignment; appoint qualified human legal reviewer to verify articles, 11 departments, 5 triage guides, and 18 glossary terms via `PATCH /admin/articles/{id}/verification`. |
| **Phase 3: Real-Device UX, Voice & Multilingual Polish** | Accessibility & Language Readiness | Execute real-browser (Chrome/Firefox/Safari), physical Android/iOS, PWA offline, Web Speech API voice I/O, and NVDA/TalkBack screen-reader tests; complete human-reviewed translations for priority Indian languages beyond `en` and `gu`. |
| **Phase 4: Production Hardening & Mobile Release** *(Stage C Gate)* | Public Citizen Release | Test and benchmark a live OpenAI-compatible LLM provider; replace shared admin tokens with per-user auth + MFA; migrate rate limiting to Redis and evaluate PostgreSQL for multi-worker concurrency; add citizen self-service deletion/export endpoints; build and sign Capacitor Android APK (`./gradlew assembleRelease`); conduct independent security penetration test. |
| **Phase 5: Ecosystem Expansion** *(Long-Term)* | Scalable Justice Access | Expand verified corpus to Bharatiya Nyaya Sanhita (BNS), BNSS, RTI Act, Consumer Protection Act, and state legal-aid directories (NALSA/GSLSA/DLSA); explore authorized integrations with official grievance/legal-aid channels only with formal institutional permission. |
