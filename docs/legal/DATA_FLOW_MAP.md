# DATA_FLOW_MAP.md

NYAYMITRA 2.0 — Data flow map
==============================

## Status

**Self-assessed.** Reflects the implemented flows. Not a legal document.

## Actors

* Citizen — uses the UI (web browser).
* NYAYMITRA service — FastAPI backend, SQLite database, filesystem document store.
* Admin / monitor — operates the admin console with a token.
* AI provider — optional local endpoint (OpenAI-compatible / Ollama); not configured by
  default.

## Flows

### 1. AI question → answer (no personal data required)

```
Citizen types a question
        │
        ▼
Frontend (web/app.js) ──POST /ai/explain──▶ Backend
        │                                         │
        │                                RAG: triage match + article retrieval
        │                                         │
        │                                Provider: offline (default) or local endpoint
        │                                         │  (only question + sources sent; never contact data)
        │                                         ▼
        │                         Answer + citations + warnings + disclaimers
        │                                         │
        ◀─────────────────────────────────────────┘
        │
        ▼
Frontend renders answer; optional speech synthesis (client-side); optional feedback report
```

Data stored: redacted question text + hash in `query_logs`; answer metadata + citations +
token usage in `ai_answers`. No contact details, no complaint text.

### 2. Complaint draft → saved (personal data)

```
Citizen fills complaint form (category, title, description, optional location/contact/documents)
        │
        ▼
Preview: POST /complaints/preview (nothing written to DB)
        │
        Citizen reviews + checks consent
        │
        ▼
POST /complaints (client_request_id for idempotency)
        │
        ▼
Backend: creates complaint row (reference, access_token_hash, redacted fields),
         stores uploaded documents under random names in storage_dir
        │
        ▼
Citizen receives reference + access token (shown once)
        │
        ◀── Download draft as .txt (client-side blob)
```

Data stored: `complaints` (reference, token hash, category, title, description, location,
district, state, respondent, phone, email, consent, status), `documents` (metadata +
stored file), `audit_log` (admin actions only).

### 3. Re-open a saved complaint

```
Citizen supplies reference + token
        │
        ▼
GET /complaints/{reference}?token={token}
        │
        Backend: constant-time token comparison; wrong token → "not found" (no oracle)
        │
        ◀── Metadata + summary (not full description / contact details by default design)
```

### 4. Document download

```
Citizen supplies document id + owner token
        │
        ▼
GET /documents/{id}/content?token={token}
        │
        Path resolved under storage_dir only (no traversal)
        │
        ◀── FileResponse with nosniff + no-store
```

### 5. Admin operations

```
Admin supplies token → GET /admin/{stats,queries,answers,errors,audit,complaints,documents,...}
        │
        All responses metadata-only; complaint text and contact details not exposed
        │
        POST /admin/backup → integrity-checked DB copy outside the checkout
```

## Data at rest

| Store | Contents | Protection |
|-------|----------|------------|
| SQLite DB | complaints, documents metadata, query logs (redacted), ai_answers, audit_log, articles, departments, triage, glossary, legacy chunks (quarantined) | File permissions; backup integrity-checked |
| Documents dir | Uploaded PDFs/images (random names) | File permissions; operator to encrypt at rest |
| Logs (stdout) | request ID, method, path, status, latency | No personal data |

## Data in transit

* Browser ↔ service: operator must terminate TLS (reverse proxy / platform); not implemented in-app.
* Service ↔ AI provider: only when configured; question + sources only.

## Third parties

* None at runtime. No analytics, no trackers, no external API calls by default.

## Retention and deletion

* Default retention 180 days (`NYAYMITRA_PII_RETENTION_DAYS`).
* `scripts/purge_data.py` (dry-run default) deletes old complaints/documents/query logs;
  audit trail retained.
* No self-service deletion endpoint yet.
