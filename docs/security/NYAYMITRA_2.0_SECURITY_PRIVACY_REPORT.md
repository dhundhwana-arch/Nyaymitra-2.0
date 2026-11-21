# NYAYMITRA 2.0 — Security & Privacy Report

**Project:** NYAYMITRA 2.0  
**Developed by:** Divyesh Bambhaniya  
**Repository:** [dhundhwana-arch/Nyaymitra-2.0](https://github.com/dhundhwana-arch/Nyaymitra-2.0/tree/arena/2497125a-nyaymitra-2-0)  
**Canonical Branch:** `arena/2497125a-nyaymitra-2-0`  
**Verified Handover Commit:** `9b2ee1f49b70ca2cc8ebafa2f017f7e24cdeee4a`  
**Primary Sources:** [`SECURITY.md`](https://github.com/dhundhwana-arch/Nyaymitra-2.0/blob/arena/2497125a-nyaymitra-2-0/SECURITY.md), [`PRIVACY.md`](https://github.com/dhundhwana-arch/Nyaymitra-2.0/blob/arena/2497125a-nyaymitra-2-0/PRIVACY.md), [`backend/app/main.py`](https://github.com/dhundhwana-arch/Nyaymitra-2.0/blob/arena/2497125a-nyaymitra-2-0/backend/app/main.py)

> **Compliance & Certification Disclaimer:** All security and privacy controls documented here are **self-assessed engineering controls** verified through automated unit tests (`test_admin_and_security.py`, `test_metrics_and_privacy.py`, `test_production_preflight.py`, `test_retention.py`). **NYAYMITRA 2.0 has NOT undergone an independent security audit, third-party penetration test, ISO 27001 certification, or formal legal compliance opinion under India's Digital Personal Data Protection (DPDP) Act, 2023.**

---

## 1. Implemented Security Controls

| Control Domain | Implementation Details (Verified in Source & Docs) |
| :--- | :--- |
| **HTTP Security Headers** | `SecurityHeadersMiddleware` injects `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and a strict `Content-Security-Policy` disallowing inline scripts, `eval`, and external origins beyond `'self'`. |
| **XSS Prevention** | Citizen and admin frontends (`web/app.js`, `web/admin.js`) use `textContent`-only DOM insertion (no `innerHTML`). Zero third-party CDNs or external script tags are loaded. |
| **CORS Restrictions** | Disabled by default. Enabled only when `NYAYMITRA_ALLOWED_ORIGINS` is explicitly set (`allow_credentials=False`, `allow_methods=["GET","POST","PATCH","OPTIONS"]`, restricted headers `Content-Type`, `X-Admin-Token`, `X-Access-Token`, `X-Request-ID`, `max_age=600`). |
| **Rate Limiting** | In-memory fixed-window per client IP and endpoint class (`60s` default window): `read` **120/min**, `write` **30/min**, `AI` **20/min**, `admin` **10/min**. |
| **Payload & Upload Validation** | Request body capped at `524,288` bytes (512 KB); multipart uploads capped at `10,485,760` bytes (10 MB). Allowed formats: PDF, JPEG, PNG, WebP validated against actual file magic bytes (spoofed `.txt` renamed `.pdf` is rejected). Document downloads enforce `X-Content-Type-Options: nosniff` and `Cache-Control: no-store`. |
| **Production Startup Preflight** | When `NYAYMITRA_ENV=production`, `create_app()` refuses to start if `NYAYMITRA_ADMIN_TOKEN` or `NYAYMITRA_MONITOR_TOKEN` is unset, short, placeholder-like, low-entropy, or identical; if `NYAYMITRA_DB_PATH` lies inside the Git repository; or if `NYAYMITRA_TRUST_PROXY_HEADERS=true` without `NYAYMITRA_ALLOWED_ORIGINS`. |
| **API Surface Minimization** | Interactive Swagger UI (`/api/docs`), ReDoc (`/redoc`), and root `/health` are disabled (`404` by design). Only machine-readable `/api/openapi.json` is exposed. |
| **AI Prompt-Injection & Grounding Guard** | `backend/app/ai/guard.py` validates input length (`5–500` chars), blocks prompt-injection patterns, refuses ungrounded queries (0 FTS5 rows), validates citations strictly against retrieved IDs (max 4 rows), and filters judicial outcome/guilt-prediction language. |

---

## 2. Authentication & Access Restrictions

| Role / Actor | Auth Mechanism | Permitted Actions | Enforced Restrictions |
| :--- | :--- | :--- | :--- |
| **Citizen (Anonymous)** | None required | Browse articles/departments/glossary, ask AI, preview/submit complaints, upload documents | Must tick explicit consent (`confirmed: true`) before complaint write |
| **Complaint / Document Owner** | One-time high-entropy token (`?token=...`), stored only as SHA-256 hash | Retrieve own saved complaint or uploaded document metadata/bytes | Wrong token returns generic `404` (eliminates enumeration oracle) |
| **Monitor (`monitor`)** | `NYAYMITRA_MONITOR_TOKEN` via `X-Admin-Token` or `Bearer` (constant-time compare) | Read-only `/admin/*` endpoints (`stats`, `verification-queue`, `queries`, `answers`, `errors`, `audit`, `complaints`, `documents`, `sources`, `metrics`, `legacy-chunks`) | **Cannot** read complaint descriptions, contact info, or uploaded document contents; **cannot** mutate state |
| **Administrator (`admin`)** | `NYAYMITRA_ADMIN_TOKEN` via `X-Admin-Token` or `Bearer` (constant-time compare) | All `monitor` reads + `PATCH /admin/articles/{id}/verification` + `POST /admin/backup` | **Cannot** read citizen complaint text or uploaded files; leaving both tokens empty disables `/admin` with HTTP `403` |

No server-side sessions or tracking cookies are used.

---

## 3. Sensitive Data Handling, Privacy & Logging

### Data Minimization (`PRIVACY.md`)
- **Collected (Complaint Flow):** Category, title, description, consent flag (mandatory); incident date, location/district/state, respondent, mobile number, email, and uploaded PDF/image (optional).
- **Explicitly NOT Collected:** Aadhaar, PAN, passport, voter ID, biometrics, health records (unless voluntarily typed into free text), tracking cookies, or third-party analytics.
- **Zero-PII Admin Views:** `/admin/complaints` and `/admin/documents` return structural metadata only (reference number, status, timestamps)—never personal narratives or contact fields.

### Logging & Retention
- **HTTP Access Logs:** Record request ID, HTTP method, path, status code, and latency only. Client IP addresses are stored only as truncated SHA-256 hashes when recorded.
- **Query Logs:** Store a **redacted copy** of the question text plus a cryptographic hash—never raw unredacted PII queries.
- **Retention & Purge:** `backend/app/services/retention.py` and `scripts/purge_data.py` enforce a default **180-day** retention period (`NYAYMITRA_PII_RETENTION_DAYS`), purging expired personal data while retaining the non-PII audit trail. *(Note: Not yet tested against real production citizen data.)*

---

## 4. Known Security & Privacy Risks (Unresolved)

| Risk ID | Risk / Gap | Current Mitigation / Required Action |
| :--- | :--- | :--- |
| **SEC-1** | **Shared Static Operator Tokens Without MFA or Per-User RBAC** | Tokens are static env vars; compromised tokens cannot be attributed to an individual operator. Add per-user authentication and MFA before public launch. |
| **SEC-2** | **In-Memory Single-Process Rate Limiter** | Effective only in single-worker deployments. Multi-worker production scaling requires a shared Redis-backed limiter and edge WAF. |
| **SEC-3** | **No Self-Service Data Deletion or Portability Endpoint** | Citizens can download `.txt` summaries in the UI, but automated deletion-on-request and structured export endpoints (relevant to DPDP Act 2023) are not yet built. |
| **SEC-4** | **Backup Retention Overlap** | Deleted citizen records may persist inside historical SQLite backups in `backups/` until backup rotation expires them. |
| **SEC-5** | **No External Secret Manager or TLS Termination in App** | Deployment must place FastAPI behind HTTPS/TLS (Render/Cloudflare/Nginx) and inject secrets via platform secret stores rather than `.env` files on disk. |
| **SEC-6** | **No Independent Penetration Test or Live Browser Audit** | Schedule third-party security review and real-browser CSP/PWA testing prior to Stage C (public release). |
