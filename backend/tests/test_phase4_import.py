"""Phase 4: structured import, diglot separation, OCR checks, rollback, locale audit."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from backend.app.db import apply_migrations, connect, rollback_migrations, transaction
from backend.app.services import diglot, ingest
from backend.app.services import structured_import as si

ROOT = Path(__file__).resolve().parents[2]
EN_14 = "The State shall not deny to any person equality before the law within the territory (sample test sentence)."
EN_21A = "The State shall provide education to all children in such manner as it may determine (sample test sentence)."
GU_A = "આ એક નમૂનાનું ગુજરાતી વાક્ય છે જે માત્ર પરીક્ષણ માટે લખવામાં આવ્યું છે અને કાયદાનું લખાણ નથી."
GU_B = "બીજું નમૂનાનું વાક્ય પણ માત્ર પરીક્ષણ માટે છે અને તેમાં કોઈ કાયદાકીય લખાણ નથી તે ધ્યાનમાં રાખો."
HI = "यह केवल परीक्षण के लिए लिखा गया एक नमूना हिंदी वाक्य है और यह कानून का पाठ नहीं है।"
SOURCE = "india-code-constitution"


@pytest.fixture()
def db(isolated_settings):
    """A throw-away seeded database; the shared test database is never written to."""
    from backend.app.db import get_db

    with get_db(isolated_settings.db_path) as conn:
        yield conn


def run(tmp_path, name, content, language, method="text_layer", mapping=None, accept=False, normalize=False, conn=None, expected=None):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    loaded = si.read_records(path)
    m = si.infer_mapping(loaded, language, mapping, accept)
    if m["status"] != "ok":
        return path, loaded, m, None, None
    records, skipped = si.build_records(loaded, m, language, method, normalize=normalize)
    report = si.quality_report(path=path, loaded=loaded, mapping=m, records=records, skipped=skipped, language=language,
                               extraction_method=method, source_key=SOURCE, expected=expected,
                               existing=si.existing_texts(conn, language) if conn is not None else {})
    return path, loaded, m, records, report


def do_apply(db, records, report, language, method="text_layer", **kw):
    return si.apply(db, records, report, language=language, source_key=SOURCE, source_file="t", extraction_method=method, **kw)


# ---------------------------------------------------------------- formats and mapping
def test_csv_with_recognisable_headers(tmp_path, db):
    csv = f'Article No,Part,Chapter,Heading,Content,Page\n14,III,,Equality,"{EN_14}",45\n21A,III,,Education,"{EN_21A}",52\n'
    _, _, m, records, report = run(tmp_path, "a.csv", csv, "en", conn=db)
    assert m["status"] == "ok" and m["fields"]["text"]["column"] == "Content"
    assert [r.article_no for r in records] == ["14", "21A"] and records[0].part_no == "III"
    assert report["totals"]["import_ready"] == 2 and report["ready_to_apply"]
    result = do_apply(db, records, report, "en", edition="test edition")
    row = db.execute("SELECT t.* FROM article_texts t JOIN constitution_articles a ON a.id = t.article_id"
                     " WHERE a.article_no = '21A' AND t.language = 'en'").fetchone()
    assert row["body"] == EN_21A and row["source_pages"] == "52" and row["edition"] == "test edition"
    assert row["extraction_method"] == "text_layer" and row["verification_status"] == "requires_human_verification"
    assert row["content_status"] != "VERIFIED" and "record 2" in row["source_locator"]
    assert result["run_id"] > 0


def test_json_nested_bilingual_and_language_isolation(tmp_path, db):
    data = {"meta": {"x": 1}, "articles": [
        {"article_no": "14", "part_no": "III", "text": {"en": EN_14, "gu": GU_A}, "pages": "45"},
        {"article_no": "243ZA", "part_no": "IXA", "text": {"en": EN_21A}, "pages": "120-121"}]}
    _, _, m, records, report = run(tmp_path, "a.json", json.dumps(data, ensure_ascii=False), "gu", method="ocr", conn=db)
    assert m["status"] == "ok"
    ready = [r for r in records if not r.rejected]
    assert [r.article_no for r in ready] == ["14"] and ready[0].text == GU_A
    do_apply(db, records, {**report, "ready_to_apply": True, "blocking_reasons": []}, "gu", method="ocr")
    rows = db.execute("SELECT t.language, t.content_status FROM article_texts t JOIN constitution_articles a"
                      " ON a.id = t.article_id WHERE a.article_no = '14'").fetchall()
    assert [(r["language"], r["content_status"]) for r in rows] == [("gu", "OCR_REVIEW_REQUIRED")]
    # English side of the same file imports independently and leaves Gujarati untouched
    _, _, _, rec_en, rep_en = run(tmp_path, "a.json", json.dumps(data, ensure_ascii=False), "en", conn=db)
    assert sorted(r.article_no for r in rec_en if not r.rejected) == ["14", "243ZA"]
    do_apply(db, rec_en, rep_en, "en")
    gu = db.execute("SELECT body FROM article_texts t JOIN constitution_articles a ON a.id = t.article_id"
                    " WHERE a.article_no='14' AND language='gu'").fetchone()
    assert gu["body"] == GU_A


def test_json_object_keyed_by_article_number(tmp_path):
    _, _, m, records, _ = run(tmp_path, "k.json", json.dumps({"14": EN_14, "21A": EN_21A}), "en")
    assert m["status"] == "ok" and [r.article_no for r in records] == ["14", "21A"]


def test_jsonl_and_tsv(tmp_path):
    jsonl = "\n".join(json.dumps(x) for x in [{"article": "14", "body": EN_14}, {"article": "21A", "body": EN_21A}])
    assert [r.article_no for r in run(tmp_path, "a.jsonl", jsonl, "en")[3]] == ["14", "21A"]
    tsv = f"article_no\ttext\n14\t{EN_14}\n"
    assert run(tmp_path, "a.tsv", tsv, "en")[3][0].text == EN_14


def test_folder_of_article_files(tmp_path):
    folder = tmp_path / "arts"
    folder.mkdir()
    (folder / "article_014.txt").write_text(EN_14, encoding="utf-8")
    (folder / "article_21A.txt").write_text(EN_21A, encoding="utf-8")
    loaded = si.read_records(folder)
    m = si.infer_mapping(loaded, "en")
    assert m["status"] == "ok"
    records, _ = si.build_records(loaded, m, "en", "ocr")
    assert sorted(r.article_no for r in records) == ["14", "21A"]


def test_unrecognisable_headers_give_mapping_report_not_a_guess(tmp_path):
    csv = f'c1,c2,c3\n14,"{EN_14}",45\n21A,"{EN_21A}",52\n'
    _, _, m, records, _ = run(tmp_path, "x.csv", csv, "en")
    assert m["status"] == "needs_mapping" and records is None
    assert "mapping_template" in m and m["column_profiles"] and m["inferred_from_content"]
    # explicit mapping resolves it
    _, _, m2, records, _ = run(tmp_path, "x.csv", csv, "en", mapping={"article_no": "c1", "text": "c2", "pages": "c3"})
    assert m2["status"] == "ok" and records[1].article_no == "21A" and records[1].pages == "52"


def test_mapping_to_missing_column_is_an_error(tmp_path):
    with pytest.raises(ValueError):
        run(tmp_path, "x.csv", f'a,b\n14,"{EN_14}"\n', "en", mapping={"article_no": "a", "text": "nope"})


# ---------------------------------------------------------------- numbers, parts
@pytest.mark.parametrize("value,expected", [
    ("14", "14"), ("૧૪", "14"), ("૨૧A", "21A"), ("२४३", "243"), ("243ZA", "243ZA"), ("243-za", "243ZA"),
    ("Article 21A", "21A"), ("અનુચ્છેદ ૩૨", "32"), ("021", "21"), ("14.", "14"), ("Preamble", "Preamble"), ("આમુખ", "Preamble"),
])
def test_article_numbers(value, expected):
    assert si.parse_article_no(value) == (expected, None)


@pytest.mark.parametrize("value", ["", "abc", "0", "999", "14 and 15", "21ABC"])
def test_bad_article_numbers(value):
    number, problem = si.parse_article_no(value)
    assert number is None and problem in ("missing_article_number", "invalid_article_number")


def test_gujarati_numerals_in_csv_and_part_chapter(tmp_path, db):
    csv = f'અનુચ્છેદ,ભાગ,પ્રકરણ,લખાણ,પાનું\n૧૪,૩,સામાન્ય,"{GU_A}",૬૧\n૨૧,ભાગ ૩,,"{GU_B}",૬૨-૬૩\n'
    _, _, m, records, report = run(tmp_path, "g.csv", csv, "gu", method="ocr", conn=db)
    assert m["status"] == "ok", m
    assert [(r.article_no, r.part_no, r.pages) for r in records] == [("14", "III", "61"), ("21", "III", "62-63")]
    assert records[0].chapter == "સામાન્ય" and report["parts"] == {"III": 2}
    do_apply(db, records, report, "gu", method="ocr")
    art = db.execute("SELECT part_no FROM constitution_articles WHERE article_no='21'").fetchone()
    assert art["part_no"] == "III"


def test_missing_articles_and_expected_list(tmp_path):
    csv = "article_no,text\n" + "".join(f'{n},"{EN_14} {n}"\n' for n in (1, 2, 4, 7))
    report = run(tmp_path, "m.csv", csv, "en", expected=["1", "2", "3", "4", "5A"])[4]
    assert report["numbering"]["gaps_in_sequence"] == ["3", "5", "6"]
    assert report["numbering"]["expected_list"]["missing"] == ["3", "5A"]
    assert report["numbering"]["expected_list"]["not_expected"] == ["7"]
    assert "not proof" in report["numbering"]["gaps_note"]
    text = si.render_markdown(report)
    assert "395" not in text and "470" not in text


# ---------------------------------------------------------------- language purity
def test_hindi_in_english_record_is_rejected(tmp_path):
    csv = f'article_no,text\n14,"{EN_14}"\n15,"{EN_14} {HI}"\n16,"{HI}"\n17,"{EN_21A} कानून"\n'
    records = run(tmp_path, "h.csv", csv, "en")[3]
    assert [r.rejected for r in records] == [None, "mixed_language_content", "wrong_script", "mixed_language_content"]


def test_english_row_in_gujarati_import_is_rejected(tmp_path):
    csv = f'article_no,text\n14,"{GU_A}"\n15,"{EN_14}"\n'
    assert [r.rejected for r in run(tmp_path, "h.csv", csv, "gu", method="ocr")[3]] == [None, "wrong_script"]


# ---------------------------------------------------------------- OCR
BROKEN = "ભારતન ું સુંવિધાન અન ે કાયદાન ું લખાણ અહી ં નમૂના માટ ે લખ્ ય ું છ ે જ ે માત્ર પરીક્ષણ છે"


def test_ocr_observations_and_grades():
    clean = si.ocr_observations(GU_A, "Gujr")
    assert clean["grade"] == "clean" and clean["detached_vowel_signs"] == 0
    bad = si.ocr_observations(BROKEN, "Gujr")
    assert bad["detached_vowel_signs"] >= 5 and bad["grade"] in ("poor", "unusable")


def test_normalisation_is_separate_and_original_is_preserved(tmp_path, db):
    mild = GU_A + " " + GU_B + " " + GU_A.replace("નમૂનાનું", "નમૂનાન ું")
    csv = f'article_no,text\n14,"{mild}"\n'
    _, _, _, records, report = run(tmp_path, "o.csv", csv, "gu", method="ocr", normalize=True, conn=db)
    r = records[0]
    assert r.rejected is None and r.text == mild and r.normalized != mild and "નમૂનાનું" in r.normalized
    assert r.normalization and report["ocr_quality"]["normalised_copies_prepared"] == 1
    do_apply(db, records, report, "gu", method="ocr")
    row = db.execute("SELECT body, body_normalized, normalization_json, content_status FROM article_texts"
                     " WHERE language='gu' AND body_normalized IS NOT NULL").fetchone()
    assert row["body"] == mild and row["body_normalized"] == r.normalized
    assert json.loads(row["normalization_json"]) and row["content_status"] == "OCR_REVIEW_REQUIRED"


def test_no_normalised_copy_unless_requested(tmp_path):
    r = run(tmp_path, "o.csv", f'article_no,text\n14,"{GU_A} નમૂનાન ું {GU_B}"\n', "gu", method="ocr")[3][0]
    assert r.normalized is None


def test_damaged_text_must_be_declared_as_ocr(tmp_path):
    csv = f'article_no,text\n14,"{BROKEN}"\n'
    assert run(tmp_path, "o.csv", csv, "gu", method="text_layer")[3][0].rejected in ("damaged_text_not_declared_as_ocr", "ocr_unusable")


def test_file_cannot_declare_itself_verified(tmp_path, db):
    csv = f'article_no,text,verification_status\n14,"{EN_14}",verified\n'
    _, _, _, records, report = run(tmp_path, "v.csv", csv, "en", conn=db)
    assert "claimed_verified_ignored" in records[0].warnings
    do_apply(db, records, report, "en")
    row = db.execute("SELECT verification_status, content_status FROM article_texts WHERE language='en'").fetchone()
    assert row["verification_status"] == "requires_human_verification" and row["content_status"] not in ("VERIFIED", "HUMAN_REVIEWED")


# ---------------------------------------------------------------- duplicates, idempotency, rollback
def test_duplicates(tmp_path):
    csv = f'article_no,text\n14,"{EN_14}"\n14,"{EN_14}"\n15,"{EN_14}"\n15,"{EN_21A}"\n16,"{EN_21A}"\n'
    _, _, _, records, report = run(tmp_path, "d.csv", csv, "en")
    assert [r.rejected for r in records] == [None, "duplicate_identical", "duplicate_conflicting_text",
                                             "duplicate_conflicting_text", None]
    assert "conflicting_duplicates" in report["blocking_reasons"] and not report["ready_to_apply"]
    with pytest.raises(ValueError):
        si.apply(None, records, report, language="en", source_key=SOURCE, source_file="d", extraction_method="text_layer")


def test_idempotent_and_no_overwrite_without_flag(tmp_path, db):
    csv = f'article_no,text\n14,"{EN_14}"\n'
    _, _, _, records, report = run(tmp_path, "i.csv", csv, "en", conn=db)
    first = do_apply(db, records, report, "en")
    _, _, _, records, report = run(tmp_path, "i.csv", csv, "en", conn=db)
    assert report["database"]["already_stored_identical"] == 1
    second = do_apply(db, records, report, "en")
    assert first["articles_written"] == 1 and second["articles_written"] == 0
    assert db.execute("SELECT COUNT(*) FROM article_texts WHERE language='en'").fetchone()[0] == 1
    changed = f'article_no,text\n14,"{EN_21A}"\n'
    _, _, _, records, report = run(tmp_path, "i2.csv", changed, "en", conn=db)
    assert report["database"]["stored_with_different_text"] == ["14"]
    do_apply(db, records, report, "en")
    assert db.execute("SELECT body FROM article_texts WHERE language='en'").fetchone()[0] == EN_14
    do_apply(db, records, report, "en", replace_existing=True)
    assert db.execute("SELECT body FROM article_texts WHERE language='en'").fetchone()[0] == EN_21A


def test_summaries_are_never_overwritten(tmp_path, db):
    before = dict(db.execute("SELECT * FROM constitution_articles WHERE article_no='14'").fetchone())
    csv = f'article_no,title,text\n14,Different title,"{EN_14}"\n'
    _, _, _, records, report = run(tmp_path, "s.csv", csv, "en", conn=db)
    do_apply(db, records, report, "en", replace_existing=True)
    after = dict(db.execute("SELECT * FROM constitution_articles WHERE article_no='14'").fetchone())
    for column in before:
        if "summary" in column or "explanation" in column:
            assert after[column] == before[column], column


def test_rollback_restores_previous_state(tmp_path, db):
    articles_before = db.execute("SELECT COUNT(*) FROM constitution_articles").fetchone()[0]
    _, _, _, records, report = run(tmp_path, "r1.csv", f'article_no,text\n14,"{EN_14}"\n', "en", conn=db)
    run1 = do_apply(db, records, report, "en")["run_id"]
    csv2 = f'article_no,text\n14,"{EN_21A}"\n300,"{EN_14}"\n'
    _, _, _, records, report = run(tmp_path, "r2.csv", csv2, "en", conn=db)
    run2 = do_apply(db, records, report, "en", replace_existing=True)["run_id"]
    assert db.execute("SELECT COUNT(*) FROM constitution_articles").fetchone()[0] == articles_before + 1
    with transaction(db):
        result = ingest.rollback_run(db, run2)
    assert not result["conflicts"]
    assert db.execute("SELECT body FROM article_texts WHERE language='en'").fetchall()[0][0] == EN_14
    assert db.execute("SELECT COUNT(*) FROM constitution_articles").fetchone()[0] == articles_before
    assert db.execute("SELECT status FROM ingest_runs WHERE id=?", (run2,)).fetchone()[0] == "rolled_back"
    with transaction(db):
        ingest.rollback_run(db, run1)
    assert db.execute("SELECT COUNT(*) FROM article_texts WHERE language='en'").fetchone()[0] == 0
    with pytest.raises(ValueError):
        ingest.rollback_run(db, run1)


def test_rollback_reports_conflict_when_text_changed_later(tmp_path, db):
    _, _, _, records, report = run(tmp_path, "c.csv", f'article_no,text\n14,"{EN_14}"\n', "en", conn=db)
    run_id = do_apply(db, records, report, "en")["run_id"]
    db.execute("UPDATE article_texts SET body = 'edited by a reviewer', content_sha256 = 'x' WHERE language='en'")
    with transaction(db):
        result = ingest.rollback_run(db, run_id)
    assert len(result["conflicts"]) == 1
    assert db.execute("SELECT body FROM article_texts WHERE language='en'").fetchone()[0] == "edited by a reviewer"


def test_failed_apply_leaves_nothing(tmp_path, db):
    _, _, _, records, report = run(tmp_path, "f.csv", f'article_no,text\n14,"{EN_14}"\n', "en", conn=db)
    runs = db.execute("SELECT COUNT(*) FROM ingest_runs").fetchone()[0]
    with pytest.raises(Exception):
        si.apply(db, records, report, language="en", source_key="no-such-source", source_file="f", extraction_method="text_layer")
    assert db.execute("SELECT COUNT(*) FROM article_texts").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM ingest_runs").fetchone()[0] == runs


def test_quarantined_and_template_data_are_refused(tmp_path):
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "x.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        si.read_records(legacy / "x.json")
    with pytest.raises(ValueError):
        si.read_records(ROOT / "data" / "legacy")
    for name, lang in (("articles_template.csv", "en"), ("articles_template.json", "en"), ("articles_template.csv", "gu")):
        path = ROOT / "data" / "templates" / name
        loaded = si.read_records(path)
        m = si.infer_mapping(loaded, lang)
        assert m["status"] == "ok", (name, m.get("reasons"))
        records, _ = si.build_records(loaded, m, lang, None)
        assert records and all(r.rejected == "template_placeholder" for r in records)


def test_report_has_every_dashboard_field(tmp_path):
    csv = f'article_no,part,text,page\n14,III,"{EN_14}",45\n,III,"{EN_14}",46\n21A,III,"{EN_21A}",\n'
    report = run(tmp_path, "q.csv", csv, "en")[4]
    assert report["totals"]["records_discovered"] == 3 and report["totals"]["rejected"] == 1
    assert report["rejections"]["by_reason"] == {"missing_article_number": 1}
    assert report["coverage"]["with_page_reference"] == 1
    for key in ("totals", "numbering", "parts", "ocr_quality", "coverage", "rejections", "blocking_reasons", "file", "mapping"):
        assert key in report
    assert "more_than_20_percent_rejected" in report["blocking_reasons"]
    assert "Rejected" in si.render_markdown(report)


# ---------------------------------------------------------------- diglot
def words(text, x, y, width=6.0):
    out = []
    for i, token in enumerate(text.split()):
        out.append((x + i * 30, y, x + i * 30 + width * 4, y + 10, token))
    return out


def two_columns(wanted_left=False, lines=12):
    page = []
    for i in range(lines):
        en = words("The State shall not deny equality", 320 if not wanted_left else 40, 50 + i * 14)
        hi = words("राज्य किसी व्यक्ति को वंचित नहीं", 40 if not wanted_left else 320, 50 + i * 14)
        page += en + hi
    return page


@pytest.mark.parametrize("wanted_left", [True, False])
def test_diglot_columns_keep_only_english(wanted_left):
    result = diglot.separate_page(two_columns(wanted_left), 7)
    assert result.mode == "columns" and not result.uncertain
    assert "State" in result.text and si.script_counts(result.text).get("Deva", 0) == 0
    assert "राज्य" in result.other_text and result.text.count("\n") == 11


def test_diglot_facing_pages_and_rows():
    assert diglot.separate_page(words("Only English text here", 40, 50), 1).mode == "single_language"
    hindi = diglot.separate_page(words("केवल हिंदी पाठ", 40, 50), 2)
    assert hindi.mode == "other_language" and hindi.text == ""
    page = []
    for i in range(8):
        page += words("यह ऊपर का हिंदी भाग है", 40, 50 + i * 14) + words("This is the lower English half", 40, 300 + i * 14)
    rows = diglot.separate_page(page, 3)
    assert rows.mode == "rows" and not rows.uncertain and "हिंदी" not in rows.text


def test_diglot_interleaved_page_is_uncertain_and_blocks_import():
    page = []
    for i in range(10):
        page += words("English words राज्य mixed with हिंदी here", 40, 50 + i * 14)
    result = diglot.separate_page(page, 4)
    assert result.mode == "interleaved" and result.uncertain
    assert si.script_counts(result.text).get("Deva", 0) == 0
    summary = diglot.summarise([diglot.separate_page(two_columns(), 1), result])
    assert not summary["reliable"] and "uncertain_column_extraction" in summary["blocking_reasons"]
    assert summary["uncertain_pages"] == [4]


def test_diglot_hindi_word_inside_english_column_is_removed_and_flagged():
    page = two_columns() + words("संविधान", 400, 300)
    result = diglot.separate_page(page, 5)
    assert si.script_counts(result.text).get("Deva", 0) == 0
    assert result.uncertain


def test_diglot_running_header_removed_without_alarm():
    page = words("भारत का संविधान", 200, 10)
    for i in range(30):
        page += words("The State shall not deny to any person equality", 40, 50 + i * 14)
    result = diglot.separate_page(page, 6)
    assert result.mode == "other_language_lines_removed" and not result.uncertain and "भारत" not in result.text


def test_diglot_clean_book_is_reliable_and_numbering_is_compared():
    pages = [diglot.separate_page(two_columns(), n) for n in (1, 2)]
    assert diglot.summarise(pages)["reliable"]
    en = ["PART III\n14. Equality before law.—The State shall not deny equality.\n15. Prohibition.—The State shall not discriminate."]
    hi = ["भाग 3\n14. विधि के समक्ष समता.—राज्य किसी व्यक्ति को वंचित नहीं करेगा।"]
    cmp = diglot.compare_numbering(en, hi)
    assert cmp["only_in_wanted"] == [15] and not cmp["agree"]


# ---------------------------------------------------------------- migration, CLI, locales
def test_migration_006_down_and_up(tmp_path):
    conn = connect(tmp_path / "m.db")
    apply_migrations(conn)
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(article_texts)")}
    assert {"body_normalized", "normalization_json"} <= columns
    rollback_migrations(conn, target=5)
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(article_texts)")}
    assert "body_normalized" not in columns and "body" in columns
    assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='import_changes'").fetchone()[0] == 0
    apply_migrations(conn)
    assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='import_changes'").fetchone()[0] == 1
    conn.close()


def cli(tmp_path, *args):
    env = {"PATH": "/usr/bin:/bin", "NYAYMITRA_DB_PATH": str(tmp_path / "cli.db"),
           "NYAYMITRA_BACKUP_DIR": str(tmp_path / "bk"), "NYAYMITRA_ENV": "development"}
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "import_constitution_data.py"), *args],
                          capture_output=True, text=True, env=env, cwd=ROOT)


def test_cli_dry_run_apply_rollback(tmp_path):
    data = tmp_path / "a.csv"
    data.write_text(f'article_no,text,page\n14,"{EN_14}",45\n21A,"{EN_21A}",52\n', encoding="utf-8")
    base = [str(data), "--language", "en", "--source-key", SOURCE, "--extraction-method", "text_layer"]
    subprocess.run([sys.executable, str(ROOT / "scripts" / "init_db.py")], capture_output=True, cwd=ROOT,
                   env={"PATH": "/usr/bin:/bin", "NYAYMITRA_DB_PATH": str(tmp_path / "cli.db")})
    out = cli(tmp_path, "check", *base, "--report", str(tmp_path / "r.json"))
    assert out.returncode == 0, out.stderr + out.stdout
    assert "DRY RUN" in out.stdout and json.loads((tmp_path / "r.json").read_text())["totals"]["import_ready"] == 2
    conn = connect(tmp_path / "cli.db")
    assert conn.execute("SELECT COUNT(*) FROM article_texts").fetchone()[0] == 0
    out = cli(tmp_path, "apply", *base)
    assert out.returncode == 0, out.stderr + out.stdout
    assert "Backup taken" in out.stdout and list((tmp_path / "bk").glob("*.db"))
    assert conn.execute("SELECT COUNT(*) FROM article_texts").fetchone()[0] == 2
    run_id = conn.execute("SELECT MAX(id) FROM ingest_runs").fetchone()[0]
    out = cli(tmp_path, "rollback", str(run_id))
    assert out.returncode == 0, out.stderr + out.stdout
    assert conn.execute("SELECT COUNT(*) FROM article_texts").fetchone()[0] == 0
    conn.close()
    bad = cli(tmp_path, "apply", str(data), "--language", "en", "--source-key", "nope", "--extraction-method", "ocr")
    assert bad.returncode == 3 and "unknown_source_key" in bad.stderr
    amb = tmp_path / "amb.csv"
    amb.write_text(f'c1,c2\n14,"{EN_14}"\n', encoding="utf-8")
    assert cli(tmp_path, "inspect", str(amb), "--language", "en").returncode == 4


def test_locale_audit_has_no_structural_errors():
    sys.path.insert(0, str(ROOT / "scripts"))
    import audit_locales

    report = audit_locales.audit()
    assert report["totals"]["languages"] == 23
    assert [r["code"] for r in report["languages"] if r["errors"]] == []
    for r in report["languages"]:
        if r["code"] not in ("en", "gu"):
            assert r["meta_status"] == "MACHINE_TRANSLATED" and not r["meta_reviewed"]
    assert {r["code"] for r in report["languages"] if r["direction"] == "rtl"} == {"ks", "sd", "ur"}
    assert audit_locales.unicode_problems("ભારતન ું") == ["vowel_sign_after_space"]
    assert "replacement_or_bidi_override_character" in audit_locales.unicode_problems("a\ufffdb")


def test_txt_export_with_page_markers(tmp_path):
    text = (f"--- Page 45 ---\nPART III\nFUNDAMENTAL RIGHTS\n14. Equality before law.—{EN_14}\n"
            f"--- Page 46 ---\n15. Sample heading.—{EN_21A}\n")
    _, loaded, m, records, report = run(tmp_path, "export.txt", text, "en")
    assert m["status"] == "ok" and loaded.page_source
    assert [(r.article_no, r.pages, r.part_no) for r in records] == [("14", "45", "III"), ("15", "46", "III")]
    assert report["coverage"]["with_page_reference"] == 2


def test_diglot_pdf_path_with_real_pdf(tmp_path):
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()
    for n, body in ((1, EN_14), (2, EN_21A)):
        page = doc.new_page()
        page.insert_text((60, 80), f"{13 + n}. Sample heading.—", fontsize=10)
        page.insert_textbox(pymupdf.Rect(60, 90, 500, 200), body, fontsize=10)
    path = tmp_path / "en.pdf"
    doc.save(str(path))
    pages, summary = diglot.extract_pdf(path)
    assert summary["reliable"] and summary["page_modes"] == {"single_language": 2}
    assert "equality" in pages[0].text and pages[0].page == 1
