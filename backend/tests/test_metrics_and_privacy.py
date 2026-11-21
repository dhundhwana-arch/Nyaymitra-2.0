"""Operational metrics, cache-control on personal data, and download hardening."""
from __future__ import annotations

import io

from backend.app.metrics import metrics

from .conftest import complaint_payload


def test_metrics_endpoint_requires_a_token(client):
    assert client.get("/api/v1/admin/metrics").status_code == 401
    assert client.get("/api/v1/admin/metrics", headers={"X-Admin-Token": "wrong"}).status_code == 401


def test_metrics_counts_requests_and_ai_outcomes(client, monitor_headers):
    metrics.reset()
    client.get("/api/v1/health")
    client.get("/api/v1/meta")
    answer = client.post("/api/v1/ai/explain", json={"question": "zzzz qqqq", "language": "en"}).json()
    assert answer["grounded"] is False

    body = client.get("/api/v1/admin/metrics", headers=monitor_headers).json()
    assert body["uptime_s"] >= 0
    assert body["http"]["requests_total"] >= 3
    assert body["http"].get("status_2xx", 0) >= 3
    assert body["ai"].get("insufficient_sources_total", 0) >= 1
    serialised = str(body)
    assert "zzzz" not in serialised and "127.0.0.1" not in serialised


def test_sensitive_responses_are_not_cacheable(client):
    complaint = client.post("/api/v1/complaints", json=complaint_payload()).json()
    responses = [
        client.get(f"/api/v1/complaints/{complaint['reference']}", params={"token": complaint["access_token"]}),
        client.get("/api/v1/admin/stats", headers={"X-Admin-Token": "test-admin-token"}),
        client.get("/admin"),
    ]
    for response in responses:
        assert response.headers.get("cache-control") == "no-store", response.request.url
        assert response.headers.get("pragma") == "no-cache"


def test_public_assets_remain_cacheable(client):
    """The no-store rule must not fall over the whole site (bandwidth matters)."""
    assert client.get("/").headers.get("cache-control") is None
    assert client.get("/styles.css").headers.get("cache-control") is None


def test_document_download_is_an_attachment_and_not_cacheable(client):
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=80, height=80)
    buffer = io.BytesIO()
    writer.write(buffer)
    created = client.post(
        "/api/v1/documents",
        files={"file": ("evidence.pdf", buffer.getvalue(), "application/pdf")},
    ).json()
    response = client.get(
        f"/api/v1/documents/{created['id']}/content", params={"token": created["access_token"]}
    )
    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith("attachment")
    assert response.headers["cache-control"] == "no-store"


def test_the_api_never_sets_cookies(client):
    """No cookie authentication means no ambient credentials and no CSRF surface."""
    responses = [
        client.get("/"),
        client.get("/api/v1/meta"),
        client.post("/api/v1/ai/explain", json={"question": "equality before law", "language": "en"}),
        client.get("/api/v1/admin/stats", headers={"X-Admin-Token": "test-admin-token"}),
    ]
    for response in responses:
        assert "set-cookie" not in response.headers, response.request.url


def test_no_cors_headers_are_advertised(client):
    """The app is same-origin; a permissive CORS header would widen the attack surface."""
    response = client.get("/api/v1/meta", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers
