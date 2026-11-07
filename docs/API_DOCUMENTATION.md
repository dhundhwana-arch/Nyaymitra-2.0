# API documentation

Base path: `/api/v1` (an unlisted `/api` alias also works). Machine-readable schema:
`GET /api/openapi.json`. Swagger UI is intentionally not enabled — it loads assets from a CDN,
which the CSP blocks and which cannot work offline.

Interactive reference for development:

```bash
python -m pip install -r backend/requirements-dev.txt
uvicorn backend.app.main:app --port 8000
curl -s http://127.0.0.1:8000/api/openapi.json | python -m json.tool | less
```

## Conventions

**Error envelope** — every 4xx/5xx JSON response has the same shape:

```json
{"error": {"code": "validation_failed", "message": "The submitted data is invalid.",
           "details": {"fields": [{"field": "description", "message": "String should have at least 20 characters"}]},
           "request_id": "8f3a1c2d9e0b4a71"}}
```

| Code | HTTP | Meaning |
|---|---|---|
| `validation_failed` | 422 | Field validation failed; `details.fields` lists them |
| `bad_request` | 400 | Semantically invalid request |
| `unauthorized` | 401 | Admin token missing or invalid |
| `forbidden` | 403 | Valid token, insufficient role; or admin disabled |
| `not_found` | 404 | Unknown resource (also returned for a wrong complaint token) |
| `conflict` | 409 | Action not allowed in the current state (e.g. verifying without source text) |
| `unsupported_media_type` | 415 | Upload type not allowed or content/type mismatch |
| `payload_too_large` | 413 | Body or file over the limit |
| `length_required` | 411 | Chunked body without `Content-Length` |
| `rate_limited` | 429 | Rate limit exceeded; see `Retry-After` |
| `provider_unavailable` | 503 | AI provider failed and `AI_FALLBACK_MODE=strict` |
| `internal_error` | 500 | Unexpected failure; details are only in the server log |

**Headers** — responses carry `X-Request-ID`, `X-Response-Time-ms` and the security headers
(`Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
`Permissions-Policy`, plus HSTS in production).

**Rate limits** (per IP, fixed window, default 60 s): read 120, write 30, AI 20, admin 10.
`/health` is exempt. Limit `0` blocks the bucket (useful to disable admin entirely).

**Authentication** — citizen endpoints take no login: a complaint is protected by a high-entropy
token shown once and stored only as SHA-256. Admin endpoints take `X-Admin-Token` (or
`Authorization: Bearer …`): the **admin** token may mutate, the **monitor** token is read-only.

---

## Endpoints (31)

### Service

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness: `{status, version, checks}` |
| GET | `/ready` | Readiness: database, migrations, storage, AI provider |
| GET | `/meta` | Capabilities, corpus counts, disclaimers (drives the UI banner) |

### Constitution

| Method | Path | Notes |
|---|---|---|
| GET | `/constitution/articles` | `q`, `language=gu|en`, `part`, `verification_status`, `page`, `page_size` (≤50) |
| GET | `/constitution/articles/{identifier}` | `14`, `39A`, `article-21a`; returns text, explanation, source, disclaimers |
| GET | `/constitution/parts` | Parts with article counts |
| GET | `/constitution/coverage` | Total articles, verified text count, missing standard articles |

```bash
curl -s 'http://127.0.0.1:8000/api/v1/constitution/articles?q=equality&language=en' | python -m json.tool
curl -s 'http://127.0.0.1:8000/api/v1/constitution/articles/14' | python -m json.tool
```

Search response item: `id, article_no, article_label, part_no, title_en, title_gu, snippet,
verification_status, text_status, score`. `text_en`/`text_gu` are `null` when the authoritative
text has not been loaded — that is deliberate, never a paraphrase in the text field.

### AI

| Method | Path | Body |
|---|---|---|
| POST | `/ai/explain` | `{question (5–500), language, category?}` |
| POST | `/ai/terminology` | `{term, language}` |
| GET | `/ai/glossary` | `?language=gu|en` |

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/ai/explain \
  -H 'Content-Type: application/json' \
  -d '{"question":"કાયદા સમક્ષ સમાનતા શું છે?","language":"gu"}' | python -m json.tool
```

Response: `request_id, language, answer, grounded, provider, model, degraded, citations[],
guide{category, steps, documents, department}, departments[], warnings[], disclaimers[],
latency_ms`. `grounded=false` with `warnings:["insufficient_sources"]` means no source matched —
the answer then says so instead of guessing. `warnings` may include `input:*` (prompt-injection
patterns), `model_rejected:*`, `provider_unavailable_fallback`, `no_verified_text`.

### Complaints

| Method | Path | Notes |
|---|---|---|
| POST | `/complaints/preview` | Validates and returns the deterministic summary **without writing** |
| POST | `/complaints` | Requires `confirmed: true`; returns reference + one-time token |
| GET | `/complaints/{reference}?token=…` | Wrong token → generic 404 (no oracle) |

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/complaints/preview \
  -H 'Content-Type: application/json' \
  -d '{"language":"en","category":"cyber_fraud","title":"Money taken from my account",
       "description":"On 5 November 2026 an unknown person withdrew 25000 rupees without any OTP. I told the bank the same day.",
       "incident_date":"2026-11-05","consent":true}'
```

Preview returns `{summary, category, word_count, checks[]}` where `checks` names missing fields
(`missing_location`, `missing_incident_date`, …). The summary is extractive — built from the
citizen's own words — and always states that it is not a legal decision.

### Documents

| Method | Path | Notes |
|---|---|---|
| POST | `/documents` | multipart `file` + `document_kind`; PDF/JPEG/PNG/WebP; ≤10 MB |
| GET | `/documents/{id}?token=…` | Metadata for the owner |
| GET | `/documents/{id}/content?token=…` | Original bytes for the owner |

`extraction_status` is `extracted`, `ocr_unavailable`, `too_large`, `extraction_failed` or
`not_processed`; it is never silently reported as empty text.

### Departments and feedback

| Method | Path | Notes |
|---|---|---|
| GET | `/departments` | `jurisdiction`, `limit`; includes provenance + verification status |
| GET | `/departments/{department_key}` | Single entry |
| POST | `/feedback` | `{target_type: ai_answer|article|department, target_ref, reason, message?}` |

### Administration (token required)

| Method | Path | Role |
|---|---|---|
| GET | `/admin/stats` | monitor |
| GET | `/admin/verification-queue` | monitor |
| GET | `/admin/queries`, `/admin/answers`, `/admin/errors`, `/admin/audit` | monitor |
| GET | `/admin/complaints` | monitor — metadata only, never text |
| GET | `/admin/documents` | monitor — metadata only, never text or file |
| GET | `/admin/sources` | monitor |
| GET | `/admin/legacy-chunks` | monitor — quarantined legacy rows, clearly marked |
| PATCH | `/admin/articles/{id}/verification` | **admin** — requires `checked_by` + `last_checked_at` + source text |
| POST | `/admin/backup` | **admin** — creates and integrity-checks a backup |

```bash
TOKEN=your-admin-token
curl -s http://127.0.0.1:8000/api/v1/admin/verification-queue -H "X-Admin-Token: $TOKEN" | python -m json.tool
curl -s -X POST http://127.0.0.1:8000/api/v1/admin/backup -H "X-Admin-Token: $TOKEN"
```

## Limits and validation worth knowing

| Field | Rule |
|---|---|
| `question` | 5–500 characters |
| complaint `title` | 5–150; `description` 20–5000; `incident_date` not in the future |
| `contact_phone` | Indian mobile/landline format, optional |
| `contact_email` | validated; optional |
| uploads | magic-byte must match declared type; max 10 MB |
| admin token | compared in constant time; 10 requests/min/IP |

## Versioning

`/api/v1` is the only public prefix today. Breaking changes get `/api/v2`; additive fields do not
bump the version. The unlisted `/api` alias exists for earlier front-end builds and will stay until
they are retired.
