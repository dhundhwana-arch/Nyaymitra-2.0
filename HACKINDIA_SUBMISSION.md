# NYAYMITRA 2.0 — HackIndia Submission Package

**Repository:** `dhundhwana-arch/Nyaymitra-2.0`
**Branch:** `arena/812d6894-nyaymitra-2-0` (HEAD `8b1e652`)
**Feature branch:** `feature/hackindia-deployment` (HEAD `c29fb8d`, pushed to origin)
**Pull request:** #1 — open draft, base `main` (`53df9ea`), head `8b1e652`, mergeable, **not merged** (owner approval required)

---

## 1. What NYAYMITRA 2.0 is

NYAYMITRA 2.0 is an inclusive justice-access and legal-navigation platform for citizens of India. It helps a citizen:

- Describe a problem in Gujarati or English
- Find the constitutional provision that applies
- Understand the official next step
- Prepare a complaint draft
- Reach the right department or free-legal-aid channel (NALSA/DLSA, toll-free 15100)

**Not a court, not a lawyer, not legal advice.** Every legal statement carries `requires_human_verification` until a qualified reviewer signs off. No legal text is invented.

---

## 2. Delivery mechanisms

### 2.1 Cloudflare Pages + PWA (primary, ready)

The frontend (`web/`) is a static SPA hosted on Cloudflare Pages:

| Artefact | Path | Status |
|----------|------|--------|
| Security headers (CSP, HSTS, X-Frame-Options, etc.) | `web/_headers` | Created |
| SPA fallback redirects (hash-based routes) | `web/_redirects` | Created |
| Cloudflare Pages config | `wrangler.toml` | Created |
| PWA manifest (10 icons, shortcuts, screenshots) | `web/manifest.webmanifest` | Updated |
| Service worker (cache-first shell, offline fallback, no API caching) | `web/sw.js` | Created |
| PWA icons (72–512 px + 2 maskable) | `web/assets/icons/` | Generated |
| Install button UI + `beforeinstallprompt` handling | `web/app.js` | Updated |
| Install button styles | `web/styles.css` | Updated |
| CI deployment jobs | `.github/workflows/ci.yml` | Added (`deploy-frontend`, `deploy-frontend-skip`) |

**Deploy:** `wrangler pages deploy web --project-name=nyaymitra --branch=main`
(gated on `CLOUDFLARE_API_TOKEN` secret in CI; not yet deployed live).

**PWA install:** Open the deployed URL → install button / "Add to Home Screen" → standalone app with offline app shell.

### 2.2 Capacitor Android (native wrapper — APK build BLOCKED)

| Artefact | Path | Status |
|----------|------|--------|
| Capacitor config | `capacitor.config.js` | Created |
| Node project | `package.json` | Created |
| Android native project | `android/` | Added + synced |
| `capacitor.config.json` (in android assets) | `android/app/src/main/assets/` | Generated |

- `npx cap add android` — succeeded
- `npx cap sync android` — succeeded (web assets copied)
- `./gradlew assembleRelease` — **BLOCKED**: no Java JDK and no Android SDK in this environment; only `npx`/Node.js is available

**Required to unblock:** Java 17+ JDK, Android SDK, license acceptance, then `cd android && ./gradlew assembleRelease`. A qualified human with Android Studio must complete this. Do not simulate an APK.

---

## 3. Verification status

| Check | Result |
|-------|--------|
| Tests | 226 passed (`python -m pytest`) |
| Coverage | 92% (`--cov=backend/app`) |
| Dependency audit | `pip-audit` clean |
| DB integrity | OK (4 migrations applied, 9 articles, 11 departments) |
| Frontend syntax | `node --check` pass |
| App startup | `/api/v1/ready` returns 200 |
| CI push run | `42599240604` success on `8b1e652` |
| PR #1 | Open draft, mergeable |

CI evidence commits: `42599240604` on `8b1e652`; `42598098956` on `947698e`.

Source snapshot for audit: `cc56d0e`.

---

## 4. Blockers (none resolved)

| Blocker | Description | Owner | Required to close |
|---------|-------------|-------|-------------------|
| B-1 | No authoritative Constitution text | Divyesh Bambhaniya | Official Constitution PDF from India Code / Legislative Department ingested via `scripts/ingest_constitution.py` |
| B-2 | No human legal verification | Divyesh to appoint | Named advocate/legal-aid officer signs off articles, departments, triage guides |
| B-3 | No real-browser / device / assistive-technology testing | Divyesh (or anyone with a phone) | Screenshots at 360/414/desktop, voice attempt on real phone, screen-reader pass |
| B-4 | No physical mobile device / real browser automation | — | Static + structural assertions in CI; manual device test script in `docs/TESTING_REPORT.md` |
| B-5 | No OCR engine (`tesseract`), no scanned PDFs | — | OCR path labelled unverified for scanned input |

Deployment-specific blocker: **Android APK build** — no Java/Android SDK available; only `npx`.

---

## 5. Government submission package

Located at `GOVERNMENT_SUBMISSION_Package/`:

- 10 source markdown documents (`sources/*.md`)
- 10 rendered PDFs (all <5 MB, all valid)
- `EVIDENCE_MATRIX.md` — 6 traceability categories
- `README.md` — package overview
- `build_pdfs.py` — PDF generation script

Commit references distinguished in every document:
- Audited source snapshot: `cc56d0e`
- Package commit: `947698e` (Markdown metadata only)
- Tests executed on: `792b529`
- CI evidence: `42599240604` on `8b1e652`; `42598098956` on `947698e`

No self-referential final commit hash embedded in any PDF. All data synthetic; no citizen data; no secrets committed.

---

## 6. Known limitations

- No live AI model available (`verify_ai_provider.py` exits 3); offline grounded provider only
- 0 of 9 constitution articles have authoritative source text
- 0 of 11 departments/helplines human-verified
- No real-device testing (responsiveness, Gujarati font shaping, voice, screen reader)
- APK build blocked (no Java/Android SDK)
- Not claimed to be penetration-tested, government-certified, or legally compliant without independent evidence

---

## 7. Files in this submission

| Category | Path |
|----------|------|
| Backend API | `backend/app/` |
| Migrations | `backend/migrations/` |
| Tests | `backend/tests/` |
| Frontend (PWA) | `web/` |
| Capacitor Android | `android/`, `capacitor.config.js`, `package.json` |
| Icon generation | `scripts/generate_pwa_icons.py` |
| Cloudflare config | `wrangler.toml`, `web/_headers`, `web/_redirects` |
| CI | `.github/workflows/ci.yml` |
| Deployment guide | `docs/DEPLOYMENT_GUIDE.md` |
| Blockers | `docs/REMAINING_BLOCKERS.md` |
| Government package | `GOVERNMENT_SUBMISSION_Package/` |
| Audit report | `docs/REPOSITORY_AUDIT.md` |

---

## 8. How to run locally

```bash
git clone https://github.com/dhundhwana-arch/Nyaymitra-2.0.git
cd Nyaymitra-2.0
git checkout arena/812d6894-nyaymitra-2-0
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
python scripts/init_db.py --info
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000` — the PWA install button will appear after the service worker registers.

For PWA icons: `python scripts/generate_pwa_icons.py` (requires Pillow).

For Android: `npx cap sync android` then open `android/` in Android Studio (APK build requires Java + Android SDK).

---

**Submission date:** 2026-11-07 (local timezone UTC, Jamnagar, Gujarat, IN)

**Owner approval for PR merge:** Required — PR #1 stays a draft until explicitly approved.
