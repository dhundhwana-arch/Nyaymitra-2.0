"""Data activation: CORS, configurable API base, Legal Library, assistant honesty, attribution."""
from __future__ import annotations

import dataclasses
import importlib.util
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parents[2]
WEB = REPO / "web"
ATTRIBUTION = "Created & Developed by Bambhaniya Divyesh Nonghanbhai"
ATTRIBUTION_HTML = "Created &amp; Developed by Bambhaniya Divyesh Nonghanbhai"
FRONTEND = "https://nyaymitra-frontend.pages.dev"


# ------------------------------------------------------------------ CORS
@pytest.fixture()
def cors_client(settings):
    from backend.app.main import create_app

    app = create_app(dataclasses.replace(settings, allowed_origins=(FRONTEND,)))
    with TestClient(app) as c:
        yield c


def test_no_cors_headers_unless_configured(client):
    r = client.get("/api/v1/meta", headers={"Origin": FRONTEND})
    assert r.status_code == 200 and "access-control-allow-origin" not in r.headers


def test_cors_allows_only_the_configured_frontend(cors_client):
    ok = cors_client.get("/api/v1/constitution/parts", headers={"Origin": FRONTEND})
    assert ok.headers["access-control-allow-origin"] == FRONTEND
    other = cors_client.get("/api/v1/constitution/parts", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in other.headers


def test_cors_preflight_for_json_post_and_admin_header(cors_client):
    for header in ("content-type", "x-admin-token"):
        r = cors_client.options("/api/v1/ai/explain", headers={
            "Origin": FRONTEND, "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": header})
        assert r.status_code == 200, header
        assert r.headers["access-control-allow-origin"] == FRONTEND


def test_cors_headers_present_on_error_responses(cors_client):
    r = cors_client.get("/api/v1/constitution/articles/999", headers={"Origin": FRONTEND})
    assert r.status_code == 404 and r.headers["access-control-allow-origin"] == FRONTEND


# ------------------------------------------------------- frontend wiring
def test_backend_serves_config_and_service_worker(client):
    cfg = client.get("/config.js")
    assert cfg.status_code == 200 and "NYAYMITRA_CONFIG" in cfg.text
    assert client.get("/sw.js").status_code == 200


def test_frontend_uses_configurable_api_base():
    for name in ("app.js", "admin.js"):
        js = (WEB / name).read_text(encoding="utf-8")
        assert "NYAYMITRA_CONFIG" in js and "var API = '/api/v1'" not in js
    for page in ("index.html", "admin.html"):
        html = (WEB / page).read_text(encoding="utf-8")
        assert html.index('src="/config.js"') < html.index('.js" defer></script>\n</body>')


def test_no_placeholder_backend_url_is_shipped():
    for path in WEB.iterdir():
        if path.is_file() and path.suffix not in {".png", ".svg"}:
            assert "YOUR_BACKEND_URL" not in path.read_text(encoding="utf-8"), path.name
    shell = (WEB / "sw.js").read_text(encoding="utf-8")
    assert '"/config.js"' in shell and "/api/openapi.json" not in shell


def _configure_module():
    spec = importlib.util.spec_from_file_location("configure_frontend", REPO / "scripts/configure_frontend.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_configure_frontend_script(tmp_path):
    mod = _configure_module()
    web = tmp_path / "web"
    web.mkdir()
    for name in ("config.js", "_headers"):
        shutil.copy(WEB / name, web / name)
    mod.configure(mod.normalise("https://api.example.org/"), web)
    assert 'apiBase: "https://api.example.org"' in (web / "config.js").read_text(encoding="utf-8")
    assert "connect-src 'self' https://api.example.org;" in (web / "_headers").read_text(encoding="utf-8")
    mod.configure("", web)
    assert 'apiBase: ""' in (web / "config.js").read_text(encoding="utf-8")
    assert "connect-src 'self';" in (web / "_headers").read_text(encoding="utf-8")
    for bad in ("api.example.org", "https://api.example.org/api/v1", "http://api.example.org"):
        with pytest.raises(ValueError):
            mod.normalise(bad)


def test_shipped_frontend_defaults_to_same_origin():
    assert 'apiBase: ""' in (WEB / "config.js").read_text(encoding="utf-8")


# ---------------------------------------------------------- attribution
def test_attribution_text_is_exact_everywhere():
    assert ATTRIBUTION_HTML in (WEB / "index.html").read_text(encoding="utf-8")   # footer, every SPA page
    assert ATTRIBUTION_HTML in (WEB / "admin.html").read_text(encoding="utf-8")   # admin sign-in page
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert f"var ATTRIBUTION = '{ATTRIBUTION}';" in app                           # home + About views
    assert app.count("esc(ATTRIBUTION)") >= 2
    assert ".attribution" in (WEB / "styles.css").read_text(encoding="utf-8")


# -------------------------------------------------------- legal library
def test_library_lists_every_stored_dataset(client):
    data = client.get("/api/v1/library", params={"page_size": 50, "language": "en"}).json()
    assert data["facets"] == {"constitution": 9, "guide": 5, "department": 11, "glossary": 18}
    assert data["total"] == 43 and len(data["items"]) == 43
    assert data["official_text_available"] is False
    for item in data["items"]:
        assert item["title"] and item["verification_status"] != "verified"
        assert item["content_kind"] == "owner_authored_summary"


def test_library_category_and_language_filters(client):
    guides = client.get("/api/v1/library", params={"category": "guide"}).json()
    assert guides["total"] == 5 and {i["category"] for i in guides["items"]} == {"guide"}
    assert guides["facets"]["constitution"] == 9          # facets describe the whole result set
    for lang in ("gu", "en"):
        data = client.get("/api/v1/library", params={"content_language": lang, "page_size": 50}).json()
        assert data["total"] == 43 and all(lang in i["languages"] for i in data["items"])
    assert client.get("/api/v1/library", params={"category": "santali"}).status_code == 422


def test_library_keyword_search_in_both_languages(client):
    en = client.get("/api/v1/library", params={"q": "equality", "language": "en"}).json()
    assert en["items"][0]["id"] == "constitution:14"
    gu = client.get("/api/v1/library", params={"q": "સમાનતા", "language": "gu"}).json()
    assert any(i["id"] == "constitution:14" for i in gu["items"])
    assert gu["items"][0]["title"] == "કાયદા સમક્ષ સમાનતા"
    none = client.get("/api/v1/library", params={"q": "zzzzqqqq"}).json()
    assert none["total"] == 0 and none["items"] == []


def test_library_item_detail_and_not_found(client):
    item = client.get("/api/v1/library/constitution/14").json()
    assert item["label"] == "Article 14" and item["body_en"] and item["body_gu"]
    assert item["content_kind"] == "owner_authored_summary"
    assert item["source"]["source_key"] == "owner-authored-citizen-notes"
    guide = client.get("/api/v1/library/guide/consumer-complaint").json()
    assert guide["list_en"] and guide["list_gu"]
    assert client.get("/api/v1/library/constitution/15").status_code == 404
    assert client.get("/api/v1/library/glossary/nope").status_code == 404


def test_library_never_exposes_quarantined_santali_rows(client):
    data = client.get("/api/v1/library", params={"page_size": 50}).text
    assert not any(0x1C50 <= ord(ch) <= 0x1C7F for ch in data)          # no Ol Chiki
    assert client.get("/api/v1/library", params={"q": "Section Chunk"}).json()["total"] == 0


# ------------------------------------------------------------ assistant
def _ask(client, question, language):
    r = client.post("/api/v1/ai/explain", json={"question": question, "language": language})
    assert r.status_code == 200, r.text
    return r.json()


def test_assistant_reports_a_named_article_that_is_not_stored(client):
    a = _ask(client, "What does Article 300A say about property?", "en")
    assert "article_not_available:300A" in a["warnings"]
    assert a["answer"].startswith("Note: Article 300A is not available")
    assert a["citations"] == [] and a["guide"] is None            # "rti" must not match "property"
    g = _ask(client, "અનુચ્છેદ ૧૫ શું કહે છે?", "gu")
    assert "article_not_available:15" in g["warnings"] and "Article 15" in g["answer"]


def test_assistant_returns_a_named_article_that_is_stored(client):
    a = _ask(client, "Explain Article 21A", "en")
    assert a["citations"][0]["article_label"] == "Article 21A"
    assert not [w for w in a["warnings"] if w.startswith("article_not_available")]
    g = _ask(client, "આર્ટિકલ ૩૨ સમજાવો", "gu")
    assert g["citations"][0]["article_label"] == "Article 32"


def test_assistant_labels_explanations_as_not_official_text(client):
    en = _ask(client, "What is equality before law?", "en")
    assert "Article 14" in en["answer"] and "[explanation — not the official text]" in en["answer"]
    assert en["citations"][0]["verification_status"] == "requires_human_verification"
    gu = _ask(client, "કાયદા સમક્ષ સમાનતા એટલે શું?", "gu")
    assert "સત્તાવાર લખાણ નથી" in gu["answer"] and gu["citations"]


def test_triage_latin_keywords_match_whole_words_only():
    from backend.app.services.triage import _keyword_in

    assert _keyword_in("rti", "i filed an rti last month")
    assert not _keyword_in("rti", "question about property")
    assert _keyword_in("ગ્રાહક", "ગ્રાહકોની ફરિયાદ")


def test_assistant_citation_links_resolve_to_a_real_article_route(client):
    """The UI turns 'Article 14' into #/library/14; '/articles/Article14' was a 404."""
    js = (WEB / "app.js").read_text(encoding="utf-8")
    assert "cite.article_label.replace(/^Article\\s+/i, '')" in js
    for cite in _ask(client, "What is equality before law?", "en")["citations"]:
        number = cite["article_label"].removeprefix("Article ").strip()
        assert client.get(f"/api/v1/constitution/articles/{number}").status_code == 200
