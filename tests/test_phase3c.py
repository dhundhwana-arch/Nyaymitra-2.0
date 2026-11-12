"""Phase 3C tests. All fixtures are SYNTHETIC placeholder text - not constitutional content."""
import hashlib
import json
import sqlite3
import unicodedata

import pymupdf
import pytest

from ingestion import VERIFICATION_STATUS, ingest, pipeline
from ingestion.acquire import AcquisitionError, acquire_all, download, sha256_file, verify_checksums
from ingestion.extract import extract_articles
from ingestion.pdfio import ExtractionError, page_texts, pdf_metadata
from ingestion.quality import compare_numbering, coverage_report, text_quality

EN_PAGES = [
    "CONTENTS\n1. Alpha heading\n2. Beta heading\n3. Gamma heading\n",
    "1. Alpha heading.\u2014Placeholder body one.\n(2) more text\n"
    "1. Subs. by the Placeholder Act, s. 2.\u2014note\n"
    "2. Beta heading.\u2014Placeholder body two.\n",
    "1[2A. Inserted heading.\u2014Placeholder body.\n3. Gamma heading.\u2014Placeholder body three.\n",
]
# Deliberately contains conjuncts, matras, ZWJ/ZWNJ and Gujarati digits.
GU_BODY = "કાયદા સમક્ષ સમાનતા શ્રી ક્ષ જ્ઞ ર\u200dય ક\u200cષ ૧૨૩"
GU_PAGES = [
    f"૧. નમૂનો મથાળું.\u2014{GU_BODY}\n૨. બીજું મથાળું.\u2014નમૂનો લખાણ\n",
    "૨ક. ઉમેરેલું મથાળું.\u2014નમૂનો લખાણ\n૩. ત્રીજું મથાળું.\u2014નમૂનો લખાણ\n",
]


def make_pdf(path, pages=("Synthetic page one", "Synthetic page two", "Synthetic page three")):
    doc = pymupdf.open()
    for text in pages:
        doc.new_page().insert_text((72, 72), text)
    doc.set_metadata({"title": "Synthetic Test Document", "author": "pytest"})
    doc.save(str(path))
    doc.close()
    return path


def fake_fetch_from(src):
    def fetch(url, dest):
        dest.write_bytes(src.read_bytes())
        return {"http_status": 200, "final_url": url}
    return fetch


def one_source(tmp_path, lang="en"):
    return {f"constitution-{lang}": {
        "language": lang, "publisher": "test", "url": "https://example.invalid/x.pdf",
        "local_path": f"raw/{lang}.pdf", "claimed_edition": "test",
        "claimed_amendments_incorporated": "test"}}


# ---------- PDF metadata ----------
def test_pdf_metadata_page_count_and_fields(tmp_path):
    meta = pdf_metadata(make_pdf(tmp_path / "a.pdf"))
    assert meta["page_count"] == 3
    assert meta["metadata"]["title"] == "Synthetic Test Document"
    assert page_texts(tmp_path / "a.pdf")[1].strip() == "Synthetic page two"


def test_manifest_records_metadata_on_success(tmp_path):
    src = make_pdf(tmp_path / "src.pdf")
    m = acquire_all(manifest_path=tmp_path / "m.json", root=tmp_path,
                    fetch=fake_fetch_from(src), sources=one_source(tmp_path))
    e = m["sources"]["constitution-en"]
    assert e["acquired"] and e["page_count"] == 3 and e["retrieved_at"]
    assert e["sha256"] == hashlib.sha256(src.read_bytes()).hexdigest()
    assert e["claims_verified_against_document"] is False
    assert json.loads((tmp_path / "m.json").read_text())["sources"]["constitution-en"]["url"]


# ---------- checksum integrity ----------
def test_checksum_matches_hashlib_and_detects_tampering(tmp_path):
    src = make_pdf(tmp_path / "src.pdf")
    m = acquire_all(manifest_path=tmp_path / "m.json", root=tmp_path,
                    fetch=fake_fetch_from(src), sources=one_source(tmp_path))
    assert verify_checksums(m, tmp_path)["constitution-en"]["ok"]
    with open(tmp_path / "raw/en.pdf", "ab") as f:
        f.write(b"tampered")
    res = verify_checksums(m, tmp_path)["constitution-en"]
    assert not res["ok"] and "mismatch" in res["reason"]
    assert sha256_file(src) == hashlib.sha256(src.read_bytes()).hexdigest()


def test_failed_download_preserves_existing_file_and_records_error(tmp_path):
    dest = tmp_path / "raw/en.pdf"
    dest.parent.mkdir()
    dest.write_bytes(b"%PDF-existing-user-file")

    def boom(url, tmp):
        tmp.write_bytes(b"partial")
        raise OSError("connection reset")

    m = acquire_all(manifest_path=tmp_path / "m.json", root=tmp_path, fetch=boom, sources=one_source(tmp_path))
    e = m["sources"]["constitution-en"]
    assert dest.read_bytes() == b"%PDF-existing-user-file"
    assert not (tmp_path / "raw/en.pdf.part").exists()
    assert e["last_attempt_status"] == "failed" and "connection reset" in e["last_attempt_error"]
    assert e["acquired"] is False and e["sha256"] is None and e["existing_file_preserved"] is True


def test_non_pdf_response_rejected(tmp_path):
    def html(url, tmp):
        tmp.write_bytes(b"<html>Access Denied</html>")
        return {}
    with pytest.raises(AcquisitionError, match="not a PDF"):
        download("https://example.invalid", tmp_path / "x.pdf", fetch=html)
    assert not (tmp_path / "x.pdf").exists()


# ---------- extraction errors ----------
def test_extraction_errors(tmp_path):
    with pytest.raises(ExtractionError, match="not found"):
        page_texts(tmp_path / "missing.pdf")
    (tmp_path / "empty.pdf").write_bytes(b"")
    with pytest.raises(ExtractionError, match="empty"):
        pdf_metadata(tmp_path / "empty.pdf")
    (tmp_path / "bad.pdf").write_bytes(b"%PDF-1.7\nthis is not really a pdf")
    with pytest.raises(ExtractionError):
        page_texts(tmp_path / "bad.pdf")


def test_truncated_download_is_rejected_and_not_installed(tmp_path):
    def trunc(url, tmp):
        tmp.write_bytes(b"%PDF-1.7\ngarbage")
        return {}
    with pytest.raises(AcquisitionError, match="cannot be opened"):
        download("https://example.invalid", tmp_path / "x.pdf", fetch=trunc)
    assert not (tmp_path / "x.pdf").exists()


# ---------- article extraction ----------
def test_english_extraction_skips_contents_and_footnotes():
    res = extract_articles(EN_PAGES, "en")
    assert [a.label_raw for a in res["articles"]] == ["1", "2", "2A", "3"]
    assert res["articles"][0].title_raw == "Alpha heading"
    assert res["articles"][0].page_start == 2
    reasons = {r["reason"] for r in res["rejected"]}
    assert any("footnote" in r for r in reasons) and any("separator" in r for r in reasons)


def test_duplicates_missing_and_order_are_reported_not_fixed():
    pages = ["1. A.\u2014x\n3. C.\u2014x\n3. C again.\u2014y\n2. B.\u2014late\n"]
    arts = extract_articles(pages, "en")["articles"]
    assert len(arts) == 4  # nothing dropped or merged
    cov = coverage_report(arts, "en")
    assert cov["duplicates"][0]["label_raw"] == "3" and cov["duplicates"][0]["count"] == 2
    assert 4 in cov["missing_base_numbers"] and 2 not in cov["missing_base_numbers"]
    assert cov["out_of_order"] == [{"label_raw": "2", "page": 1}]


# ---------- Gujarati Unicode preservation ----------
def test_gujarati_text_preserved_codepoint_for_codepoint():
    arts = extract_articles(GU_PAGES, "gu")["articles"]
    assert [a.label_raw for a in arts] == ["૧", "૨", "૨ક", "૩"]   # digits/suffix NOT transliterated
    assert [a.base_no for a in arts] == [1, 2, 2, 3]
    assert GU_BODY in arts[0].text_raw
    assert "\u200d" in arts[0].text_raw and "\u200c" in arts[0].text_raw
    assert "\n".join(a.text_raw for a in arts) == "\n".join(GU_PAGES)  # lossless, in order


def test_no_unicode_normalisation_applied():
    decomposed = "કો"  # KA + AA + E-matra sequence that NFC would not compose identically
    raw = "૧. મથાળું.\u2014e\u0301 " + decomposed + "\n"
    art = extract_articles([raw], "gu")["articles"][0]
    assert "e\u0301" in art.text_raw
    assert art.text_raw != unicodedata.normalize("NFC", art.text_raw)


def test_gujarati_roundtrip_through_database_and_json(tmp_path):
    arts = extract_articles(GU_PAGES, "gu")["articles"]
    db = tmp_path / "t.db"
    ingest.apply(db, {"constitution-gu": ("sha", arts)}, {"g": {"passed": True}})
    rows = sqlite3.connect(db).execute(
        f"SELECT article_label_raw, text_raw, verification_status FROM {ingest.TABLE} ORDER BY id").fetchall()
    assert [r[0] for r in rows] == [a.label_raw for a in arts]
    assert [r[1] for r in rows] == [a.text_raw for a in arts]
    assert json.loads(json.dumps(arts[0].to_dict(), ensure_ascii=False))["text_raw"] == arts[0].text_raw


def test_gujarati_quality_flags_legacy_font_and_scans():
    assert text_quality(GU_PAGES, "gu")["passed"]
    legacy = text_quality(["Ûkhíkçkwt çktÄkhý yLku fkÞËku " * 20], "gu")  # legacy-font style mojibake
    assert not legacy["passed"] and "Gujarati Unicode" in legacy["failures"][0]
    assert not text_quality(["", "", ""], "gu")["passed"]            # image-only scan
    assert not text_quality(["ક\ufffd\ufffdખ\ue000" * 50], "gu")["passed"]


# ---------- cross-language comparison ----------
def test_numbering_comparison_reports_without_mapping():
    en = extract_articles(EN_PAGES + ["4. Delta.\u2014x\n"], "en")["articles"]
    gu = extract_articles(GU_PAGES, "gu")["articles"]
    cmp_ = compare_numbering(en, gu)
    assert cmp_["plain_only_in_en"] == [4] and cmp_["plain_only_in_gu"] == []
    amb = cmp_["suffixed_articles_needing_human_mapping"]
    assert amb == [{"base_no": 2, "en_labels": ["2A"], "gu_labels": ["૨ક"],
                    "status": "count_matches_mapping_unconfirmed", "note": amb[0]["note"]}]
    assert [a.label_raw for a in gu] == ["૧", "૨", "૨ક", "૩"]  # inputs untouched


# ---------- gated ingestion ----------
def test_apply_refused_when_any_gate_fails(tmp_path):
    db = tmp_path / "t.db"
    arts = extract_articles(EN_PAGES, "en")["articles"]
    with pytest.raises(ingest.GateError):
        ingest.apply(db, {"constitution-en": ("sha", arts)},
                     {"ok": {"passed": True}, "bad": {"passed": False}})
    assert not db.exists()


def test_dry_run_writes_nothing_and_seed_table_is_untouched(tmp_path):
    db = tmp_path / "t.db"
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE constitution_articles (id INTEGER PRIMARY KEY, article_no TEXT, description_en TEXT)")
    c.execute("INSERT INTO constitution_articles VALUES (1, 'Article 14', 'seed summary')")
    c.commit(); c.close()
    before = db.read_bytes()
    arts = extract_articles(EN_PAGES, "en")["articles"]
    batches = {"constitution-en": ("sha", arts)}
    p = ingest.plan(db, batches)
    assert p["sources"]["constitution-en"]["would_insert"] == 4 and p["rows_written"] == 0
    assert db.read_bytes() == before

    ingest.apply(db, batches, {"g": {"passed": True}})
    ingest.apply(db, batches, {"g": {"passed": True}})  # idempotent
    c = sqlite3.connect(db)
    assert c.execute("SELECT * FROM constitution_articles").fetchall() == [(1, "Article 14", "seed summary")]
    assert c.execute(f"SELECT count(*), count(DISTINCT verification_status), min(verification_status),"
                     f" count(verified_by) FROM {ingest.TABLE}").fetchone() == (4, 1, VERIFICATION_STATUS, 0)
    assert ingest.plan(db, batches)["sources"]["constitution-en"]["already_present"] == 4


def test_pipeline_end_to_end_stays_dry_and_refuses_apply(tmp_path):
    src = make_pdf(tmp_path / "src.pdf", pages=["1. Alpha.\u2014body", "2. Beta.\u2014body"])
    acquire_all(manifest_path=tmp_path / "m.json", root=tmp_path,
                fetch=fake_fetch_from(src), sources=one_source(tmp_path))
    kw = dict(root=tmp_path, manifest_path=tmp_path / "m.json", report_dir=tmp_path / "rep",
              db_path=tmp_path / "t.db", exceptions_path=tmp_path / "none.json")
    rep = pipeline.run(**kw)
    assert rep["gates"]["constitution-en:checksum"]["passed"]
    assert not rep["gates"]["constitution-en:coverage"]["passed"]      # 393 numbers missing
    assert rep["import"]["mode"] == "dry-run" and not (tmp_path / "t.db").exists()
    rep = pipeline.run(apply=True, **kw)
    assert rep["import"]["status"] == "REFUSED" and not (tmp_path / "t.db").exists()
    assert rep["numbering_comparison"]["status"] == "not_run"


def test_unsigned_exceptions_file_rejected(tmp_path):
    p = tmp_path / "ex.json"
    p.write_text(json.dumps({"accepted_missing_base_numbers": {"en": [238]}}))
    with pytest.raises(ValueError, match="reviewed_by"):
        pipeline._load_exceptions(p)
