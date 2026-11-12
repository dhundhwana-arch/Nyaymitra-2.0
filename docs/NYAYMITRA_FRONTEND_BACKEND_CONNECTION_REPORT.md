# NYAYMITRA 2.0 — Frontend ↔ Backend Connection Report

**Date:** 2026-11-12 (UTC) · **Branch:** `arena/08f8f3c5-nyaymitra-2-0`

Scope note: the live frontend and backend addresses were not provided and the sandbox cannot reach
external sites, so the causes below were established **from the repository's deployment files** and
reproduced locally. They were not observed on the live sites.

## 1. Why the live site showed 404 / "Data Not Available"

| # | Cause | Evidence | Effect on a separately hosted frontend |
|---|---|---|---|
| 1 | `web/_redirects` shipped the placeholder `/api/*  https://YOUR_BACKEND_URL/api/:splat  200` | file on `feature/hackindia-deployment` | Every API call 404s. Cloudflare Pages also cannot proxy to another domain from `_redirects`, so the line could not have worked even with a real address. |
| 2 | API address hard-coded as `/api/v1` in `web/app.js` and `web/admin.js` | source | The frontend could only ever call its own host. |
| 3 | Backend sent no CORS headers | `NYAYMITRA_ALLOWED_ORIGINS` was read into settings but never used | A browser blocks every cross-site API call. |
| 4 | Frontend CSP `connect-src 'self'` in `web/_headers` | file | The browser blocks calls to any other host. |
| 5 | Docker image had no seed data (`.dockerignore` excluded `data/`, `Dockerfile` did not copy `data/seed`) | files; fix existed only on the other rebuild branch | Backend runs but every table is empty. |
| 6 | `/sw.js` not served by the backend; service worker pre-cached `/api/openapi.json` | 404 reproduced locally | Service-worker install fails on some hosts. |
| 7 | Assistant citation links pointed to `#/library/Article14` | 404 reproduced locally | Every "source" link in an answer opened "not found". |

## 2. What was changed

| Area | Change | Files |
|---|---|---|
| API address | Read from `window.NYAYMITRA_CONFIG.apiBase` (empty = same origin) | `web/config.js` (new), `web/app.js`, `web/admin.js`, both HTML pages |
| CORS | `CORSMiddleware`, only for origins in `NYAYMITRA_ALLOWED_ORIGINS`; no credentials; GET/POST/PATCH/OPTIONS | `backend/app/main.py` |
| Redirects | Placeholder proxy removed; `/admin` mapped; SPA fallback kept | `web/_redirects` |
| CSP | `connect-src` set together with the API address by one command | `scripts/configure_frontend.py` (new), `web/_headers` |
| Static routes | Backend now serves `/config.js` and `/sw.js` | `backend/app/main.py` |
| Service worker | Cache bumped to `nyaymitra-v2`; `/config.js` added; `/api/openapi.json` removed | `web/sw.js` |
| Seed in image | `data/seed` copied into the image (merged from the other branch) | `Dockerfile`, `.dockerignore` |
| Env docs | `NYAYMITRA_ALLOWED_ORIGINS` documented | `.env.example`, `render.yaml` |
| Error text | Network failure now says the server could not be reached (gu/en) | `web/app.js` |

## 3. API routes

Repaired or added:

| Route | Status before | Now |
|---|---|---|
| `GET /api/v1/library` | did not exist | list + `q`, `category`, `content_language`, paging, facets |
| `GET /api/v1/library/{category}/{key}` | did not exist | item detail with source |
| `GET /config.js`, `GET /sw.js` | 404 | 200 |
| `POST /api/v1/ai/explain` | worked; wrong guide for some English questions; silent about a missing named article | fixed |
| all `/api/*` from another origin | blocked (no CORS) | allowed for configured origins |

Already working once the database is seeded (unchanged): `/meta`, `/health`, `/ready`,
`/constitution/articles`, `/constitution/articles/{no}`, `/constitution/parts`,
`/constitution/coverage`, `/departments`, `/ai/glossary`, `/complaints*`, `/documents*`, `/feedback`.
Response formats were not changed.

## 4. How to connect the deployed sites (needs your approval — nothing was deployed)

**Option A — one website (simplest).** The backend already serves the frontend
(`NYAYMITRA_SERVE_WEB=true` in `render.yaml`). Redeploy the backend from this branch and use its
address. No CORS or configuration needed.

**Option B — two websites (e.g. Cloudflare Pages + Render).**

1. `python scripts/configure_frontend.py --api-base https://<your-backend-host>` and commit the two
   edited files (`web/config.js`, `web/_headers`).
2. On the backend set `NYAYMITRA_ALLOWED_ORIGINS=https://<your-frontend-host>` and redeploy.
3. Redeploy the frontend from `web/`.
4. Check: `node scripts/e2e_activation.mjs https://<frontend> https://<backend>`.

On Render's free plan the database is rebuilt from the seed at every restart; complaints and
uploads are lost (already stated in `render.yaml`).

## 5. Test results

### Unit and API integration tests (pytest, temporary database)

| Suite | Result |
|---|---|
| `backend/tests` — `.venv/bin/python -m pytest` | **260 passed, 0 failed** (240 existing + 20 new in `test_data_activation.py`) |
| `tests/test_phase3c.py` — `.venv/bin/python -m pytest tests` | **15 passed, 0 failed** (3 tests removed with the retired table) |

New tests cover: CORS on/off/preflight/error responses, config and service-worker routes, no
placeholder address shipped, the configure script, exact attribution text, library
list/filters/search/detail/404, Santali rows never exposed, assistant missing-article and
explanation labels, citation links.

### End-to-end tests against the running application (local, jsdom)

`scripts/e2e_activation.mjs` loads the real pages, clicks through them and records every network call.

| Layout | Result |
|---|---|
| Same origin — backend serves the site (`:8000`) | **31/31 passed** |
| Separate sites — static frontend `:3000`, backend `:8000`, CORS enforced by the script | **31/31 passed** |
| Wrong origin | no `Access-Control-Allow-Origin` header returned |
| Existing `scripts/smoke_web.mjs` | OK — all citizen journeys; admin console skipped (no token set) |

| Step | Result |
|---|---|
| 1. Open frontend | pass — `/api/v1/meta` 200 |
| 2–3. Constitution, Parts and Articles | pass — 4 parts, 9 articles, Part III = 6 |
| 4. Article detail | pass — Article 14 content, source, badges, "text not loaded" notice |
| 5. English ↔ Gujarati | pass |
| 6. Library | pass — 43 items |
| 7. Search | pass — "refund" → consumer guide |
| 8. Filters | pass — Offices 11; Gujarati content 43 |
| 9. Assistant, Gujarati | pass — legal-aid guide; Article 14 cited for an equality question |
| 10. Assistant, English | pass |
| 11. Source references | pass — link opens Article 14 |
| 12. Unavailable data | pass — Article 300A reported unavailable; empty search says "No results" |
| 13. Network | pass — 27 calls: 26×200, 1×404 (the deliberate 300A request), 0 blocked |

### Deployed-website tests

**None run.** The live addresses are unknown and unreachable from the sandbox, and nothing was
deployed. The live site will keep its current behaviour until redeployed.

### Not covered

Real browser rendering, mobile layout, service-worker behaviour, speech input, a live AI provider,
and the admin console.

## 6. Remaining issues

1. Owner approval and site addresses are needed to deploy and to run the live check.
2. `web/config.js` ships with same-origin settings; Option B needs the one command in §4.
3. The Android (Capacitor) build bundles `web/`; it needs `apiBase` set before building, since an
   app has no "same origin" backend. Not built or tested here.
4. See the data report for the content gap: 9 summaries, no official text in either language.
