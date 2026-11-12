"""Static accessibility and dead-end checks for the two served pages.

These are not a substitute for a screen-reader session (see TESTING_REPORT.md), but they
catch the mechanical defects that are cheap to introduce and expensive to notice.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB = REPO_ROOT / "web"


def test_no_dead_links():
    for name in ("index.html", "admin.html"):
        text = (WEB / name).read_text(encoding="utf-8")
        assert 'href="#"' not in text, f"{name} contains a link to nowhere"
        assert 'javascript:' not in text.lower(), f"{name} contains a javascript: URL"


def test_every_button_declares_a_type():
    """A button without type=submit inside a form submits it by accident."""
    pattern = re.compile(r"<button(?![^>]*\btype=)[^>]*>", re.IGNORECASE)
    for name in ("index.html", "admin.html"):
        assert not pattern.search((WEB / name).read_text(encoding="utf-8")), name
    for name in ("app.js", "admin.js"):
        text = (WEB / name).read_text(encoding="utf-8")
        for match in re.finditer(r"'<button[^']*'", text):
            assert "type=" in match.group(0), f"{name}: {match.group(0)[:80]}"


def test_skip_link_targets_exist():
    for page, main_id in (("index.html", "main"), ("admin.html", "adminMain")):
        text = (WEB / page).read_text(encoding="utf-8")
        assert 'class="skip-link"' in text
        assert f'href="#{main_id}"' in text
        assert f'id="{main_id}"' in text
        assert f'<main id="{main_id}" tabindex="-1">' in text, "main must be focusable for skip links"


def test_navigation_targets_have_routes():
    index = (WEB / "index.html").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    for nav in set(re.findall(r'data-nav="([a-z]+)"', index)):
        assert f"current.name === '{nav}'" in app, f"nav item {nav} has no route"


def test_forms_are_never_submitted_by_default():
    """Every form handler must call preventDefault, otherwise the page navigates away."""
    app = (WEB / "app.js").read_text(encoding="utf-8")
    handlers = re.findall(r"addEventListener\('submit',\s*(?:async\s*)?function\s*\(event\)\s*\{(.{0,200})", app, re.S)
    assert handlers, "no submit handlers found"
    for body in handlers:
        assert "preventDefault()" in body, "a submit handler does not prevent the default action"


def test_admin_page_is_not_indexable():
    text = (WEB / "admin.html").read_text(encoding="utf-8")
    assert 'name="robots"' in text and "noindex" in text


def test_language_switch_is_announced():
    index = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'id="langGu"' in index and 'aria-pressed' in index
    assert 'id="langEn"' in index and 'aria-pressed' in index
    assert 'lang="gu"' in index and 'lang="en"' in index


def test_live_regions_exist_for_async_updates():
    index = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'id="statusRegion"' in index
    assert 'aria-live' in index
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert "aria-live" in app and "aria-invalid" in app


def test_no_third_party_or_inline_script_in_either_page():
    for name in ("index.html", "admin.html"):
        text = (WEB / name).read_text(encoding="utf-8")
        assert not re.search(r"<script(?![^>]*\bsrc=)", text)
        assert "http://" not in text.replace("http://localhost", "")


def test_voice_has_a_text_alternative():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert "webkitSpeechRecognition" in app or "SpeechRecognition" in app
    assert "speechSynthesis" in app
    # The typed textarea must remain the primary input, with the mic as an extra.
    assert 'id="question"' in app
    assert "micUnsupported" in app, "a browser without speech support must be told so"
