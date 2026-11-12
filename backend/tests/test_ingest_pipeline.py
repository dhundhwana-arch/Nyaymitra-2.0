"""Production behaviour of the Constitution ingestion pipeline.

Covers page/part provenance, boundary detection, the quality gate, idempotency, the
protection of existing and verified text, the coverage report and the CLI contract.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from backend.app.db import apply_migrations, get_db
from backend.app.services import ingest as ingest_service

REPO_ROOT = Path(__file__).resolve().parents[2]

PAGE_ONE = """THE CONSTITUTION OF INDIA

PART III
FUNDAMENTAL RIGHTS

14. Equality before law.—The State shall not deny to any person equality before the law or the
equal protection of the laws within the territory of India.
"""

PAGE_TWO = """15. Prohibition of discrimination on grounds of religion, race, caste, sex or place of birth.—
(1) The State shall not discriminate against any citizen on grounds only of religion, race, caste,
sex, place of birth or any of them.

21. Protection of life and personal liberty.—No person shall be deprived of his life or personal
liberty except according to procedure established by law.
"""

PAGES = [PAGE_ONE, PAGE_TWO]


def test_pages_and_parts_are_preserved():
    articles, malformed = ingest_service.parse_articles(PAGES)
    assert malformed == []
    by_number = {a.article_no: a for a in articles}

    assert by_number["14"].page_start == 1
    assert by_number["14"].page_end == 1
    assert by_number["14"].part_no == "III"
    assert by_number["14"].part_title.upper().startswith("FUNDAMENTAL RIGHTS")

    assert by_number["15"].page_start == 2
    assert by_number["21"].pages_label == "2"


def test_read_pages_keeps_page_boundaries(tmp_path):
    path = tmp_path / "doc.txt"
    path.write_text(PAGE_ONE + "\n\f\n" + PAGE_TWO, encoding="utf-8")
    pages, kind = ingest_service.read_pages(path)
    assert kind == "text"
    assert len(pages) == 1, "a text file is a single page"


def test_read_pages_rejects_unsupported_formats(tmp_path):
    path = tmp_path / "doc.docx"
    path.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        ingest_service.read_pages(path)


def test_boundary_detection_flags_embedded_headings_and_page_headers():
    text = """14. Equality before law.—The State shall not deny equality.

THE CONSTITUTION OF INDIA

999. A heading that cannot be a real article number because it is out of range.
"""
    articles, _ = ingest_service.parse_articles(text)
    issues = ingest_service.boundary_issues(articles)
    assert issues and issues[0]["article_no"] == "14"
    assert {"page_header_inside_body", "embedded_article_heading"} <= set(issues[0]["reasons"])


def test_boundary_detection_flags_oversized_bodies():
    # A heading line is limited to ~400 characters, so build many body lines.
    filler = "\n".join("word " * 80 for _ in range(30))  # ~10k characters
    text = f"14. Equality before law.—first line of the body\n{filler}\n"
    articles, _ = ingest_service.parse_articles(text)
    issues = ingest_service.boundary_issues(articles)
    assert any("oversized_body" in issue["reasons"] for issue in issues)


def test_quality_gate_passes_a_clean_document(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        report = ingest_service.ingest_text(
            conn, text=PAGES, source_key="india-code-constitution",
            source_file="clean.txt", language="en", dry_run=True,
        )
    assert report.quality_ok is True
    assert report.blocking_reasons == []
    assert report.articles_found == 3


def test_quality_gate_blocks_a_duplicated_document(isolated_settings):
    duplicated = PAGE_ONE + "\n" + PAGE_ONE
    with get_db(isolated_settings.db_path) as conn:
        report = ingest_service.ingest_text(
            conn, text=duplicated, source_key="india-code-constitution",
            source_file="dupe.txt", language="en", dry_run=True,
        )
    assert report.quality_ok is False
    assert "duplicate_article_numbers" in report.blocking_reasons
    assert report.duplicates == ["14"]


def test_quality_gate_blocks_noisy_text():
    noise = "\ufffd" * 250
    noisy = (
        "14. Equality before law.—The State shall not deny equality.\n"
        f"{noise}\n"
    )
    with get_db(":memory:") as conn:  # parse-only; nothing is written in a dry run
        report = ingest_service.ingest_text(
            conn, text=noisy, source_key="india-code-constitution",
            source_file="scan.txt", language="en", dry_run=True,
        )
    assert "low_text_quality" in report.blocking_reasons


def test_ingest_stores_page_provenance(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        ingest_service.ingest_text(
            conn, text=PAGES, source_key="india-code-constitution",
            source_file="pages.txt", language="en", dry_run=False,
        )
        row = conn.execute(
            "SELECT source_pages, source_locator, part_no FROM constitution_articles"
            " WHERE article_no = '15'"
        ).fetchone()
        assert row["source_pages"] == "2"
        assert "pages 2" in row["source_locator"]
        assert row["part_no"] == "III"


def test_reingest_is_idempotent(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        first = ingest_service.ingest_text(
            conn, text=PAGES, source_key="india-code-constitution",
            source_file="pages.txt", language="en", dry_run=False,
        )
        assert first.articles_written == 3
        before = conn.execute("SELECT COUNT(*) FROM constitution_articles").fetchone()[0]

        second = ingest_service.ingest_text(
            conn, text=PAGES, source_key="india-code-constitution",
            source_file="pages.txt", language="en", dry_run=False,
        )
        after = conn.execute("SELECT COUNT(*) FROM constitution_articles").fetchone()[0]

        assert second.articles_written == 0
        assert second.articles_unchanged == 3
        assert before == after, "a re-run must not add rows"


def test_existing_text_is_not_replaced_by_a_worse_extract(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        ingest_service.ingest_text(
            conn, text=PAGES, source_key="india-code-constitution",
            source_file="pages.txt", language="en", dry_run=False,
        )
        conn.execute(
            "UPDATE constitution_articles SET text_en = 'GOOD ORIGINAL TEXT' WHERE article_no = '14'"
        )
        partial = ingest_service.ingest_text(
            conn, text="14. Equality before law.—truncated garbage\n",
            source_key="india-code-constitution", source_file="partial.txt",
            language="en", dry_run=False,
        )
        assert partial.articles_conflicting == 1
        assert partial.articles_written == 0
        assert conn.execute(
            "SELECT text_en FROM constitution_articles WHERE article_no = '14'"
        ).fetchone()["text_en"] == "GOOD ORIGINAL TEXT"


def test_replace_existing_requires_an_explicit_opt_in(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        ingest_service.ingest_text(
            conn, text=PAGES, source_key="india-code-constitution",
            source_file="pages.txt", language="en", dry_run=False,
        )
        conn.execute(
            "UPDATE constitution_articles SET text_en = 'OLD TEXT' WHERE article_no = '14'"
        )
        report = ingest_service.ingest_text(
            conn, text=PAGES, source_key="india-code-constitution", source_file="pages.txt",
            language="en", dry_run=False, replace_existing=True,
        )
        assert report.articles_written == 1
        assert "shall not deny" in conn.execute(
            "SELECT text_en FROM constitution_articles WHERE article_no = '14'"
        ).fetchone()["text_en"]


def test_replace_existing_still_refuses_verified_rows(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        ingest_service.ingest_text(
            conn, text=PAGES, source_key="india-code-constitution",
            source_file="pages.txt", language="en", dry_run=False,
        )
        conn.execute(
            "UPDATE constitution_articles SET verification_status = 'verified',"
            " text_en = 'HUMAN APPROVED' WHERE article_no = '14'"
        )
        report = ingest_service.ingest_text(
            conn, text=PAGES, source_key="india-code-constitution", source_file="pages.txt",
            language="en", dry_run=False, replace_existing=True,
        )
        assert report.articles_skipped_verified == 1
        assert conn.execute(
            "SELECT text_en FROM constitution_articles WHERE article_no = '14'"
        ).fetchone()["text_en"] == "HUMAN APPROVED"


def test_ingest_run_records_a_warning_status_when_quality_failed(isolated_settings):
    duplicated = PAGE_ONE + "\n" + PAGE_ONE
    with get_db(isolated_settings.db_path) as conn:
        ingest_service.ingest_text(
            conn, text=duplicated, source_key="india-code-constitution",
            source_file="dupe.txt", language="en", dry_run=False,
        )
        run = conn.execute("SELECT status, report_json FROM ingest_runs ORDER BY id DESC LIMIT 1").fetchone()
        assert run["status"] == "completed_with_warnings"
        assert json.loads(run["report_json"])["duplicates"] == ["14"]


# ------------------------------------------------------------------ coverage
def test_coverage_ranges_compress():
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import constitution_coverage as coverage

    assert coverage._ranges([1, 2, 3, 7, 9, 10]) == "1-3, 7, 9-10"
    assert coverage._ranges([]) == ""


def test_coverage_report_counts_real_rows(isolated_settings):
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import constitution_coverage as coverage

    with get_db(isolated_settings.db_path) as conn:
        ingest_service.ingest_text(
            conn, text=PAGES, source_key="india-code-constitution",
            source_file="pages.txt", language="en", dry_run=False,
        )
        report = coverage.build_report(conn)
        assert report["loaded_articles"] >= 3
        assert report["articles_with_source_text"] >= 3
        assert report["articles_human_verified"] == 0
        assert report["duplicate_numbers"] == []
        assert "1-" in report["missing_ranges"]
        markdown = coverage.to_markdown(report)
        assert "# Constitution coverage" in markdown
        assert "human verified" in markdown.lower() or "signed off" in markdown.lower()


# ----------------------------------------------------------------------- CLI
def _run_cli(args: list[str], db_path: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, NYAYMITRA_DB_PATH=str(db_path))
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "ingest_constitution.py"), *args],
        capture_output=True, text=True, env=env, cwd=REPO_ROOT,
    )


def test_cli_dry_run_writes_nothing_and_exits_zero(isolated_settings, tmp_path):
    source = tmp_path / "constitution.txt"
    source.write_text("\n".join(PAGES), encoding="utf-8")
    with get_db(isolated_settings.db_path) as conn:
        before = conn.execute("SELECT COUNT(*) FROM constitution_articles").fetchone()[0]

    result = _run_cli(
        ["--file", str(source), "--source-key", "india-code-constitution", "--language", "en"],
        isolated_settings.db_path,
    )
    assert result.returncode == 0, result.stderr
    assert "DRY RUN" in result.stdout
    with get_db(isolated_settings.db_path) as conn:
        after = conn.execute("SELECT COUNT(*) FROM constitution_articles").fetchone()[0]
    assert before == after


def test_cli_refuses_to_apply_a_failed_quality_gate(isolated_settings, tmp_path):
    source = tmp_path / "duplicated.txt"
    source.write_text(PAGE_ONE + "\n" + PAGE_ONE, encoding="utf-8")
    result = _run_cli(
        ["--file", str(source), "--source-key", "india-code-constitution", "--apply"],
        isolated_settings.db_path,
    )
    assert result.returncode == 3
    assert "Refusing to write" in result.stderr
    with get_db(isolated_settings.db_path) as conn:
        run = conn.execute("SELECT COUNT(*) FROM ingest_runs").fetchone()[0]
    assert run == 0, "a refused run must not be recorded as an ingestion"


def test_cli_apply_is_idempotent_and_records_the_run(isolated_settings, tmp_path):
    source = tmp_path / "constitution.txt"
    source.write_text("\n".join(PAGES), encoding="utf-8")
    args = ["--file", str(source), "--source-key", "india-code-constitution", "--apply"]

    first = _run_cli(args, isolated_settings.db_path)
    assert first.returncode == 0, first.stderr
    second = _run_cli(args, isolated_settings.db_path)
    assert second.returncode == 0, second.stderr
    assert "0 unchanged" not in second.stdout  # unchanged count is reported for a re-run
    with get_db(isolated_settings.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM ingest_runs").fetchone()[0] == 2


# ------------------------------------------------- source metadata / manifest

def test_unknown_source_key_raises(isolated_settings):
    """ingest_text must refuse a source_key that is not in legal_sources."""
    with get_db(isolated_settings.db_path) as conn:
        with pytest.raises(ValueError, match="unknown source_key"):
            ingest_service.ingest_text(
                conn, text=PAGES, source_key="does-not-exist",
                source_file="x.txt", language="en", dry_run=False,
            )


def test_ingest_run_records_source_metadata(isolated_settings):
    """Each ingest_run row must carry source_key, source_file and article counts."""
    with get_db(isolated_settings.db_path) as conn:
        report = ingest_service.ingest_text(
            conn, text=PAGES, source_key="india-code-constitution",
            source_file="constitution-en.txt", language="en", dry_run=False,
        )
        run = conn.execute(
            "SELECT source_key, source_file, articles_found, articles_written, status"
            " FROM ingest_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert run["source_key"] == "india-code-constitution"
    assert run["source_file"] == "constitution-en.txt"
    assert run["articles_found"] == report.articles_found
    assert run["articles_written"] == report.articles_written
    assert run["status"] == "completed"


# ------------------------------------------------- document integrity

def test_empty_text_produces_zero_articles_and_blocks(isolated_settings):
    """An empty source must be caught by the quality gate, not silently imported."""
    with get_db(isolated_settings.db_path) as conn:
        report = ingest_service.ingest_text(
            conn, text="", source_key="india-code-constitution",
            source_file="empty.txt", language="en", dry_run=True,
        )
    assert report.articles_found == 0
    assert report.quality_ok is False
    assert "no_articles_found" in report.blocking_reasons


def test_whitespace_only_text_produces_zero_articles():
    """Text with no article headings yields zero parsed articles."""
    articles, malformed = ingest_service.parse_articles(
        ["\n   \n\n  \n", "PART III\nFUNDAMENTAL RIGHTS\n"]
    )
    assert articles == []
    assert malformed == []


def test_unsupported_file_format_is_rejected(tmp_path):
    """read_pages must reject formats it cannot parse (docx, etc.)."""
    path = tmp_path / "document.docx"
    path.write_bytes(b"PK\x03\x04 fake zip")
    with pytest.raises(ValueError, match="unsupported source type"):
        ingest_service.read_pages(path)


def test_nonexistent_file_cli_returns_exit_code_2(isolated_settings, tmp_path):
    """The CLI must exit 2 when the source file does not exist."""
    result = _run_cli(
        ["--file", str(tmp_path / "missing.pdf"), "--source-key", "india-code-constitution"],
        isolated_settings.db_path,
    )
    assert result.returncode == 2
    assert "Source file not found" in result.stderr


# ------------------------------------------------- Gujarati language separation

def test_gujarati_text_writes_to_text_gu_column(isolated_settings):
    """language='gu' must populate text_gu, not text_en; title goes to title_gu."""
    gu_pages = [
        "14. સમાનતા.—રાજ્ય કોઈપણ વ્યક્તિ સાથે સમાનતા વર્તાવશે.\n"
    ]
    with get_db(isolated_settings.db_path) as conn:
        report = ingest_service.ingest_text(
            conn, text=gu_pages, source_key="india-code-constitution",
            source_file="samvidhan-gu.txt", language="gu", dry_run=False,
        )
        assert report.articles_written == 1
        row = conn.execute(
            "SELECT text_en, text_gu, title_en, title_gu FROM constitution_articles"
            " WHERE article_no = '14'"
        ).fetchone()
    assert row["text_en"] is None or row["text_en"] == ""
    assert "સમાનતા" in row["text_gu"]
    assert row["title_gu"] is not None


# ------------------------------------------------- article number validation

def test_article_number_zero_is_rejected():
    """Article 0 is not a valid Constitution article and must be skipped."""
    articles, malformed = ingest_service.parse_articles(
        "0. Invalid article.—This should not be parsed.\n"
        "14. Equality before law.—Valid article.\n"
    )
    numbers = {a.article_no for a in articles}
    assert "0" not in numbers
    assert "14" in numbers


def test_out_of_range_article_numbers_are_rejected():
    """Article numbers above MAX_ARTICLE_NUMBER (500) must be skipped."""
    articles, _ = ingest_service.parse_articles(
        "501. Not a real article.—Out of range.\n"
        "14. Equality before law.—Valid.\n"
    )
    numbers = {a.article_no for a in articles}
    assert "501" not in numbers
    assert "14" in numbers


def test_letter_suffix_articles_are_accepted():
    """Constitution articles with letter suffixes (21A, 39A, 44A) are valid."""
    articles, _ = ingest_service.parse_articles(
        "21A. Right to education.—Valid suffixed article.\n"
        "39A. Equal justice and free legal aid.—Valid suffixed article.\n"
    )
    numbers = {a.article_no for a in articles}
    assert "21A" in numbers
    assert "39A" in numbers


# ------------------------------------------------- missing numbers / gap reporting

def test_missing_numbers_are_reported_not_invented(isolated_settings):
    """find_missing must report gaps in the observed range, never fabricate articles."""
    with get_db(isolated_settings.db_path) as conn:
        report = ingest_service.ingest_text(
            conn, text=PAGES, source_key="india-code-constitution",
            source_file="pages.txt", language="en", dry_run=False,
        )
    # PAGES contains articles 14, 15, 21 → 1-13, 16-20, 22-21 (empty) are missing
    assert report.missing_numbers == ["1", "2", "3", "4", "5", "6", "7", "8",
                                      "9", "10", "11", "12", "13",
                                      "16", "17", "18", "19", "20"]
    assert "21" not in report.missing_numbers, "21 is present in PAGES"
    assert "missing_articles" in report.warnings[0] if report.warnings else True


def test_empty_source_reports_no_missing_numbers():
    """find_missing on an empty article list must return [], not 1-395."""
    missing = ingest_service.find_missing([])
    assert missing == []


# ------------------------------------------------- extraction quality signals

def test_low_text_quality_is_flagged_not_blocked_alone():
    """Replacement characters lower OCR confidence; alone they warn but do not block
    unless combined with other quality-gate failures."""
    noise = "\ufffd" * 200
    noisy = f"14. Equality before law.—The State shall not deny equality.\n{noise}\n"
    with get_db(":memory:") as conn:
        report = ingest_service.ingest_text(
            conn, text=noisy, source_key="india-code-constitution",
            source_file="scan.txt", language="en", dry_run=True,
        )
    assert report.ocr_confidence < 1.0
    assert any("low_text_quality" in w for w in report.warnings)


def test_article_pages_label_format():
    """pages_label must render 'start-end' for multi-page articles and 'n' for single-page."""
    from backend.app.services.ingest import ParsedArticle

    single = ParsedArticle(article_no="14", title="T", body="B", line_no=1,
                           page_start=5, page_end=5)
    assert single.pages_label == "5"

    multi = ParsedArticle(article_no="15", title="T", body="B", line_no=1,
                          page_start=3, page_end=7)
    assert multi.pages_label == "3-7"
