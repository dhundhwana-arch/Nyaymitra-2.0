# NYAYMITRA 2.0 — HackIndia Submission Checklist

**Project:** NYAYMITRA 2.0  
**Developed by:** Divyesh Bambhaniya  
**Hackathon:** [HackIndia — AI for Lawyers Hackathon](https://hackindia.org/2026/ai-for-lawyers-hackathon)  
**Track / Problem Statement:** PS-02 · Access to Justice (Legal Information Chatbot)  
**Team Name:** DIVYESH INNOVATION  
**Canonical Development Repo:** [dhundhwana-arch/Nyaymitra-2.0](https://github.com/dhundhwana-arch/Nyaymitra-2.0/tree/arena/2497125a-nyaymitra-2-0) (`arena/2497125a-nyaymitra-2-0`, commit `9b2ee1f49b70ca2cc8ebafa2f017f7e24cdeee4a`)  
**Provisioned HackIndia Repo:** `https://github.com/HackIndiaXYZ/ai-for-lawyers-hackathon-divyesh-innovation`  
**Code Freeze Deadline:** November 30, 2026 · 19:48 PST (December 1, 2026 · 09:18 IST)  

---

## 1. Official HackIndia Requirement Mapping

Verified from the official [HackIndia AI for Lawyers Hackathon](https://hackindia.org/2026/ai-for-lawyers-hackathon) event page (checked 2026-11-20):

| Official HackIndia Requirement | Evaluation Weight / Rule | Mapped NYAYMITRA 2.0 Deliverable | Actual Status |
| :--- | :--- | :--- | :--- |
| **Source Code (GitHub Repo)** | Required at code freeze | `dhundhwana-arch/Nyaymitra-2.0` (`arena/2497125a-nyaymitra-2-0`) → must be merged/pushed to provisioned `HackIndiaXYZ/ai-for-lawyers-hackathon-divyesh-innovation` | **PARTIAL** — Code verified on `arena/2497125a-nyaymitra-2-0` (475 tests passing); PR #2 merge & sync to HackIndiaXYZ repo pending owner action |
| **Working Legal AI Prototype** | Technical Implementation (40%) | FastAPI backend (`41` ops), SQLite+FTS5 (`22` tables), Vanilla JS SPA (`6` citizen routes + `/admin`), grounded offline AI guard | **COMPLETE (Local)** — Verified locally; live LLM provider & official Constitution PDFs not yet loaded |
| **Deployed Demo Link** | Required at code freeze | Render backend (`render.yaml` / `Dockerfile`) + Cloudflare Pages frontend (`wrangler.toml`) | **BLOCKED / PENDING** — 0 live deployments (Render Nov 9 build failed; Cloudflare needs `CLOUDFLARE_API_TOKEN`) |
| **Pitch Deck (≤ 5-Min Presentation)** | Presentation ≤ 5 min; UX (20%), Innovation (30%), Impact (10%) | `NYAYMITRA_2.0_HACKINDIA_FINAL_PRESENTATION.pptx` | **COMPLETE** — Created & visually verified in this package |
| **Demo Video & Live Walkthrough** | Listed in hackathon deliverables | `NYAYMITRA_2.0_HACKINDIA_DEMO_SCRIPT.md` | **SCRIPT READY / VIDEO PENDING** — Script complete; developer must record real screen capture of running app |
| **Explanation of AI Workflows & Sample Outputs** | Listed in hackathon deliverables | `NYAYMITRA_2.0_TECHNICAL_REPORT.pdf`, `NYAYMITRA_2.0_SYSTEM_ARCHITECTURE.md`, `NYAYMITRA_2.0_USER_GUIDE.pdf` | **COMPLETE** — Grounded in verified source code |
| **Exact Slide-Count Limit / Portal Template / Prize Details** | **Needs Confirmation** | Not specified on the public AI for Lawyers Hackathon page (prizes listed as `"TBD"` / `"fill in"`) | **NEEDS CONFIRMATION** — Verify on HackIndia team submission dashboard before uploading |

---

## 2. Final Submission Package Deliverable Inventory

| # | Deliverable Filename | Recommended Repo Path | Status | Verification Notes |
| :--- | :--- | :--- | :--- | :--- |
| A | `NYAYMITRA_2.0_HACKINDIA_FINAL_PRESENTATION.pptx` | `presentations/` | **Complete** | Validated with `validate_pptx.py` and visually inspected via rendered PNGs |
| B | `NYAYMITRA_2.0_TECHNICAL_REPORT.pdf` | `reports/` | **Complete** | Compiled via Chromium (`compile_and_render.py`) and visually inspected |
| C | `NYAYMITRA_2.0_USER_GUIDE.pdf` | `docs/user-guides/` | **Complete (No Live Screenshots)** | Compiled & visually inspected; explicitly notes live UI screenshots pending real-browser capture (zero fabricated screenshots) |
| D | `NYAYMITRA_2.0_SETUP_DEPLOYMENT_GUIDE.md` | `docs/submission/` | **Complete** | Aligned to branch `arena/2497125a-nyaymitra-2-0`, migrations `001–006`, `.env.example` |
| E | `NYAYMITRA_2.0_HACKINDIA_DEMO_SCRIPT.md` | `docs/submission/` | **Complete** | Strict 5-minute timeline covering only verified working features + fallbacks |
| F | `NYAYMITRA_2.0_SYSTEM_ARCHITECTURE.md` | `docs/architecture/` | **Complete** | Accurate Mermaid diagrams, 10 routers, 22 tables, security boundaries |
| G | `NYAYMITRA_2.0_TESTING_EVIDENCE.md` | `docs/testing/` | **Complete** | Clearly separates current session, 475 historical tests, unexecuted tests, and failed builds |
| H | `NYAYMITRA_2.0_SECURITY_PRIVACY_REPORT.md` | `docs/security/` | **Complete** | Documents actual controls & 6 known risks; disclaims independent certification |
| I | `NYAYMITRA_2.0_LIMITATIONS_AND_ROADMAP.md` | `docs/submission/` | **Complete** | Transparently documents B-1..B-11 blockers and 5-phase roadmap |
| J | `NYAYMITRA_2.0_HACKINDIA_SUBMISSION_CHECKLIST.md` | `docs/submission/` | **Complete** | Maps official HackIndia requirements and external action items |

*(Existing repository package `GOVERNMENT_SUBMISSION_PACKAGE/` with 10 PDFs and root docs remain untouched and preserved.)*

---

## 3. Required External Submission Steps (Owner Action Before Code Freeze)

1. **Commit & Push New Deliverables:** Place the 10 generated files into the recommended directories on `arena/2497125a-nyaymitra-2-0`, commit, and push to GitHub.
2. **Merge PR #2 & Update Repo Description:** Review and merge PR #2 into `main` on `dhundhwana-arch/Nyaymitra-2.0`, and update the GitHub repository description so it does not overclaim corpus or language completion.
3. **Sync Provisioned HackIndia Repo:** Push the verified release branch to `https://github.com/HackIndiaXYZ/ai-for-lawyers-hackathon-divyesh-innovation` (confirm team invite acceptance).
4. **Deploy Live Demo URL:**
   - Provision Render web service with persistent disk (`NYAYMITRA_DB_PATH` outside repo), `NYAYMITRA_ENV=production`, strong distinct `NYAYMITRA_ADMIN_TOKEN` and `NYAYMITRA_MONITOR_TOKEN`, and `--workers 1`.
   - Add `CLOUDFLARE_API_TOKEN` secret to GitHub Actions (or deploy `web/` directly via Cloudflare Pages) and verify `GET /api/v1/ready` returns `200`.
5. **Re-Run Local Verification & Capture Real Screenshots/Video:** Run `node scripts/e2e_activation.mjs` and `node scripts/smoke_web.mjs` on commit `9b2ee1f`, capture real browser screenshots of `#/home`, `#/assistant`, `#/complaint`, `#/library`, `#/glossary`, and `/admin` for `assets/screenshots/`, and record a ≤ 5-minute demo video following `NYAYMITRA_2.0_HACKINDIA_DEMO_SCRIPT.md`.
6. **Submit on HackIndia Portal:** Before **November 30, 2026, 19:48 PST (December 1, 2026, 09:18 IST)**, submit Project Description, Live Demo URL, GitHub Repository URL, Pitch Deck (`NYAYMITRA_2.0_HACKINDIA_FINAL_PRESENTATION.pptx`), and Demo Video on the HackIndia team dashboard. Confirm any portal-specific slide limit or template notice at upload time.
