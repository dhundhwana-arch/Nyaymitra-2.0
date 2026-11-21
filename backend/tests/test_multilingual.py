"""Multilingual architecture: registry, Unicode handling, fallback honesty, per-language text.

Every "article" body used here is a synthetic placeholder ("PLACEHOLDER …"); none of it is
constitutional text, and no test relies on a translation being correct.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import languages
from backend.app.db import get_db
from backend.app.services import ingest as ingest_service
from backend.app.services import textsearch

ROOT = Path(__file__).resolve().parents[2]
LOCALES = ROOT / "web" / "locales"
SOURCE = "india-code-constitution"

# One real word per script (the language's own name), used only as Unicode test material.
NATIVE = {lang.code: lang.native_name for lang in languages.REGISTRY}
DIGITS_12 = {
    "Gujr": "૧૨", "Deva": "१२", "Beng": "১২", "Guru": "੧੨", "Orya": "୧୨", "Taml": "௧௨", "Telu": "౧౨",
    "Knda": "೧೨", "Mlym": "൧൨", "Arab": "١٢", "Arab-ext": "۱۲", "Olck": "᱑᱒", "Mtei": "꯱꯲",
}


# ------------------------------------------------------------------------------ registry
def test_registry_is_the_eighth_schedule_plus_english():
    assert len(languages.REGISTRY) == 23 and len(set(languages.CODES)) == 23
    assert sum(1 for l in languages.REGISTRY if l.eighth_schedule) == 22
    assert [l.code for l in languages.REGISTRY if not l.eighth_schedule] == ["en"]
    assert {l.english_name for l in languages.REGISTRY} >= {
        "Assamese", "Bengali", "Bodo", "Dogri", "Gujarati", "Hindi", "Kannada", "Kashmiri", "Konkani",
        "Maithili", "Malayalam", "Manipuri", "Marathi", "Nepali", "Odia", "Punjabi", "Sanskrit",
        "Santali", "Sindhi", "Tamil", "Telugu", "Urdu", "English"}


def test_right_to_left_languages_and_script_codes():
    assert {l.code for l in languages.REGISTRY if l.direction == "rtl"} == {"ur", "sd", "ks"}
    assert {l.script for l in languages.REGISTRY} <= {
        "Beng", "Deva", "Gujr", "Knda", "Arab", "Mlym", "Orya", "Guru", "Olck", "Taml", "Telu", "Latn"}
    for lang in languages.REGISTRY:          # the native name is really written in the declared script
        counts = languages.script_counts(lang.native_name)
        assert max(counts, key=counts.get) == lang.script, lang.code


@pytest.mark.parametrize("script,digits", sorted(DIGITS_12.items()))
def test_digits_of_every_script_are_unified(script, digits):
    assert languages.normalize_digits(f"x {digits} y") == "x 12 y"


@pytest.mark.parametrize("code", languages.CODES)
def test_detection_with_the_selected_language(code):
    result = languages.detect(NATIVE[code] + " " + NATIVE[code], hint=code)
    assert result["language"] == code and result["script"] == languages.get(code).script


def test_detection_without_a_hint_is_honest_about_shared_scripts():
    assert languages.detect("ગુજરાતી પ્રશ્ન")["confidence"] == "high"
    assert languages.detect("தமிழ் கேள்வி")["language"] == "ta"
    deva = languages.detect("यह एक प्रश्न है")
    assert deva["language"] == "hi" and deva["confidence"] == "low" and "mr" in deva["candidates"]
    assert languages.detect("মোৰ প্ৰশ্ন")["language"] == "as"          # ৰ is Assamese-only
    assert languages.detect("هي سنڌي ٻولي آهي")["language"] == "sd"     # ٻ is Sindhi-only
    assert languages.detect("یہ اردو ہے")["language"] == "ur"
    assert languages.detect("12345 ???")["confidence"] == "none"


@pytest.mark.parametrize("code", languages.CODES)
def test_search_tokeniser_keeps_words_of_every_script_whole(code):
    word = NATIVE[code].strip("'")
    assert textsearch.tokens(f"{word} 14")[0] == languages.normalize_text(word).lower()


# ----------------------------------------------------------------------------- catalogues
def test_every_language_has_a_catalogue_with_honest_metadata():
    reference = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))["strings"]
    for code in languages.CODES:
        data = json.loads((LOCALES / f"{code}.json").read_text(encoding="utf-8"))
        meta, strings = data["_meta"], data["strings"]
        assert set(strings) <= set(reference), f"{code}: keys unknown to en.json"
        assert all(isinstance(v, str) and v.strip() and "\ufffd" not in v for v in strings.values())
        if code in ("en", "gu"):
            assert meta["translation_status"] == "PROJECT_AUTHORED"
        else:                               # never presented as human or official translation
            assert meta["translation_status"] == "MACHINE_TRANSLATED" and meta["review"] == "none"
            script = languages.get(code).script
            for value in strings.values():
                counts = languages.script_counts(value)
                assert max(counts, key=counts.get) == script, f"{code}: {value!r} is not in {script}"


def test_static_registry_for_the_frontend_is_up_to_date():
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_locales.py"), "--check"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_frontend_has_no_hard_coded_two_language_toggle():
    app_js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert "var T = {" not in app_js and "langGu" not in app_js
    assert "locales/" in app_js and "root.dir" in app_js


# ------------------------------------------------------------------------------------ API
def test_languages_endpoint_reports_only_what_exists(client):
    data = client.get("/api/v1/languages").json()
    assert data["total"] == 23
    by = {i["code"]: i for i in data["items"]}
    assert set(by["gu"]["statuses"]) == {"UI_READY", "SAMPLE_CONTENT_AVAILABLE", "ASSISTANT_SUPPORTED"}
    assert set(by["en"]["statuses"]) == {"UI_READY", "SAMPLE_CONTENT_AVAILABLE", "ASSISTANT_SUPPORTED"}
    assert by["hi"]["statuses"] == ["UI_READY"] and by["hi"]["ui"]["translation_status"] == "MACHINE_TRANSLATED"
    assert by["sat"]["statuses"] == ["UI_PARTIAL"] and by["sat"]["ui"]["missing_essential"]
    for item in data["items"]:
        assert "HUMAN_VERIFIED" not in item["statuses"]
        assert item["content"]["machine_translated_articles"] == 0
        if item["code"] not in ("gu", "en"):
            assert item["content"]["owner_summaries"] == 0
            assert item["assistant"]["answers_in_language"] is False
    assert client.get("/api/v1/languages/ur").json()["direction"] == "rtl"
    assert client.get("/api/v1/languages/xx").status_code == 404


def test_unsupported_content_language_falls_back_and_says_so(client):
    response = client.get("/api/v1/constitution/articles", params={"language": "hi", "q": "equality"})
    assert response.status_code == 200
    assert response.headers["content-language"] == "en"
    assert response.headers["x-requested-language"] == "hi"
    assert response.headers["x-language-fallback"] == "true"
    plain = client.get("/api/v1/constitution/articles", params={"language": "gu"})
    assert "x-language-fallback" not in plain.headers
    assert client.get("/api/v1/constitution/articles", params={"language": "zz"}).status_code == 422
    assert client.get("/api/v1/ai/glossary", params={"language": "ta"}).status_code == 200


def test_article_text_in_a_language_without_text_is_unavailable_not_translated(client):
    data = client.get("/api/v1/constitution/articles/14/text", params={"lang": "hi"}).json()
    assert data["record"] == data["record"] | {"available": False, "content_status": "UNAVAILABLE", "text": None}
    assert data["fallback"] is None                       # no official text exists in any language
    assert data["explanation"]["is_official_text"] is False and data["explanation"]["language"] == "en"
    assert "Nothing has been translated automatically" in data["notice"]
    assert client.get("/api/v1/constitution/articles/14/text", params={"lang": "zz"}).status_code == 422
    assert client.get("/api/v1/constitution/articles/999/text", params={"lang": "en"}).status_code == 404


@pytest.mark.parametrize("language,question,article", [
    ("hi", "अनुच्छेद २१ क्या है?", "Article 21"),
    ("bn", "অনুচ্ছেদ ১৪ কী?", "Article 14"),
    ("ur", "آرٹیکل ۳۲ کیا ہے؟", "Article 32"),
    ("ta", "உறுப்பு 21A என்றால் என்ன?", "Article 21A"),
    ("mr", "अनुच्छेद 19 काय आहे?", "Article 19"),
])
def test_assistant_finds_the_named_article_in_other_scripts(client, language, question, article):
    data = client.post("/api/v1/ai/explain", json={"question": question, "language": language}).json()
    assert [c["article_label"] for c in data["citations"]] == [article]
    assert data["requested_language"] == language and data["language"] == "en"
    assert data["language_fallback"] is True and "answer_language_fallback" in data["warnings"]
    assert "Nothing was machine-translated" in data["language_notice"]
    assert data["detected_language"]["script"] == languages.get(language).script


@pytest.mark.parametrize("code", languages.CODES)
def test_assistant_accepts_a_question_in_every_language(client, code):
    question = f"{NATIVE[code]} {NATIVE[code]} 300A?"
    response = client.post("/api/v1/ai/explain", json={"question": question, "language": code})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["citations"] == []                         # nothing invented for an unknown query
    assert data["language_fallback"] is (code not in ("gu", "en"))
    assert data["disclaimers"]


def test_assistant_reports_a_missing_article_in_any_language(client):
    data = client.post("/api/v1/ai/explain", json={"question": "अनुच्छेद 300A क्या कहता है?", "language": "hi"}).json()
    assert "Article 300A is not available" in data["answer"] and data["citations"] == []


def test_assistant_rejects_unknown_language_and_keeps_gujarati_unchanged(client):
    assert client.post("/api/v1/ai/explain", json={"question": "What is Article 14?", "language": "zz"}).status_code == 422
    data = client.post("/api/v1/ai/explain", json={"question": "અનુચ્છેદ ૧૪ શું છે?", "language": "gu"}).json()
    assert data["language"] == "gu" and data["language_fallback"] is False and data["language_notice"] is None


def test_locale_files_are_served_and_not_rate_limited(client):
    for _ in range(3):
        for code in languages.CODES:
            response = client.get(f"/locales/{code}.json")
            assert response.status_code == 200 and "strings" in response.json()
    assert len(client.get("/locales/index.json").json()["languages"]) == 23


# ---------------------------------------------------------------------- per-language text
def _body(code: str) -> str:
    name = NATIVE[code]
    return (f"14. {name} PLACEHOLDER heading.\u2014PLACEHOLDER body, not constitutional text. "
            f"{name} {name} {name} synthetic sentence used only by the automated tests.\n")


@pytest.mark.parametrize("code", [c for c in languages.CODES if c not in ("en", "gu")])
def test_text_in_every_language_round_trips_unchanged(isolated_settings, code):
    with get_db(isolated_settings.db_path) as conn:
        report = ingest_service.ingest_text(conn, text=_body(code), source_key=SOURCE, source_file="t.txt",
                                            language=code, dry_run=False, extraction_method="text_layer")
        assert report.articles_written == 1
        row = conn.execute(
            "SELECT t.* FROM article_texts t JOIN constitution_articles a ON a.id = t.article_id"
            " WHERE a.article_no = '14' AND t.language = ?", (code,)).fetchone()
        assert NATIVE[code] in row["body"] and row["title"].startswith(NATIVE[code])
        assert row["content_status"] == "OFFICIAL_SOURCE"
        assert row["verification_status"] == "requires_human_verification"
        legacy = conn.execute("SELECT text_en, text_gu, citizen_explanation_en FROM constitution_articles"
                              " WHERE article_no = '14'").fetchone()
        assert not legacy["text_en"] and not legacy["text_gu"]       # other languages untouched
        assert legacy["citizen_explanation_en"]                        # owner summary preserved
        again = ingest_service.ingest_text(conn, text=_body(code), source_key=SOURCE, source_file="t.txt",
                                           language=code, dry_run=False, extraction_method="text_layer")
        assert again.articles_written == 0 and again.articles_unchanged == 1          # idempotent


def test_ocr_text_is_never_labelled_official_or_verified(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        ingest_service.ingest_text(conn, text=_body("gu"), source_key=SOURCE, source_file="ocr.txt",
                                   language="gu", dry_run=False, extraction_method="ocr", edition="TEST")
        row = conn.execute("SELECT * FROM article_texts WHERE language = 'gu'").fetchone()
        assert row["content_status"] == "OCR_REVIEW_REQUIRED" and row["extraction_method"] == "ocr"
        assert row["verification_status"] == "requires_human_verification" and row["edition"] == "TEST"
        assert conn.execute("SELECT COUNT(*) FROM article_texts WHERE verification_status = 'verified'"
                            " OR content_status IN ('VERIFIED','HUMAN_REVIEWED')").fetchone()[0] == 0


def test_second_language_does_not_overwrite_the_first_language_provenance(isolated_settings):
    english = "14. PLACEHOLDER English heading.\u2014PLACEHOLDER English body, synthetic test sentence only, not law.\n"
    with get_db(isolated_settings.db_path) as conn:
        ingest_service.ingest_text(conn, text=["", "", english], source_key=SOURCE, source_file="en.txt",
                                   language="en", dry_run=False)
        before = dict(conn.execute("SELECT source_locator, source_pages, title_en, text_en FROM"
                                   " constitution_articles WHERE article_no='14'").fetchone())
        ingest_service.ingest_text(conn, text=["", _body("gu").replace("14.", "૧૪.")], source_key=SOURCE,
                                   source_file="gu.txt", language="gu", dry_run=False, extraction_method="ocr")
        after = dict(conn.execute("SELECT source_locator, source_pages, title_en, text_en FROM"
                                  " constitution_articles WHERE article_no='14'").fetchone())
        assert before == after and "en.txt" in after["source_locator"] and after["source_pages"] == "3"
        rows = {r["language"]: r for r in conn.execute(
            "SELECT t.* FROM article_texts t JOIN constitution_articles a ON a.id=t.article_id WHERE a.article_no='14'")}
        assert rows["en"]["source_pages"] == "3" and rows["gu"]["source_pages"] == "2"
        assert "gu.txt" in rows["gu"]["source_locator"]
        # Gujarati digits joined the existing Article 14 instead of creating a second row
        assert conn.execute("SELECT COUNT(*) FROM constitution_articles WHERE article_no IN ('14','૧૪')").fetchone()[0] == 1


def test_multi_letter_suffixes_and_indic_part_headings_are_parsed():
    text = ("PART IXA\nPLACEHOLDER PART TITLE\n243Z. PLACEHOLDER one.\u2014PLACEHOLDER body one, long enough to count.\n"
            "243ZA. PLACEHOLDER two.\u2014PLACEHOLDER body two, long enough to count.\n"
            "ભાગ ૩\n૧૫. PLACEHOLDER three.\u2014PLACEHOLDER body three, long enough to count.\n")
    articles, _ = ingest_service.parse_articles(text)
    assert [(a.article_no, a.part_no) for a in articles] == [("243Z", "IXA"), ("243ZA", "IXA"), ("15", "III")]
    assert "243ZA" not in articles[0].body


def test_broken_text_layer_and_wrong_script_are_blocked(isolated_settings):
    broken = "14. ભારતન ું સુંવિધાન ન ું લખાણ ન ું.\u2014ભારતન ું સુંવિધાન ન ું લખાણ ન ું ન ું ન ું ન ું.\n"
    santali = "14. ᱵᱷᱟᱨᱚᱛ ᱨᱮᱭᱟᱜ.\u2014ᱵᱷᱟᱨᱚᱛ ᱨᱮᱭᱟᱜ ᱥᱚᱝᱣᱤᱫᱷᱟᱱ ᱵᱷᱟᱨᱚᱛ ᱨᱮᱭᱟᱜ ᱥᱚᱝᱣᱤᱫᱷᱟᱱ PLACEHOLDER.\n"
    with get_db(isolated_settings.db_path) as conn:
        r1 = ingest_service.ingest_text(conn, text=broken, source_key=SOURCE, source_file="b.txt", language="gu")
        assert "broken_indic_text_layer" in r1.blocking_reasons and not r1.quality_ok
        r2 = ingest_service.ingest_text(conn, text=santali, source_key=SOURCE, source_file="s.txt", language="gu")
        assert "script_mismatch" in r2.blocking_reasons          # Santali text offered as Gujarati
        clean = "14. ગુજરાતી ગુજરાતી.\u2014" + "ગુજરાતી " * 30 + "\n"
        good = ingest_service.ingest_text(conn, text=clean, source_key=SOURCE, source_file="g.txt", language="gu")
        assert "broken_indic_text_layer" not in good.blocking_reasons and "script_mismatch" not in good.blocking_reasons


def test_unknown_language_method_and_non_official_source_are_refused(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        with pytest.raises(ValueError):
            ingest_service.ingest_text(conn, text=_body("hi"), source_key=SOURCE, source_file="x", language="zz")
        with pytest.raises(ValueError):
            ingest_service.ingest_text(conn, text=_body("hi"), source_key=SOURCE, source_file="x", language="hi",
                                       extraction_method="guess")
        owner = conn.execute("SELECT source_key FROM legal_sources WHERE source_type <> 'official' LIMIT 1").fetchone()
        with pytest.raises(ValueError, match="not 'official'"):
            ingest_service.ingest_text(conn, text=_body("hi"), source_key=owner["source_key"], source_file="x",
                                       language="hi", dry_run=False)


def test_imported_language_becomes_visible_everywhere_with_its_label(isolated_settings):
    from backend.app.main import create_app

    with get_db(isolated_settings.db_path) as conn:
        ingest_service.ingest_text(conn, text=_body("hi"), source_key=SOURCE, source_file="hi.txt",
                                   language="hi", dry_run=False, extraction_method="ocr")
    from backend.app.deps import db_dependency, settings_dependency

    def _db():
        with get_db(isolated_settings.db_path) as conn:
            yield conn

    app = create_app(isolated_settings)
    app.dependency_overrides[db_dependency] = _db
    app.dependency_overrides[settings_dependency] = lambda: isolated_settings
    with TestClient(app) as client:
        text = client.get("/api/v1/constitution/articles/14/text", params={"lang": "hi"}).json()
        assert text["record"]["available"] and text["record"]["content_status"] == "OCR_REVIEW_REQUIRED"
        assert NATIVE["hi"] in text["record"]["text"] and text["available_text_languages"] == ["hi"]
        other = client.get("/api/v1/constitution/articles/14/text", params={"lang": "ta"}).json()
        assert other["record"]["content_status"] == "UNAVAILABLE" and other["fallback"] is None
        assert other["available_text_languages"] == ["hi"]      # offered, never substituted silently
        detail = client.get("/api/v1/constitution/articles/14").json()
        assert detail["language_texts"][0]["language"] == "hi" and not detail["text_en"]
        found = client.get("/api/v1/library", params={"q": NATIVE["hi"], "language": "hi"}).json()
        assert found["total"] == 1 and found["items"][0]["content_language"] == "hi"
        assert found["items"][0]["content_status"] == "OCR_REVIEW_REQUIRED" and found["matched_terms"]
        only = client.get("/api/v1/library", params={"content_language": "hi"}).json()
        assert only["total"] == 1
        assert client.get("/api/v1/library", params={"content_language": "ta"}).json()["total"] == 0
        by = {i["code"]: i for i in client.get("/api/v1/languages").json()["items"]}
        assert by["hi"]["content"]["ocr_review_required_articles"] == 1
        assert "OFFICIAL_TEXT_AVAILABLE" not in by["hi"]["statuses"]       # OCR is not official text
        assert "HUMAN_VERIFIED" not in by["hi"]["statuses"]


def test_migration_005_is_reversible_and_leaves_existing_data_alone(isolated_settings):
    down = (ROOT / "backend" / "migrations" / "005_article_texts.down.sql").read_text(encoding="utf-8")
    with get_db(isolated_settings.db_path) as conn:
        before = conn.execute("SELECT COUNT(*) FROM constitution_articles").fetchone()[0]
        assert conn.execute("SELECT COUNT(*) FROM article_texts").fetchone()[0] == 0
        conn.executescript(down)
        assert conn.execute("SELECT name FROM sqlite_master WHERE name='article_texts'").fetchone() is None
        assert conn.execute("SELECT COUNT(*) FROM constitution_articles").fetchone()[0] == before == 9
