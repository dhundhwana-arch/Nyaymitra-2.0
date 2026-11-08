"""Tests for the changeset integrity checker and the live-provider probe.

The provider tests use a **stub HTTP server** that speaks the OpenAI chat-completions
protocol. That proves the probe's logic (it parses a real HTTP response, through the real
provider client and the real guard) but it does *not* prove a real model works — nothing in
this repository can do that without a model. `docs/HANDOVER.md` records the difference.
"""
from __future__ import annotations

import json
import re
import sys
import tarfile
import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import verify_changeset as changeset  # noqa: E402
import verify_ai_provider as provider_probe  # noqa: E402


# ------------------------------------------------------------------ changeset: hashing
def test_sha256_is_stable_and_content_dependent(tmp_path):
    target = tmp_path / "a.txt"
    target.write_bytes(b"nyaymitra\n")
    first = changeset.sha256_file(target)
    assert len(first) == 64
    assert changeset.sha256_file(target) == first, "hashing must be deterministic"
    target.write_bytes(b"nyaymitra!\n")
    assert changeset.sha256_file(target) != first


def test_manifest_round_trip(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "one.py").write_text("print(1)\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")

    paths = ["src/one.py", "README.md"]
    manifest = changeset.build_manifest(tmp_path, paths, commit="deadbeef")
    assert manifest["entry_count"] == 2
    assert [entry["path"] for entry in manifest["entries"]] == ["README.md", "src/one.py"]
    assert all(len(entry["sha256"]) == 64 for entry in manifest["entries"])

    manifest_path = tmp_path / "manifest.json"
    changeset.write_manifest(manifest_path, manifest)
    loaded = changeset.load_manifest(manifest_path)
    assert changeset.verify_tree(tmp_path, loaded)["ok"] is True


def test_modified_and_missing_and_extra_files_are_reported(tmp_path):
    (tmp_path / "keep.txt").write_text("keep\n", encoding="utf-8")
    (tmp_path / "change.txt").write_text("before\n", encoding="utf-8")
    (tmp_path / "gone.txt").write_text("bye\n", encoding="utf-8")
    manifest = changeset.build_manifest(
        tmp_path, ["keep.txt", "change.txt", "gone.txt"], commit=None
    )

    (tmp_path / "change.txt").write_text("after\n", encoding="utf-8")
    (tmp_path / "gone.txt").unlink()
    (tmp_path / "added.txt").write_text("new\n", encoding="utf-8")

    report = changeset.compare(
        manifest["entries"],
        changeset.hash_entries(tmp_path, ["keep.txt", "change.txt", "added.txt"]),
    )
    assert report["ok"] is False
    assert report["modified"] == ["change.txt"]
    assert report["missing"] == ["gone.txt"]
    assert report["extra"] == ["added.txt"]


def test_tampered_manifest_is_rejected(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"format": "something-else", "entries": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        changeset.load_manifest(bad)


def test_archive_is_extracted_and_verified(tmp_path):
    root = tmp_path / "checkout"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    (root / "README.md").write_text("docs\n", encoding="utf-8")
    manifest = changeset.build_manifest(root, ["pkg/mod.py", "README.md"], commit="abc123")

    archive = tmp_path / "code.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(root, arcname="nyaymitra-2.0")
    report = changeset.verify_archive(archive, manifest)
    assert report["ok"] is True, report
    assert report["archive_files"] == 2


def test_archive_with_an_extra_file_is_not_ok(tmp_path):
    root = tmp_path / "checkout"
    root.mkdir()
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    manifest = changeset.build_manifest(root, ["a.txt"], commit=None)
    (root / "b.txt").write_text("b\n", encoding="utf-8")
    archive = tmp_path / "code.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(root, arcname="checkout")
    report = changeset.verify_archive(archive, manifest)
    assert report["ok"] is False
    assert report["extra"] == ["b.txt"]


def test_cli_verifies_the_real_checkout():
    """The manifest mode must work against this repository, not just a toy directory."""
    paths = changeset.git_tracked_paths(REPO_ROOT)
    assert paths, "git reported no tracked files"
    manifest = changeset.build_manifest(REPO_ROOT, paths, commit=changeset.head_commit(REPO_ROOT))
    assert manifest["entry_count"] == len(paths)
    assert changeset.verify_tree(REPO_ROOT, manifest)["ok"] is True


# ------------------------------------------------------------------ provider probe
class _StubHandler(BaseHTTPRequestHandler):
    """Minimal OpenAI-compatible endpoint. Records the last request body."""

    answer: str = ""
    models: list[str] = ["stub-model"]
    last_body: dict | None = None
    mode: str = "answer"  # answer | error

    def do_GET(self):  # noqa: N802 - http.server API
        if self.path.rstrip("/").endswith("/models"):
            body = json.dumps({"object": "list", "data": [{"id": m} for m in self.models]})
            self._send(200, body)
        else:
            self._send(404, "{}")

    def do_POST(self):  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        type(self).last_body = json.loads(raw or "{}")
        if type(self).mode == "error":
            self._send(500, "{}")
            return
        text = type(self).answer
        if "{first_label}" in text:
            prompt = json.dumps(type(self).last_body)
            match = re.search(r"id=(.*?) status=", prompt)
            label = match.group(1) if match else "Article 14"
            text = text.replace("{first_label}", label)
        self._send(200, json.dumps({
            "choices": [{"message": {"role": "assistant", "content": text}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }))

    def _send(self, status: int, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):  # keep pytest output quiet
        return


@pytest.fixture()
def stub_server():
    handler = type("Handler", (_StubHandler,), {
        "answer": "This is a stub answer. This is information, not legal advice.",
        "mode": "answer",
        "last_body": None,
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


def _provider_settings(settings, port: int):
    return replace(
        settings,
        ai_provider="openai_compatible",
        ai_base_url=f"http://127.0.0.1:{port}/v1",
        ai_model="stub-model",
        ai_api_key="stub-key",
        ai_fallback_mode="offline_grounded",
    )


def test_unconfigured_provider_is_reported_as_unavailable(settings):
    offline = replace(settings, ai_provider="auto", ai_api_key=None, ai_base_url=None, ai_model=None)
    status, problems = provider_probe.evaluate({
        "provider": "offline", "grounded": True, "citations": [], "answer": "x", "warnings": [],
    })
    assert status == "unavailable"
    assert problems
    assert "provider preference : auto" in provider_probe.requirement(offline)


def test_rejected_model_output_is_ungrounded_not_unavailable():
    status, problems = provider_probe.evaluate({
        "provider": "offline",
        "grounded": True,
        "citations": [{"article_label": "Article 14"}],
        "answer": "fallback text",
        "warnings": ["model_rejected:uncited_article_reference: 499", "fell_back_to_offline_grounded"],
    })
    assert status == "ungrounded"
    assert any("rejected" in problem for problem in problems)


def test_preflight_reports_reachability_and_models(stub_server, settings):
    server, _ = stub_server
    info = provider_probe.preflight(_provider_settings(settings, server.server_port))
    assert info["reachable"] is True
    assert info["models"] == ["stub-model"]


def test_preflight_reports_an_unreachable_endpoint(settings):
    dead = _provider_settings(settings, 9)  # discard port: nothing listens
    info = provider_probe.preflight(dead, timeout=0.5)
    assert info["reachable"] is False
    assert "could not reach" in info["detail"]


def test_stub_model_answer_is_grounded_and_cited(client, db, settings, stub_server):
    """End to end through rag.answer_question: retrieval, guard, citations, provider client.

    The server is a stub, so this validates the probe and the wiring — not a real model.
    """
    server, handler = stub_server
    handler.answer = "{first_label} is relevant to your question. This is information, not legal advice."
    live = _provider_settings(settings, server.server_port)

    payload = provider_probe.probe(
        db, live, question="What does equality before the law mean?", language="en"
    )
    assert payload["status"] == "live", payload["problems"]
    assert payload["result"]["provider"] == "openai_compatible"
    assert payload["result"]["model"] == "stub-model"
    assert payload["cited_labels"], "a grounded answer must carry citations"
    assert any(citation["article_label"] in handler.last_body["messages"][1]["content"]
               for citation in payload["result"]["citations"])
    assert "SOURCE id=" in handler.last_body["messages"][1]["content"], "sources were not injected"


def test_hallucinated_article_is_caught_end_to_end(client, db, settings, stub_server):
    server, handler = stub_server
    handler.answer = "Article 499 says you are guilty and you will win. Guaranteed."
    live = _provider_settings(settings, server.server_port)

    payload = provider_probe.probe(
        db, live, question="What does equality before the law mean?", language="en"
    )
    assert payload["status"] == "ungrounded"
    assert payload["result"]["provider"] == "offline", "the guard must fall back to the offline text"


def test_provider_http_error_degrades_instead_of_crashing(client, db, settings, stub_server):
    server, handler = stub_server
    handler.mode = "error"
    live = _provider_settings(settings, server.server_port)

    payload = provider_probe.probe(
        db, live, question="What does equality before the law mean?", language="en"
    )
    assert payload["status"] == "unavailable"
    assert any("provider_unavailable" in problem for problem in payload["problems"])


def test_guarded_citation_of_a_real_model_sentence():
    """Regression: "Article 14 is ..." used to be parsed as article "14I" and rejected."""
    from backend.app.ai import guard

    assert guard.find_cited_articles("Article 14 is relevant to you.") == {"14"}
    ok, problems = guard.validate_answer(
        "Article 14 is relevant to you.", allowed_article_labels={"Article 14"}
    )
    assert ok, problems


def test_gujarati_digits_match_ascii_labels():
    from backend.app.ai import guard

    assert guard.find_cited_articles("કલમ ૧૪ અને કલમ ૧૯એ") >= {"14"}
    ok, problems = guard.validate_answer(
        "કલમ ૧૪ તમારા પ્રશ્ન સાથે સંબંધિત છે.", allowed_article_labels={"Article 14"}
    )
    assert ok, problems


def test_exit_codes_are_distinct():
    assert provider_probe.EXIT_LIVE == 0
    assert provider_probe.EXIT_UNAVAILABLE == 3
    assert provider_probe.EXIT_UNGROUNDED == 4
    assert len({provider_probe.EXIT_LIVE, provider_probe.EXIT_UNAVAILABLE,
                provider_probe.EXIT_UNGROUNDED}) == 3


def test_requirement_text_never_contains_a_secret(client, settings):
    with_key = replace(settings, ai_api_key="sk-super-secret-value", ai_base_url="http://x/v1")
    text = provider_probe.requirement(with_key)
    assert "sk-super-secret-value" not in text
    assert "API key             : set" in text
