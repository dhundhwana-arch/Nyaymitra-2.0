"""Provider reliability: retries, token accounting, health reporting, review packet, DB checks.

The HTTP server in this file is a **stub**. It proves the client's retry and parsing logic;
it does not prove that any real model works (see `docs/HANDOVER.md` §4 and
`docs/AI_PROVIDER_GUIDE.md`).
"""
from __future__ import annotations

import json
import sys
import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_db  # noqa: E402

from backend.app.ai.registry import describe  # noqa: E402
from backend.app.db import apply_migrations, get_db  # noqa: E402
from backend.app.services import monitoring, provider_health, review  # noqa: E402


class _Handler(BaseHTTPRequestHandler):
    script: list[tuple[int, dict]] = []   # responses in order; the last one repeats
    calls: int = 0
    last_payload: dict | None = None

    def do_GET(self):  # noqa: N802 - http.server API
        if self.path.rstrip("/").endswith("/models"):
            body = json.dumps({"object": "list", "data": [{"id": "stub-model"}]})
            self._send(200, body)
        else:
            self._send(404, "{}")

    def do_POST(self):  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        type(self).last_payload = json.loads(raw or "{}")
        index = min(type(self).calls, len(type(self).script) - 1)
        status, body = type(self).script[index]
        type(self).calls += 1
        self._send(status, json.dumps(body))

    def _send(self, status: int, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        return


@pytest.fixture()
def stub():
    handler = type("Handler", (_Handler,), {
        "script": [(200, {"choices": [{"message": {"content": "Article 14 is about equality."}}]})],
        "calls": 0,
        "last_payload": None,
    })
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, handler
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _live(settings, port: int, **overrides):
    base = dict(
        ai_provider="openai_compatible",
        ai_base_url=f"http://127.0.0.1:{port}/v1",
        ai_model="stub-model",
        ai_api_key="stub-key",
        ai_max_attempts=2,
        ai_retry_backoff_s=0.0,
    )
    base.update(overrides)
    return replace(settings, **base)


# --------------------------------------------------------------------- retries
def _provider(settings):
    from backend.app.ai.openai_compatible import OpenAICompatibleProvider

    return OpenAICompatibleProvider(settings)


def test_transient_500_is_retried_and_then_succeeds(stub, settings):
    server, handler = stub
    handler.script = [
        (500, {"error": "busy"}),
        (200, {"choices": [{"message": {"content": "ok"}, "usage": {"prompt_tokens": 7}}]}),
    ]
    result = _provider(_live(settings, server.server_port)).generate(
        system_prompt="s", user_prompt="u", max_output_tokens=50
    )
    assert result.text == "ok"
    assert handler.calls == 2, "a 5xx must be retried exactly once"


def test_client_error_is_not_retried(stub, settings):
    server, handler = stub
    handler.script = [(400, {"error": "bad request"})]
    with pytest.raises(Exception):
        _provider(_live(settings, server.server_port)).generate(
            system_prompt="s", user_prompt="u", max_output_tokens=50
        )
    assert handler.calls == 1, "a 4xx is our mistake; retrying only burns quota"


def test_rate_limit_is_retried(stub, settings):
    server, handler = stub
    handler.script = [
        (429, {"error": "slow down"}),
        (200, {"choices": [{"message": {"content": "ok"}}]}),
    ]
    result = _provider(_live(settings, server.server_port)).generate(
        system_prompt="s", user_prompt="u", max_output_tokens=50
    )
    assert result.text == "ok"
    assert handler.calls == 2


def test_retries_are_bounded(stub, settings):
    server, handler = stub
    handler.script = [(503, {"error": "down"})]
    with pytest.raises(Exception):
        _provider(_live(settings, server.server_port)).generate(
            system_prompt="s", user_prompt="u", max_output_tokens=50
        )
    assert handler.calls == 2, "AI_MAX_ATTEMPTS=2 means two calls, never an infinite loop"


# ------------------------------------------------------------------ usage/health
def test_usage_is_persisted_with_tokens(client, db):
    query_id = monitoring.log_query(db, request_id="r1", language="en", query_text="q",
                                    category=None, provider="openai_compatible", latency_ms=42,
                                    status="ok", error_code=None)
    monitoring.log_answer(db, query_log_id=query_id, provider="openai_compatible",
                          model="stub-model", grounded=True, degraded=False, citations=[],
                          answer_text="a", warnings=[],
                          usage={"prompt_tokens": 120, "completion_tokens": 30})
    row = db.execute("SELECT prompt_tokens, completion_tokens FROM ai_answers ORDER BY id DESC").fetchone()
    assert (row["prompt_tokens"], row["completion_tokens"]) == (120, 30)


def test_usage_is_null_when_the_provider_does_not_report_it(client, db):
    query_id = monitoring.log_query(db, request_id="r2", language="en", query_text="q",
                                    category=None, provider="offline", latency_ms=1,
                                    status="ok", error_code=None)
    monitoring.log_answer(db, query_log_id=query_id, provider="offline", model=None,
                          grounded=True, degraded=False, citations=[], answer_text="a",
                          warnings=[], usage=None)
    row = db.execute("SELECT prompt_tokens FROM ai_answers ORDER BY id DESC").fetchone()
    assert row["prompt_tokens"] is None, "unknown usage is NULL, not zero"


def test_usage_summary_aggregates_without_text(client, db):
    query_id = monitoring.log_query(db, request_id="r3", language="en",
                                    query_text="my private question", category=None,
                                    provider="openai_compatible", latency_ms=99,
                                    status="ok", error_code=None)
    monitoring.log_answer(db, query_log_id=query_id, provider="openai_compatible",
                          model="stub-model", grounded=True, degraded=False, citations=[],
                          answer_text="answer text", warnings=[],
                          usage={"prompt_tokens": 10, "completion_tokens": 5})
    summary = monitoring.usage_summary(db, days=30)
    assert summary["totals"]["prompt_tokens"] >= 10
    serialised = json.dumps(summary)
    assert "my private question" not in serialised
    assert "answer text" not in serialised
    assert summary["latency"]["answers"] >= 1


def test_health_reports_not_configured_without_leaking_keys(settings):
    offline = replace(settings, ai_provider="auto", ai_api_key="sk-secret-value",
                      ai_base_url=None, ai_model=None)
    payload = provider_health.health(offline, probe=False)
    assert payload["status"] == provider_health.STATUS_NOT_CONFIGURED
    assert "sk-secret-value" not in json.dumps(payload)
    assert payload["api_key_set"] is True


def test_health_reports_ok_for_a_reachable_endpoint(stub, settings):
    server, _ = stub
    payload = provider_health.health(_live(settings, server.server_port))
    assert payload["status"] == provider_health.STATUS_OK
    assert payload["endpoint"]["models"] == ["stub-model"]
    assert "stub-key" not in json.dumps(payload)


def test_health_flags_a_missing_model(stub, settings):
    """Reachable but the configured model is absent: the most common confusing failure."""
    server, _ = stub
    payload = provider_health.health(_live(settings, server.server_port, ai_model="llama9:70b"))
    assert payload["status"] == provider_health.STATUS_UNREACHABLE
    assert "does not list the configured model" in payload["detail"]


def test_health_reports_unreachable_endpoint(settings):
    payload = provider_health.health(_live(settings, 9, ai_api_key="x"), timeout=0.3)
    assert payload["status"] == provider_health.STATUS_UNREACHABLE


def test_describe_matches_configuration(settings):
    assert describe(replace(settings, ai_provider="offline")).name == "offline"
    assert describe(replace(settings, ai_provider="auto", ai_api_key=None)).live is False


# ---------------------------------------------------------------- review packet
def test_review_packet_lists_every_unverified_item(client, db):
    packet = review.build(db)
    kinds = packet["counts"]
    assert kinds.get("article", 0) >= 9
    assert kinds.get("department", 0) >= 11
    assert kinds.get("triage", 0) >= 5
    assert kinds.get("glossary", 0) >= 18
    assert packet["total"] == len(packet["items"])
    for item in packet["items"]:
        assert item["checklist"], f"{item['ref']} has no checklist"
        assert item["sign_off_fields"], f"{item['ref']} has no sign-off fields"
        assert item["verification_status"] != "verified"


def test_review_packet_markdown_is_reviewable(client, db):
    packet = review.build(db, kinds=("article",))
    markdown = review.to_markdown(packet)
    assert markdown.startswith("# Review packet")
    assert "- [ ]" in markdown, "the reviewer needs checkboxes"
    assert "checked_by:" in markdown, "the reviewer needs a place to sign"
    assert "not been verified by a qualified reviewer" in markdown


def test_review_packet_contains_no_complaint_data(client, db):
    """The word "complaint" is legitimate triage content; a complaint *record* is not."""
    serialised = json.dumps(review.build(db))
    assert "NYM-" not in serialised, "a complaint reference must never appear in a review packet"
    assert "access_token" not in serialised
    # Only the four reviewable tables are read: prove it by checking the queries used.
    import inspect
    source = inspect.getsource(review)
    for table in ("FROM complaints", "FROM documents", "FROM query_logs", "FROM ai_answers"):
        assert table not in source, f"review packet must not read {table}"


def test_review_packet_endpoint_requires_a_token(client):
    assert client.get("/api/v1/admin/review-packet").status_code == 401
    assert client.get("/api/v1/admin/review-packet", headers={"X-Admin-Token": "wrong"}).status_code == 401


def test_review_packet_endpoint_formats(client, monitor_headers):
    json_response = client.get("/api/v1/admin/review-packet", headers=monitor_headers)
    assert json_response.status_code == 200
    body = json_response.json()
    assert body["total"] >= 43  # 9 + 11 + 5 + 18
    assert set(body["counts"]) >= {"article", "department", "triage", "glossary"}

    markdown = client.get("/api/v1/admin/review-packet?format=markdown", headers=monitor_headers)
    assert markdown.status_code == 200
    assert markdown.json()["markdown"].startswith("# Review packet")

    bad = client.get("/api/v1/admin/review-packet?kinds=bogus", headers=monitor_headers)
    assert bad.status_code in {400, 422}


def test_ai_health_endpoint(client, monitor_headers):
    response = client.get("/api/v1/admin/ai/health?probe=false", headers=monitor_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "not_configured", "unreachable"}
    assert "api_key" not in json.dumps(body).replace("api_key_set", "")


def test_ai_usage_endpoint(client, monitor_headers):
    response = client.get("/api/v1/admin/ai/usage?days=7", headers=monitor_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["days"] == 7
    assert "totals" in body and "providers" in body


# --------------------------------------------------------------- database check
def test_check_db_passes_on_a_healthy_database(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        apply_migrations(conn, isolated_settings.migrations_dir)
        report = check_db.check(conn, isolated_settings)
    assert report["problems"] == [], report["problems"]
    assert report["integrity"] == "ok"
    assert report["migrations"]["pending"] == []
    assert report["indexes"]["missing"] == []
    assert report["ok"] is True


def test_check_db_detects_a_missing_index(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        apply_migrations(conn, isolated_settings.migrations_dir)
        conn.execute("DROP INDEX idx_ai_answers_created")
        report = check_db.check(conn, isolated_settings)
    assert "idx_ai_answers_created" in " ".join(report["problems"])
    assert report["ok"] is False


def test_check_db_detects_an_orphan_document(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        apply_migrations(conn, isolated_settings.migrations_dir)
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute(
            """INSERT INTO documents (stored_name, original_name, mime_type, size_bytes, sha256,
                                      owner_token_hash, complaint_id)
               VALUES ('x.pdf', 'x.pdf', 'application/pdf', 1, 'deadbeef', 'hash', 99999)"""
        )
        report = check_db.check(conn, isolated_settings)
    assert report["orphans"]["documents_without_complaint"] == 1
    assert any("documents_without_complaint" in warning for warning in report["warnings"])


def test_check_db_never_reports_personal_data(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        apply_migrations(conn, isolated_settings.migrations_dir)
        conn.execute(
            """INSERT INTO complaints (reference, access_token_hash, category, title,
                                       description, summary, location, incident_date,
                                       consent_given, status)
               VALUES ('NYM-TEST01', 'hash', 'other', 'private title',
                       'private description text', 'summary', 'Jamnagar', '2026-01-01',
                       1, 'submitted')"""
        )
        report = check_db.check(conn, isolated_settings)
    serialised = json.dumps(report)
    assert "private description text" not in serialised
    assert "NYM-TEST01" not in serialised
    assert report["personal_data"]["complaints"] == 1
