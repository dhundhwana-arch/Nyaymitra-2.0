"""Department directory and feedback contract."""
from __future__ import annotations


def test_departments_list_is_bilingual_and_sourced(client):
    body = client.get("/api/v1/departments").json()
    assert len(body["items"]) >= 10
    for item in body["items"]:
        assert item["name_en"] and item["name_gu"]
        assert item["verification_status"] in {"verified", "requires_human_verification", "unverified"}
        assert item["source"] is not None
        assert "confirm" in body["notice"].lower() or "verification" in body["notice"].lower()


def test_department_filter_and_detail(client):
    body = client.get("/api/v1/departments", params={"jurisdiction": "state:gujarat"}).json()
    assert body["items"]
    key = body["items"][0]["department_key"]
    detail = client.get(f"/api/v1/departments/{key}")
    assert detail.status_code == 200
    assert client.get("/api/v1/departments/nope").status_code == 404


def test_no_department_is_marked_verified_without_a_date(client):
    for item in client.get("/api/v1/departments").json()["items"]:
        if item["verification_status"] == "verified":
            assert item["verified_on"], f"{item['department_key']} claims verification without a date"


def test_feedback_rejects_unknown_target_and_reason(client):
    assert client.post(
        "/api/v1/feedback", json={"target_type": "nonsense", "target_ref": "x", "reason": "other"}
    ).status_code == 422
    assert client.post(
        "/api/v1/feedback", json={"target_type": "ai_answer", "target_ref": "x", "reason": "nonsense"}
    ).status_code == 422


def test_feedback_message_is_length_limited(client):
    response = client.post(
        "/api/v1/feedback",
        json={"target_type": "article", "target_ref": "14", "reason": "wrong_information", "message": "x" * 5000},
    )
    assert response.status_code == 422
