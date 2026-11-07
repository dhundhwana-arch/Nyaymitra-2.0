"""Complaint intake: validation, deterministic summary, token-gated retrieval."""
from __future__ import annotations

from .conftest import complaint_payload


def test_create_and_retrieve_complaint(client):
    created = client.post("/api/v1/complaints", json=complaint_payload())
    assert created.status_code == 201
    body = created.json()
    assert body["reference"].startswith("NYM-")
    assert len(body["access_token"]) >= 20
    assert body["next_steps"], "a complaint must be returned with navigation steps"
    assert body["departments"]

    fetched = client.get(
        f"/api/v1/complaints/{body['reference']}", params={"token": body["access_token"]}
    )
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "submitted"
    assert fetched.json()["description"] == complaint_payload()["description"]


def test_wrong_token_is_indistinguishable_from_missing(client):
    created = client.post("/api/v1/complaints", json=complaint_payload()).json()
    wrong = client.get(f"/api/v1/complaints/{created['reference']}", params={"token": "x" * 32})
    missing = client.get("/api/v1/complaints/NYM-NOPE00", params={"token": "x" * 32})
    assert wrong.status_code == missing.status_code == 404
    assert wrong.json() == missing.json() or wrong.json()["error"]["code"] == missing.json()["error"]["code"]


def test_access_token_is_not_stored_in_plaintext(client, db):
    created = client.post("/api/v1/complaints", json=complaint_payload()).json()
    row = db.execute(
        "SELECT access_token_hash FROM complaints WHERE reference = ?", (created["reference"],)
    ).fetchone()
    assert row["access_token_hash"] != created["access_token"]
    assert len(row["access_token_hash"]) == 64


def test_short_description_rejected(client):
    response = client.post("/api/v1/complaints", json=complaint_payload(description="too short"))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_future_incident_date_rejected(client):
    response = client.post("/api/v1/complaints", json=complaint_payload(incident_date="2999-01-01"))
    assert response.status_code == 422


def test_consent_and_confirmation_are_required(client):
    without_consent = client.post("/api/v1/complaints", json=complaint_payload(consent=False))
    without_confirm = client.post("/api/v1/complaints", json=complaint_payload(confirmed=False))
    assert without_consent.status_code == 422
    assert without_confirm.status_code == 422


def test_phone_validation(client):
    bad = client.post("/api/v1/complaints", json=complaint_payload(contact_phone="12345"))
    good = client.post("/api/v1/complaints", json=complaint_payload(contact_phone="98765 43210"))
    assert bad.status_code == 422
    assert good.status_code == 201


def test_unknown_category_rejected(client):
    response = client.post("/api/v1/complaints", json=complaint_payload(category="witchcraft"))
    assert response.status_code == 422


def test_summary_is_extractive_and_labelled(client):
    body = client.post("/api/v1/complaints", json=complaint_payload()).json()
    summary = body["summary"]
    assert "Unauthorised withdrawal" in summary
    assert "Category" in summary
    assert "no legal decision" in summary.lower() or "કોઈ કાનૂની નિર્ણય" in summary
    assert "guilty" not in summary.lower()


def test_summary_in_gujarati(client):
    body = client.post("/api/v1/complaints", json=complaint_payload(language="gu")).json()
    assert "શ્રેણી" in body["summary"]


def test_preview_does_not_persist(client, db):
    before = db.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    preview = client.post(
        "/api/v1/complaints/preview",
        json={k: v for k, v in complaint_payload().items() if k != "confirmed"},
    )
    assert preview.status_code == 200
    assert preview.json()["summary"]
    after = db.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    assert before == after


def test_preview_flags_missing_information(client):
    payload = {k: v for k, v in complaint_payload().items() if k not in {"confirmed", "incident_date", "location"}}
    body = client.post("/api/v1/complaints/preview", json=payload).json()
    assert "missing_location" in body["checks"]
    assert "missing_incident_date" in body["checks"]


def test_admin_complaint_index_has_no_free_text(client, admin_headers):
    client.post("/api/v1/complaints", json=complaint_payload())
    body = client.get("/api/v1/admin/complaints", headers=admin_headers).json()
    assert body["items"]
    serialised = str(body)
    assert "Unauthorised withdrawal" not in serialised
    assert "98765" not in serialised
