"""Application startup, health, metadata, static assets and basic accessibility checks."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB = REPO_ROOT / "web"


def test_app_imports_and_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "2.1.0"


def test_legacy_entry_point_still_imports():
    """`uvicorn backend.main:app` must keep working for existing run instructions."""
    from backend.main import app as legacy_app

    assert legacy_app.title.startswith("NYAYMITRA")


def test_readiness_reports_database_and_storage(client):
    body = client.get("/api/v1/ready").json()
    assert body["ready"] is True
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["migrations"] == "ok"
    assert body["checks"]["storage"] == "ok"


def test_meta_declares_capabilities_and_disclaimers(client):
    body = client.get("/api/v1/meta").json()
    assert body["capabilities"]["languages"] == ["gu", "en"]
    assert body["capabilities"]["ai_provider"] in {"offline", "openai_compatible"}
    assert any("not an AI judge" in line for line in body["disclaimers"])
    assert body["corpus"]["verified_text"] == 0, "no official text is loaded yet — the API must say so"


def test_openapi_schema_is_served(client):
    schema = client.get("/api/openapi.json").json()
    assert schema["info"]["title"].startswith("NYAYMITRA")
    assert "/api/v1/constitution/articles" in schema["paths"]
    assert "/api/v1/ai/explain" in schema["paths"]


def test_home_page_is_served_with_security_headers(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "NYAYMITRA" in response.text
    csp = response.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_assets_are_served_locally(client):
    for path, content_type in (
        ("/app.js", "javascript"),
        ("/styles.css", "text/css"),
        ("/manifest.webmanifest", "json"),
        ("/favicon.svg", "svg"),
    ):
        response = client.get(path)
        assert response.status_code == 200, path
        assert content_type in response.headers["content-type"], path
    assert client.get("/admin").status_code == 200


def test_frontend_has_no_third_party_assets():
    """The citizen UI must not depend on a CDN: rural bandwidth and CSP both matter."""
    external = re.compile(
        r"""(?:src|href)\s*=\s*["']https?://(?!localhost|127\.0\.0\.1)"""
        r"""|url\(\s*["']?https?://|@import\s+url\(\s*["']?https?://""",
        re.IGNORECASE,
    )
    for name in ("index.html", "admin.html", "app.js", "styles.css"):
        text = (WEB / name).read_text(encoding="utf-8")
        assert not external.search(text), f"{name} loads a third-party asset"
        assert "fonts.googleapis" not in text.lower()
        assert "cdn.jsdelivr" not in text.lower()


def test_html_has_no_inline_scripts_and_has_lang():
    parser_checks = []
    for name in ("index.html", "admin.html"):
        text = (WEB / name).read_text(encoding="utf-8")
        assert re.search(r'<html[^>]+lang="', text), f"{name} is missing <html lang>"
        assert 'name="viewport"' in text, f"{name} is missing the viewport meta tag"
        assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", text), f"{name} has an inline <script>"
        parser_checks.append(name)
    assert parser_checks


class _LabelCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.controls: list[tuple[str, str]] = []
        self.labels: set[str] = set()
        self.current_label_for: str | None = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "label" and attributes.get("for"):
            self.current_label_for = attributes["for"]
        if tag in {"input", "select", "textarea"}:
            control_id = attributes.get("id")
            if attributes.get("type") in {"hidden", "submit", "button"}:
                return
            if control_id:
                self.controls.append((tag, control_id))

    def handle_endtag(self, tag):
        if tag == "label":
            self.current_label_for = None


def test_every_visible_form_control_has_a_label(client):
    text = client.get("/").text
    collector = _LabelCollector()
    collector.feed(text)
    unlabelled = [
        control_id
        for tag, control_id in collector.controls
        if f'for="{control_id}"' not in text and 'aria-label' not in text
    ]
    # Controls rendered by app.js are covered by the JS template checks below.
    assert unlabelled == [], f"unlabelled controls in index.html: {unlabelled}"


def test_app_js_labels_dynamic_controls(settings):
    js = (WEB / "app.js").read_text(encoding="utf-8")
    for control_id in ("question", "category", "cTitle", "cDescription", "cDocs", "cConsent", "savedRef", "savedToken"):
        assert f'for="{control_id}"' in js, f"missing <label for={control_id}> in app.js"
    assert "aria-live" in js
    assert "aria-invalid" in js
    assert "localStorage" in js


def test_responsive_css_uses_media_queries_and_reduced_motion():
    css = (WEB / "styles.css").read_text(encoding="utf-8")
    assert "@media (min-width: 720px)" in css or "@media (min-width" in css
    assert "prefers-reduced-motion" in css
    assert "min-height: 44px" in css, "tap targets must be at least 44px high"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_javascript_syntax():
    for name in ("app.js", "admin.js"):
        result = subprocess.run(
            ["node", "--check", str(WEB / name)], capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr


def test_manifest_is_valid_json():
    payload = json.loads((WEB / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert payload["start_url"] == "/"
    assert payload["display"] == "standalone"


def test_legacy_frontend_is_not_served(client):
    """The broken prototype must stay archived, not reachable from the app."""
    assert client.get("/index_v2.html").status_code == 404
    assert not (REPO_ROOT / "frontend" / "library_fix.js").exists()
    assert (REPO_ROOT / "frontend" / "legacy" / "LEGACY_NOTES.md").exists()
