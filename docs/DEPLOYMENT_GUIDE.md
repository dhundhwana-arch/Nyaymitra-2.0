# Deployment guide

Two supported shapes: **local evaluation** (laptop, LAN, court help-desk kiosk) and **small
server** (single VM behind a TLS reverse proxy). The application is one Python process, one SQLite
file and one storage directory; it needs no Redis, no message broker and no outbound internet.

> Run **one** worker. Rate limiting is in-process and SQLite writes are serialised; `--workers 2+`
> multiplies the rate limits and increases lock contention.

## 1. Local evaluation

```bash
git clone https://github.com/dhundhwana-arch/Nyaymitra-2.0.git && cd Nyaymitra-2.0
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
python scripts/init_db.py --info
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

`./run.sh [port]` wraps the same steps (and installs dependencies). Windows: `run.bat`.

## 2. Server

### 2.1 Layout and user

```bash
sudo useradd --system --home /opt/nyaymitra --shell /usr/sbin/nologin nyaymitra
sudo mkdir -p /opt/nyaymitra /var/lib/nyaymitra/{documents,backups}
sudo chown -R nyaymitra:nyaymitra /opt/nyaymitra /var/lib/nyaymitra
sudo chmod 750 /var/lib/nyaymitra
```

### 2.2 Environment file

`/etc/nyaymitra.env` (mode `0600`, owner `root`):

```ini
NYAYMITRA_ENV=production
NYAYMITRA_HOST=127.0.0.1
NYAYMITRA_PORT=8000
NYAYMITRA_LOG_LEVEL=INFO
NYAYMITRA_DB_PATH=/var/lib/nyaymitra/nyaymitra.db
NYAYMITRA_STORAGE_DIR=/var/lib/nyaymitra/documents
NYAYMITRA_BACKUP_DIR=/var/lib/nyaymitra/backups
NYAYMITRA_SERVE_WEB=true

# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
NYAYMITRA_ADMIN_TOKEN=__replace_me__
NYAYMITRA_MONITOR_TOKEN=__replace_me_too__

# Keep offline unless you have reviewed the provider and the data-flow implications.
NYAYMITRA_AI_PROVIDER=auto
NYAYMITRA_AI_BASE_URL=
NYAYMITRA_AI_MODEL=
NYAYMITRA_AI_API_KEY=
NYAYMITRA_AI_FALLBACK_MODE=offline_grounded

# Retention window for complaint personal data (decide with the owner before enabling the cron).
NYAYMITRA_PII_RETENTION_DAYS=180
# A repeated identical complaint without a client id inside this window is treated as a retry.
NYAYMITRA_DUPLICATE_WINDOW_S=600

# Per IP per minute. 0 blocks the bucket (and disables the admin API).
NYAYMITRA_RATE_LIMIT_READ=120
NYAYMITRA_RATE_LIMIT_WRITE=30
NYAYMITRA_RATE_LIMIT_AI=20
NYAYMITRA_RATE_LIMIT_ADMIN=10
NYAYMITRA_MAX_UPLOAD_BYTES=10485760
NYAYMITRA_PII_RETENTION_DAYS=180
NYAYMITRA_TRUST_PROXY_HEADERS=true
```

`TRUST_PROXY_HEADERS=true` **only** when a reverse proxy you control sets `X-Forwarded-For`;
otherwise every request looks like the proxy and shares one rate-limit bucket.

Full variable reference: `.env.example` (every variable has a working default).

### 2.3 systemd unit

`/etc/systemd/system/nyaymitra.service`:

```ini
[Unit]
Description=NYAYMITRA 2.0
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=nyaymitra
Group=nyaymitra
WorkingDirectory=/opt/nyaymitra
EnvironmentFile=/etc/nyaymitra.env
ExecStartPre=/opt/nyaymitra/.venv/bin/python scripts/init_db.py --no-seed
ExecStart=/opt/nyaymitra/.venv/bin/python -m uvicorn backend.app.main:app \
          --host 127.0.0.1 --port 8000 --workers 1 --no-server-header
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/nyaymitra
UMask=0077

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now nyaymitra
curl -fsS http://127.0.0.1:8000/api/v1/ready
```

### 2.4 Reverse proxy (nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name nyaymitra.example.org;

    ssl_certificate     /etc/letsencrypt/live/nyaymitra.example.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/nyaymitra.example.org/privkey.pem;

    # Must be >= the app upload limit, or nginx rejects first with an HTML error.
    client_max_body_size 12m;

    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy no-referrer always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
    }
}
server {
    listen 80;
    server_name nyaymitra.example.org;
    return 301 https://$host$request_uri;
}
```

The application sends its own CSP and security headers; do not duplicate them at the proxy unless
you are sure the stricter copy wins.

## 3. Data: backup, restore, upgrade

```bash
# backup (verified, 0600) — run daily from cron
/opt/nyaymitra/.venv/bin/python /opt/nyaymitra/scripts/backup_db.py
# /etc/cron.d/nyaymitra:  15 2 * * *  nyaymitra  ...backup_db.py

# list / restore
python scripts/backup_db.py --list
python scripts/backup_db.py --restore backups/nyaymitra-20261107T020000Z.db
```

Copy backups **off the machine** (they contain personal data — encrypt the destination).

Upgrade:

```bash
sudo systemctl stop nyaymitra
sudo -u nyaymitra python scripts/backup_db.py          # verified backup first
git pull --ff-only
sudo -u nyaymitra .venv/bin/pip install -r backend/requirements.txt
sudo -u nyaymitra .venv/bin/python scripts/init_db.py --migrate
sudo systemctl start nyaymitra && curl -fsS http://127.0.0.1:8000/api/v1/ready
```

Rollback:

```bash
sudo systemctl stop nyaymitra
python scripts/init_db.py --rollback-to <n>        # schema only
# or restore the file: python scripts/backup_db.py --restore <backup>
sudo systemctl start nyaymitra
```

## 4. Verification after deploy

```bash
curl -fsS http://127.0.0.1:8000/api/v1/health         # {"status":"ok"}
curl -fsS http://127.0.0.1:8000/api/v1/ready | python -m json.tool
curl -fsSI https://nyaymitra.example.org/ | grep -i content-security-policy
curl -s -o /dev/null -w '%{http_code}\n' https://nyaymitra.example.org/api/v1/admin/stats   # 401/403
stat -c '%a %n' /var/lib/nyaymitra/nyaymitra.db /var/lib/nyaymitra/documents            # 600 / 700
```

Checklist before announcing a URL:

- [ ] `NYAYMITRA_ENV=production`, HTTPS working, HSTS present
- [ ] Admin and monitor tokens are random, different, and stored outside the repository
- [ ] `/admin` reachable only by the operator (proxy/VPN allow-list if possible)
- [ ] Backup run + restore rehearsed on a copy
- [ ] Official Constitution documents ingested and reviewed — otherwise the banner will (correctly)
      tell every citizen that the text is not loaded
- [ ] Retention decision recorded; purge cron installed (`python scripts/purge_data.py` dry run
      reviewed first)
- [ ] `pip-audit --vulnerability-service pypi -r backend/requirements.txt` clean
- [ ] `/api/v1/admin/metrics` scrapeable by the operator's monitoring
- [ ] `docs/SECURITY_AUDIT.md` §6 checklist completed

## 4.1 Migrations, retention and monitoring

**Migrations.** Startup applies pending migrations automatically (recorded in `schema_migrations`).
Three ship today:

| Migration | Effect | Rollback |
|---|---|---|
| `001_initial` | Base schema, FTS5 triggers | `001_initial.down.sql` |
| `002_complaint_idempotency` | `client_request_id`, `fingerprint`, partial unique index | `002_complaint_idempotency.down.sql` |
| `003_article_source_pages` | `constitution_articles.source_pages` | `003_article_source_pages.down.sql` |

On an upgrade: take a backup first (`python scripts/backup_db.py --label pre-upgrade`), then
`python scripts/init_db.py --info` to see what will be applied. Rolling back schema changes is a
manual step (`sqlite3 db < migrations/00X_*.down.sql` with the app stopped) — this is why the
backup comes first. Rolling back a *deployment* (old code, new schema) is safe for 002/003 because
both migrations are additive.

**Retention cron.** After the owner decides the window:

```cron
# 03:15 daily: delete personal data older than the retention window, then audit it
15 3 * * * cd /opt/nyaymitra && /opt/nyaymitra/.venv/bin/python scripts/purge_data.py --apply             >> /var/log/nyaymitra-purge.log 2>&1
```

Run it once without `--apply` first and read the JSON: it reports how many complaints, documents,
query logs and files would be removed. The purge keeps the audit trail, keeps `error_log`, keeps
`ingest_runs`, and cannot delete a file outside `NYAYMITRA_STORAGE_DIR`.

**Monitoring.** `GET /api/v1/admin/metrics` (monitor token) returns in-process counters:

```json
{"uptime_s": 1284, "counters": {"http.requests_total": 412, "http.status_2xx": 401,
 "http.status_4xx": 11, "http.rate_limited_total": 3, "ai.insufficient_sources_total": 7,
 "ai.model_rejected_total": 1, "ai.provider_fallback_total": 2}}
```

Suggested alerts: `http.status_5xx > 0`, `http.rate_limited_total` climbing (someone is hammering
the API), `ai.provider_fallback_total` climbing (the provider is failing), and uptime resets
(a crash loop). `/health` is liveness, `/ready` is dependency readiness — point the uptime check at
`/ready`. Note these counters are per worker: run one worker (see `KNOWN_LIMITATIONS.md` #19).

**AI provider probe.** Before telling anyone the assistant "uses AI", prove it:

```bash
NYAYMITRA_AI_PROVIDER=openai_compatible \
NYAYMITRA_AI_BASE_URL=http://127.0.0.1:11434/v1 \
NYAYMITRA_AI_MODEL=llama3.2:3b \
NYAYMITRA_AI_API_KEY=ollama \
python scripts/verify_ai_provider.py --question "What does equality before the law mean?"
```

Exit 0 means a real model produced a grounded, cited answer; exit 3 means no model is reachable
(the script prints the requirement); exit 4 means the model answered but the guard rejected the
output as uncited or unsafe. Never treat a 3 or a 4 as a pass.

**Handover integrity.** `python scripts/verify_changeset.py --write|--verify|--verify-archive`
proves that a deployed copy matches the manifest of the tested commit. Run `--verify` after any
transfer and before a release tag.

**Dependency audit.** Before every deploy:

```bash
pip-audit --vulnerability-service pypi -r backend/requirements.txt
```

CI runs the same command; the last local run was clean.

## 5. Optional Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY . .
RUN useradd -r -u 10001 nyaymitra && mkdir -p /data && chown nyaymitra /data
USER nyaymitra
ENV NYAYMITRA_DB_PATH=/data/nyaymitra.db NYAYMITRA_STORAGE_DIR=/data/documents
EXPOSE 8000
CMD ["uvicorn","backend.app.main:app","--host","0.0.0.0","--port","8000","--workers","1"]
```

Mount `/data` as a volume and back it up. Do not run multiple replicas against one SQLite file.

## 6. Capacity

A single small VM (1 vCPU, 1 GB RAM) is sufficient for a help-desk workload: SQLite FTS5 answers
searches in milliseconds at this corpus size, and the offline AI path is CPU-light. The limits are
concurrent uploads (bounded) and PDF extraction (5 pages). Measure before scaling; if you need
multiple processes, move rate limiting to Redis and the database to PostgreSQL first.
