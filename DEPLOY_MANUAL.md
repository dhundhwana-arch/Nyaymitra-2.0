# NYAYMITRA 2.0 — Manual Cloudflare Pages Deployment

**Purpose:** Deploy the PWA frontend (`web/`) to Cloudflare Pages (free tier) using `wrangler` CLI.
**Branch:** `feature/hackindia-deployment` (commit `e4cda77`)
**Backend:** Not deployed. The frontend calls a separately hosted backend via `/api/*`.

---

## Prerequisites (one-time, on your machine)

You need a Cloudflare account and two credentials. **Do not commit these to the repository.**

| Credential | Where to create | GitHub secret name |
|------------|-----------------|--------------------|
| `CLOUDFLARE_API_TOKEN` | Cloudflare dashboard → My Profile → API Tokens → Create Token (Pages:Edit scope) | `CLOUDFLARE_API_TOKEN` |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare dashboard → right sidebar → Account ID | `CLOUDFLARE_ACCOUNT_ID` |

Install wrangler:

```bash
npm install -g wrangler
# or use npx without installing
npx wrangler --version   # should print 4.x
```

Authenticate (interactive, opens a browser):

```bash
wrangler login
```

Or set the token non-interactively:

```bash
export CLOUDFLARE_API_TOKEN=your_token
export CLOUDFLARE_ACCOUNT_ID=your_account_id
```

---

## Deploy the Frontend

From the repository root:

```bash
git clone https://github.com/dhundhwana-arch/Nyaymitra-2.0.git
cd Nyaymitra-2.0
git checkout feature/hackindia-deployment

# Deploy the static web directory to Cloudflare Pages
npx wrangler pages deploy web \
  --project-name=nyaymitra-frontend \
  --branch=feature/hackindia-deployment
```

Expected output includes a deployment URL like:
`https://nyaymitra-frontend.<account>.pages.dev`

No build step is required (`wrangler.toml` sets `publish = "web"` and a no-op build command).

---

## PWA Installation on Android

After deployment, open the live URL in Chrome/Edge on Android:

1. The browser shows an install prompt ("Add NYAYMITRA to Home screen"), or tap the three-dot menu → "Add to Home screen".
2. The app installs as a standalone PWA with its own icon.
3. The service worker registers on first visit and caches the app shell for offline use.
4. API calls fail gracefully offline (no personal data is cached).

No APK is produced. The Capacitor Android project in `android/` requires Java 17+ JDK and Android SDK, which are not available in this environment — see `docs/DEPLOYMENT_GUIDE.md` §7.

---

## Why GitHub Actions Cannot Deploy From This Branch

The CI deploy jobs (`.github/workflows/ci.yml`) are gated on:

```yaml
if: github.ref == 'refs/heads/main' && secrets.CLOUDFLARE_API_TOKEN != ''
```

They will **not** run on `feature/hackindia-deployment`. Deployment to production requires:
1. A repository owner to merge `feature/hackindia-deployment` into `main` (PR #1 is open, draft, not merged).
2. `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` added as repository secrets.

Neither condition is currently met.

---

## What Was Verified (Pre-Deployment)

| Check | Result |
|-------|--------|
| `web/_headers` | CSP, HSTS, X-Frame-Options: DENY, cache controls — present |
| `web/_redirects` | SPA fallback `/* /index.html 200` — present |
| `wrangler.toml` | `publish = "web"`, project `nyaymitra-frontend` — present |
| `web/manifest.webmanifest` | 10 icons, shortcuts, scope `/` — valid JSON |
| `web/sw.js` | Cache-first shell, offline fallback, no API caching — valid |
| `web/index.html` | Manifest link `<link rel="manifest" href="/manifest.webmanifest">` — present |
| `web/favicon.svg` | Present (cached by service worker) |
| `node --check web/app.js` | Pass |
| Tests | 226 passed, 92% coverage, pip-audit clean |

---

## What Was NOT Done

- No deployment was performed (no `CLOUDFLARE_API_TOKEN` available).
- No live URL exists to verify.
- No domain was purchased.
- No backend was deployed.
- No secret values were exposed or requested.

**Do not claim deployment succeeded without a verified live URL.**
