"""Document upload: type/size validation, safe storage, ownership tokens."""
from __future__ import annotations

import io

import pytest

from .conftest import complaint_payload


def make_pdf(text: str = "Complaint evidence document for testing.") -> bytes:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def upload(client, content: bytes, name: str, mime: str, token: str | None = None):
    return client.post(
        "/api/v1/documents",
        files={"file": (name, content, mime)},
        data={"document_kind": "evidence"},
    )


def test_upload_pdf_is_accepted(client):
    response = upload(client, make_pdf(), "statement.pdf", "application/pdf")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["mime_type"] == "application/pdf"
    assert body["sha256"]
    assert body["extraction_status"] in {"extracted", "ocr_unavailable", "too_large", "extraction_failed"}
    assert body["access_token"]
    assert body["created_at"], "the upload response must carry the real timestamp"


def test_upload_requires_matching_content_type(client):
    response = upload(client, b"just plain text, not a pdf", "notes.pdf", "application/pdf")
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"


def test_upload_rejects_disallowed_type(client):
    response = upload(client, b"#!/bin/sh\necho hi", "script.sh", "application/x-sh")
    assert response.status_code == 415


def test_upload_rejects_empty_file(client):
    response = upload(client, b"", "empty.pdf", "application/pdf")
    assert response.status_code in {400, 413, 415}


def test_upload_enforces_size_limit(client, monkeypatch):
    from backend.app.config import reset_settings_cache, get_settings
    import os

    monkeypatch.setenv("NYAYMITRA_MAX_UPLOAD_BYTES", "1024")
    reset_settings_cache()
    try:
        from fastapi.testclient import TestClient
        from backend.app.main import create_app

        with TestClient(create_app(get_settings())) as small_client:
            big = b"%PDF-1.4\n" + b"A" * 4096
            response = small_client.post(
                "/api/v1/documents",
                files={"file": ("big.pdf", big, "application/pdf")},
            )
            assert response.status_code == 413
            assert response.json()["error"]["code"] == "payload_too_large"
    finally:
        monkeypatch.delenv("NYAYMITRA_MAX_UPLOAD_BYTES", raising=False)
        reset_settings_cache()


def test_uploaded_filename_is_sanitised(client, db):
    response = upload(client, make_pdf(), "../../etc/passwd.pdf", "application/pdf")
    assert response.status_code == 201
    body = response.json()
    assert ".." not in body["original_name"] and "/" not in body["original_name"]
    row = db.execute("SELECT stored_name FROM documents ORDER BY id DESC LIMIT 1").fetchone()
    assert row["stored_name"].endswith(".pdf")
    assert "passwd" not in row["stored_name"]


def test_download_requires_owner_token(client):
    created = upload(client, make_pdf(), "evidence.pdf", "application/pdf").json()
    assert client.get(f"/api/v1/documents/{created['id']}/content").status_code == 422
    assert (
        client.get(f"/api/v1/documents/{created['id']}/content", params={"token": "bad-token-value"})
        .status_code
        == 404
    )
    good = client.get(
        f"/api/v1/documents/{created['id']}/content", params={"token": created["access_token"]}
    )
    assert good.status_code == 200
    assert good.headers["content-type"].startswith("application/pdf")


def test_document_can_be_attached_to_a_complaint(client):
    created = upload(client, make_pdf(), "evidence.pdf", "application/pdf").json()
    payload = complaint_payload()
    payload["documents"] = [{"id": created["id"], "token": created["access_token"]}]
    complaint = client.post("/api/v1/complaints", json=payload)
    assert complaint.status_code == 201
    fetched = client.get(
        f"/api/v1/complaints/{complaint.json()['reference']}",
        params={"token": complaint.json()["access_token"]},
    ).json()
    assert fetched["documents"] and fetched["documents"][0]["id"] == created["id"]


def test_attaching_with_wrong_document_token_does_not_link(client):
    created = upload(client, make_pdf(), "evidence.pdf", "application/pdf").json()
    payload = complaint_payload()
    payload["documents"] = [{"id": created["id"], "token": "y" * 32}]
    complaint = client.post("/api/v1/complaints", json=payload).json()
    fetched = client.get(
        f"/api/v1/complaints/{complaint['reference']}", params={"token": complaint["access_token"]}
    ).json()
    assert fetched["documents"] == []


def test_image_upload_reports_ocr_unavailable(client):
    png = bytes.fromhex("89504e470d0a1a0a") + b"\x00" * 64
    response = upload(client, png, "scan.png", "image/png")
    assert response.status_code == 201
    assert response.json()["extraction_status"] == "ocr_unavailable"
