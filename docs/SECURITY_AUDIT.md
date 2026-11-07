# Security audit

Scope: the application in this branch (`backend/`, `web/`, `scripts/`), its data handling and the
deployment defaults it ships with. Date: 2026-11-07. Reviewed by: automated analysis plus manual
code review; **no third-party penetration test has been performed**.

## 1. Threat model

| Actor | Capability | What they want |
|---|---|---|
| Anonymous internet user | Any request | Scrape the corpus; abuse the AI endpoint; find another citizen's complaint |
| Malicious uploader | Arbitrary file bytes | Path traversal, stored payload served back, parser exploit, storage exhaustion |
| Curious operator | Admin/monitor token | Read complaint text or document contents |
| Attacker with a leaked token | One admin token | Escalate to verification changes, backups |
| Model output | Unbounded text | Fabricated law, a verdict, prompt-injection persistence |

Non-goals: defending a shared host from a root-level attacker, nation-state traffic analysis, or
guaranteeing availability under DDoS (see residual risk R-6).

## 2. Controls in place

| Area | Control |
|---|---|
| Transport | HTTPS expected at the reverse proxy; HSTS sent when `NYAYMITRA_ENV=production` |
| Headers | CSP `default-src 'self'` with no `unsafe-inline`/`unsafe-eval`; `frame-ancestors 'none'`; `nosniff`; `no-referrer`; `Permissions-Policy` (only microphone for self) |
| AuthN | Admin/monitor tokens from environment, compared with `hmac.compare_digest`; citizen data protected by 192-bit access tokens |
| AuthZ | `require_role("monitor"|"admin")` dependency on every admin route; admin disabled entirely when no token is configured |
| Secrets at rest | Access tokens stored **only** as SHA-256; admin tokens are never written to the database or logs |
| SQL | Every statement parameterised; the only dynamic SQL is column selection from fixed literals; FTS queries are built from tokenised input with quoted phrases |
| Uploads | Extension-independent magic-byte sniffing, declared/actual type must match, size cap, random storage name, `0600` file mode, no path from user input, extraction bounded to 5 pages / 20 k chars / 8 MB |
| Path traversal | `Path(...).name` + NFKC normalisation + control-char stripping; resolved target must stay inside `storage_dir` |
| PII in logs | `logging_utils.redact()` masks phone numbers, e-mails, Aadhaar-like numbers, tokens and `Bearer` values; query text is redacted before it reaches `query_logs` |
| Admin index data | Complaint and document admin endpoints return metadata only — no description, no extracted text, no contact details |
| Abuse limits | Per-IP fixed-window buckets: read 120, write 30, AI 20, admin 10 per minute; body and upload size caps; chunked bodies refused (411) because they cannot be size-checked |
| Error disclosure | Uniform envelope; internal exception text only in `error_log`; `request_id` for correlation |
| XSS | All dynamic text is set via `textContent` or an escaping helper; no raw HTML interpolation; CSP blocks inline script |
| CSRF | No cookie-based authentication, so no ambient credentials to forge; admin token must be sent explicitly |
| Clipboard/session | Admin token kept in `sessionStorage` for the tab only; the citizen token is displayed once and not persisted |
| Filesystem | Database `0600`, database directory `0700`, uploaded files `0600`, storage directory `0700` |
| Dependencies | Fully pinned (`requirements.txt`); no CDN, no runtime JS dependency at all |

## 3. Findings fixed in this round

| ID | Severity | Finding | Fix |
|---|---|---|---|
| S-20 | High (availability) | `/admin` was served but `/admin.js` returned 404, so the console was dead in the browser while all unit tests passed | Registered the asset route; added a test that fetches every asset referenced by both pages |
| S-21 | High | CSP allowed `'unsafe-inline'` styles | Removed the allowance and replaced the three inline `style` attributes with `.field-grow` / `.field-flush` classes; test asserts both |
| S-22 | High | Admin endpoints shared the 120/min read bucket — a token could be brute-forced at that rate | Dedicated `admin` bucket (default 10/min, configurable, `0` disables admin); test asserts 429 |
| S-23 | Medium | Size limit trusted `Content-Length`; a chunked body could be buffered without limit | Chunked bodies on mutating methods are now refused with 411 `length_required`; upload route still caps the read at `max_upload_bytes + 1` |
| S-24 | Medium | Database, storage and backup files were created with default (0644) permissions | `harden_permissions()` forces `0600`/`0700`; test asserts the modes |
| S-25 | Medium | `/api/docs` pointed at Swagger UI assets loaded from a CDN, which the CSP blocks and which leaks a request to a third party | Swagger UI disabled; schema remains at `/api/openapi.json` |

## 4. Findings fixed earlier in this branch

| ID | Severity | Finding | Fix |
|---|---|---|---|
| S-1 | Critical (legal) | Every legacy row carried a fabricated “Constitutional Provision & Statutory Guidelines” remedy string, presented as law | Corpus quarantined to `legacy_import_chunks`; a regression test proves it is unreachable through the API |
| S-2 | High | Access tokens stored recoverably next to the data | SHA-256 only; one-time display |
| S-3 | High | No validation of uploaded content; the legacy UI accepted any file | Magic-byte + declared-type + size checks, random names, owner tokens |
| S-4 | High | No rate limiting or size limits anywhere | Buckets and body caps as above |
| S-5 | High | User text could reach the model unfenced, allowing prompt injection to shape legal answers | Sources fenced with `<<SOURCE … >>`, injection patterns flagged, answers validated against retrieved citations |
| S-6 | Medium | Internal error text returned to clients | Uniform envelope + server-side log only |
| S-7 | Medium | PII in query logs | Redaction before write, hash for correlation |
| S-8 | Medium | Admin could mark content verified without a reviewer or source text | `checked_by` + `last_checked_at` + `text_status == verified_source_text` required; audit entry written |

## 5. Residual risk (accepted, documented)

| ID | Risk | Why it remains | Mitigation / next step |
|---|---|---|---|
| R-1 | Rate limiting is per process and in memory; multiple workers multiply limits | Single-process deployment target | Use Redis or a proxy limiter when scaling out; run **one** worker |
| R-2 | No encryption at rest | SQLite + local disk; key management not in scope | Full-disk/volume encryption at the host; restrict filesystem access |
| R-3 | PII retention purge is not automated | `NYAYMITRA_PII_RETENTION_DAYS` exists but no job uses it | Add a scheduled purge before any public deployment (see `KNOWN_LIMITATIONS.md`) |
| R-4 | No malware scanning of uploads | No engine available offline | ClamAV integration if uploads are ever shared between users |
| R-5 | PDF parsing runs in-process | Bounded (5 pages, 8 MB) but a hostile PDF still consumes CPU briefly | Run extraction in a worker with a timeout if uploads become public |
| R-6 | No DDoS protection, no WAF | Application-level only | Put a CDN/WAF or reverse-proxy limiter in front for public use |
| R-7 | Single shared admin token, no individual accounts, no MFA | Deliberate simplicity for a small operator | Add per-user accounts with TOTP before delegating access widely |
| R-8 | No dependency scanning in CI | Only pinned versions | Enable Dependabot/`pip-audit` (network-dependent) |
| R-9 | Voice features use browser APIs with no privacy notice | Speech recognition may be cloud-backed in some browsers | Add a privacy note where voice is offered; text input always remains |

## 6. Verification checklist for an operator

```bash
# headers
curl -sI https://your-host/ | grep -iE 'content-security-policy|strict-transport|referrer|x-content'
# admin is off unless configured
curl -s -o /dev/null -w '%{http_code}\n' https://your-host/api/v1/admin/stats        # 401/403
# files are not world-readable
stat -c '%a %n' data/nyaymitra.db storage/documents backups/*.db
# no secrets in the repository
git grep -nE 'sk-|AIza|ghp_|xoxb-' || echo clean
```

## 7. Disclosure

Report a vulnerability privately to the repository owner rather than opening a public issue.
Include the request id from the response (or the `X-Request-ID` header) where possible.
