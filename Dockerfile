# NYAYMITRA 2.0 — single-process container (SQLite + in-process rate limiting).
# Two workers against one SQLite file would split the rate limiter and increase write
# contention, so the container is deliberately single-process. See docs/DEPLOYMENT_GUIDE.md.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NYAYMITRA_ENV=production \
    NYAYMITRA_HOST=0.0.0.0 \
    NYAYMITRA_PORT=8000 \
    NYAYMITRA_DB_PATH=/data/nyaymitra.db \
    NYAYMITRA_STORAGE_DIR=/data/documents \
    NYAYMITRA_BACKUP_DIR=/data/backups

WORKDIR /app

# Dependencies first so an application edit does not invalidate the wheel layer.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY web web
COPY scripts scripts
COPY data/seed data/seed

RUN useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin nyaymitra \
    && mkdir -p /data/documents /data/backups \
    && chown -R nyaymitra:nyaymitra /data /app

USER nyaymitra
EXPOSE 8000

# Container-level health check hits the readiness probe, which checks the database,
# migrations and storage rather than just "the process is up".
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import json,urllib.request,sys; \
r=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/ready', timeout=4)); \
sys.exit(0 if r.get('ready') else 1)"

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers"]
