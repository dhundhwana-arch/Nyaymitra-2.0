"""Admin roles, audit trail, backups, rate limits, headers, redaction."""
from __future__ import annotations

import sqlite3

import pytest

from backend.app.logging_utils import redact, redact_and_truncate
from backend.app.security import hash_token, sanitize_original_name, sniff_mime, validate_upload
from backend.app.config import get_settings


def test_admin_requires_token(client):
    response = client.get("/api/v1/admin/stats")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_admin_rejects_wrong_token(client):
    assert client.get("/api/v1/admin/stats", headers={"X-Admin-Token": "nope"}).status_code == 401


def test_monitor_can_read(client, monitor_headers):
    assert client.get("/api/v1/admin/stats", headers=monitor_headers).status_code == 200
    assert client.get("/api/v1/admin/sources", headers=monitor_headers).status_code == 200


def test_monitor_cannot_mutate(client, monitor_headers):
    response = client.patch(
        "/api/v1/admin/articles/1/verification",
        headers=monitor_headers,
        json={"verification_status": "verified", "checked_by": "someone"},
    )
    assert response.status_code == 403


def test_admin_cannot_verify_without_reviewer_and_date(client, admin_headers, db):
    article_id = db.execute("SELECT id FROM constitution_articles WHERE article_no='14'").fetchone()["id"]
    response = client.patch(
        f"/api/v1/admin/articles/{article_id}/verification",
        headers=admin_headers,
        json={"verification_status": "verified"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_admin_cannot_verify_article_without_source_text(client, admin_headers, db):
    """An article whose authoritative text is missing must not be marked verified."""
    article_id = db.execute("SELECT id FROM constitution_articles WHERE article_no='21'").fetchone()["id"]
    response = client.patch(
        f"/api/v1/admin/articles/{article_id}/verification",
        headers=admin_headers,
        json={
            "verification_status": "verified",
            "checked_by": "Adv. Test Reviewer",
            "last_checked_at": "2026-11-07T10:00:00+00:00",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_admin_verification_update_is_audited(client, admin_headers, db):
    article_id = db.execute("SELECT id FROM constitution_articles WHERE article_no='19'").fetchone()["id"]
    response = client.patch(
        f"/api/v1/admin/articles/{article_id}/verification",
        headers=admin_headers,
        json={
            "verification_status": "unverified",
            "checked_by": "Adv. Test Reviewer",
            "notes": "Needs re-check against the official PDF",
        },
    )
    assert response.status_code == 200
    entry = db.execute(
        "SELECT * FROM audit_log WHERE action = 'article.verification_update' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert entry["actor"] == "admin"
    assert entry["target"] == str(article_id)


def test_admin_backup_creates_verified_file(client, admin_headers, settings):
    response = client.post("/api/v1/admin/backup", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["verified"] is True
    assert (settings.backup_dir / body["file"]).exists()


def test_local_legacy_chunks_are_admin_only_and_quarantined(client, admin_headers):
    assert client.get("/api/v1/admin/legacy-chunks").status_code == 401
    body = client.get("/api/v1/admin/legacy-chunks", headers=admin_headers).json()
    assert body["total"] == 2125, "every legacy row must be preserved"
    assert "NOT articles" in body["note"]


def test_verification_queue_lists_unchecked_content(client, admin_headers):
    body = client.get("/api/v1/admin/verification-queue", headers=admin_headers).json()
    assert body["articles"]
    assert body["departments"]
    assert all(a["verification_status"] != "verified" for a in body["articles"])


def test_error_log_is_written_and_details_do_not_leak(app, db, monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app.routers import constitution as constitution_router

    def boom(*args, **kwargs):
        raise sqlite3.OperationalError("simulated database failure")

    monkeypatch.setattr(constitution_router.constitution, "parts", boom)
    with TestClient(app, raise_server_exceptions=False) as tolerant:
        response = tolerant.get("/api/v1/constitution/parts")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "simulated" not in response.text, "internal details must not leak"
    row = db.execute("SELECT message FROM error_log ORDER BY id DESC LIMIT 1").fetchone()
    assert row is not None
    assert "simulated database failure" in (row["message"] or "")


def test_unknown_api_path_returns_json_envelope(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.headers["content-type"].startswith("application/json")


def test_rate_limit_returns_429(client, monkeypatch):
    from backend.app.config import reset_settings_cache, get_settings
    from fastapi.testclient import TestClient
    from backend.app.main import create_app

    monkeypatch.setenv("NYAYMITRA_RATE_LIMIT_READ", "3")
    reset_settings_cache()
    try:
        with TestClient(create_app(get_settings())) as limited:
            statuses = [limited.get("/api/v1/meta").status_code for _ in range(6)]
            assert 429 in statuses
            blocked = limited.get("/api/v1/meta")
            assert blocked.headers.get("retry-after")
    finally:
        monkeypatch.delenv("NYAYMITRA_RATE_LIMIT_READ", raising=False)
        reset_settings_cache()


def test_request_id_header_is_echoed(client):
    response = client.get("/api/v1/health", headers={"X-Request-ID": "abc123"})
    assert response.headers["x-request-id"] == "abc123"


def test_body_size_limit(client, monkeypatch):
    from backend.app.config import reset_settings_cache, get_settings
    from fastapi.testclient import TestClient
    from backend.app.main import create_app

    monkeypatch.setenv("NYAYMITRA_MAX_BODY_BYTES", "2048")
    reset_settings_cache()
    try:
        with TestClient(create_app(get_settings())) as small:
            response = small.post(
                "/api/v1/ai/explain",
                json={"question": "a" * 5000, "language": "en"},
            )
            assert response.status_code == 413
    finally:
        monkeypatch.delenv("NYAYMITRA_MAX_BODY_BYTES", raising=False)
        reset_settings_cache()


def test_redaction_removes_pii_and_secrets():
    text = "call 9876543210 or mail a@b.com with token=abc123 and Bearer xyz.987"
    cleaned = redact(text)
    assert "9876543210" not in cleaned
    assert "a@b.com" not in cleaned
    assert "abc123" not in cleaned
    assert "xyz.987" not in cleaned
    assert len(redact_and_truncate("x" * 1000)) == 301


def test_token_hashing_and_filename_sanitising():
    assert hash_token("abc") == hash_token("abc")
    assert hash_token("abc") != hash_token("abd")
    assert sanitize_original_name("../../etc/passwd") == "passwd"
    assert sanitize_original_name("C:\\windows\\system32\\x.pdf") == "x.pdf"
    assert sanitize_original_name(None) == "unnamed"
    assert sniff_mime(b"%PDF-1.7 ...") == "application/pdf"
    assert sniff_mime(b"GIF89a") is None


def test_upload_validation_rejects_type_mismatch():
    settings = get_settings()
    check = validate_upload(
        original_name="a.pdf", declared_mime="application/pdf", size=10,
        head=b"\x89PNG\r\n\x1a\n", settings=settings,
    )
    assert check.ok is False


def test_security_headers_on_api_responses(client):
    response = client.get("/api/v1/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_no_secret_is_hardcoded_in_tracked_source():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    suspicious = []
    for path in list(root.glob("backend/app/**/*.py")) + list(root.glob("scripts/*.py")):
        text = path.read_text(encoding="utf-8")
        for marker in ("sk-", "AIza", "ghp_", "xoxb-"):
            if marker in text:
                suspicious.append((path.name, marker))
    assert suspicious == []
