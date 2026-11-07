"""Migrations, rollback, backup/restore, seeding and the ingestion validator.

Everything here runs against its own throw-away database (``isolated_settings``) so that
destructive checks never touch the database the other tests share.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from backend.app.db import (
    apply_migrations,
    applied_migrations,
    backup_database,
    get_db,
    rollback_migrations,
)
from backend.app.services import ingest as ingest_service
from backend.app.services.seed import seed_all

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_migrations_are_idempotent(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        assert apply_migrations(conn, isolated_settings.migrations_dir) == []
        assert "001_initial.sql" in applied_migrations(conn)


def test_rollback_and_reapply(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        rolled = rollback_migrations(conn, isolated_settings.migrations_dir, target=0)
        assert "001_initial.sql" in rolled
        tables = {
            r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "constitution_articles" not in tables
        assert apply_migrations(conn, isolated_settings.migrations_dir) == ["001_initial.sql"]


def test_foreign_keys_are_enforced(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO documents (stored_name, original_name, mime_type, size_bytes, sha256,"
                " owner_token_hash, complaint_id) VALUES ('x','x','application/pdf',1,'h','t',999999)"
            )


def test_backup_and_restore_roundtrip(isolated_settings):
    backup = backup_database(isolated_settings.backup_dir, isolated_settings.db_path)
    assert backup.exists()
    with sqlite3.connect(str(backup)) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("SELECT COUNT(*) FROM constitution_articles").fetchone()[0] >= 9


def test_seed_is_idempotent_and_preserves_human_decisions(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        first = conn.execute("SELECT COUNT(*) FROM constitution_articles").fetchone()[0]
        conn.execute(
            "UPDATE constitution_articles SET verification_status='verified',"
            " checked_by='reviewer', last_checked_at='2026-01-01' WHERE article_no='14'"
        )
    seed_all(isolated_settings)
    with get_db(isolated_settings.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM constitution_articles").fetchone()[0] == first
        row = conn.execute(
            "SELECT verification_status, checked_by FROM constitution_articles WHERE article_no='14'"
        ).fetchone()
        assert row["verification_status"] == "verified", "seeding must not undo a human verification"
        assert row["checked_by"] == "reviewer"


def test_legacy_rows_are_preserved(client, admin_headers):
    body = client.get("/api/v1/admin/legacy-chunks", headers=admin_headers).json()
    assert body["total"] == 2125
    with get_db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM legacy_import_chunks").fetchone()[0] == 2125
        # the quarantined content must never appear as an article
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM constitution_articles WHERE article_no LIKE 'Section Chunk%'"
            ).fetchone()[0]
            == 0
        )


def test_legacy_archive_has_checksums():
    note = (REPO_ROOT / "data" / "legacy" / "LEGACY_DATA_NOTE.md").read_text(encoding="utf-8")
    assert "sha256" in note
    archive = next((REPO_ROOT / "data" / "legacy").glob("*.jsonl.gz"))
    assert archive.stat().st_size > 100_000


# --------------------------------------------------------------- ingestion
SAMPLE = """\
THE CONSTITUTION OF INDIA

14. Equality before law.—The State shall not deny to any person equality before the law or the
equal protection of the laws within the territory of India.

15. Prohibition of discrimination on grounds of religion, race, caste, sex or place of birth.—
(1) The State shall not discriminate against any citizen on grounds only of religion, race, caste,
sex, place of birth or any of them.

15. Prohibition of discrimination (duplicate page).—This duplicated page appears twice in the OCR
output of the supplied document, which is exactly the Article 222 problem the legacy import hid.

19. Protection of certain rights regarding freedom of speech, etc.—All citizens shall have the
right to freedom of speech and expression.
"""


def test_parser_extracts_articles():
    articles, malformed = ingest_service.parse_articles(SAMPLE)
    numbers = [a.article_no for a in articles]
    assert numbers == ["14", "15", "15", "19"]
    assert malformed == []
    assert articles[0].title.startswith("Equality before law")
    assert "shall not deny" in articles[0].body


def test_duplicate_detection():
    articles, _ = ingest_service.parse_articles(SAMPLE)
    assert ingest_service.find_duplicates(articles) == ["15"]


def test_missing_numbers_are_reported_not_invented():
    articles, _ = ingest_service.parse_articles(SAMPLE)
    missing = ingest_service.find_missing(articles)
    assert missing == [str(n) for n in range(1, 19) if n not in {14, 15, 19}]
    assert "1" in missing and "13" in missing


def test_pdf_noise_lowers_ocr_confidence():
    clean = ingest_service.ocr_confidence("Equality before law is guaranteed.")
    noisy = ingest_service.ocr_confidence("Equa\ufffdli\ufffdty be\ufffdf\ufffdre la\ufffdw")
    assert clean > noisy
    assert noisy < 0.9


def test_dry_run_writes_nothing(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        before = conn.execute("SELECT COUNT(*) FROM constitution_articles").fetchone()[0]
        report = ingest_service.ingest_text(
            conn, text=SAMPLE, source_key="india-code-constitution",
            source_file="sample.txt", language="en", dry_run=True,
        )
        after = conn.execute("SELECT COUNT(*) FROM constitution_articles").fetchone()[0]
        assert before == after
        assert report.articles_found == 4
        assert report.duplicates == ["15"]
        assert report.missing_numbers


def test_apply_writes_articles_and_report(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        report = ingest_service.ingest_text(
            conn, text=SAMPLE, source_key="india-code-constitution",
            source_file="sample.txt", language="en", dry_run=False,
        )
        assert report.articles_written >= 3
        row = conn.execute(
            "SELECT text_en, text_status, verification_status, source_id FROM constitution_articles"
            " WHERE article_no = '14'"
        ).fetchone()
        assert row["text_status"] == "verified_source_text"
        assert "shall not deny" in row["text_en"]
        assert row["verification_status"] == "requires_human_verification"
        assert row["source_id"] is not None
        run = conn.execute("SELECT * FROM ingest_runs ORDER BY id DESC LIMIT 1").fetchone()
        payload = json.loads(run["report_json"])
        assert payload["duplicates"] == ["15"]


def test_ingest_does_not_overwrite_verified_rows(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        conn.execute(
            "UPDATE constitution_articles SET verification_status='verified', text_en='HUMAN VERIFIED',"
            " text_status='verified_source_text' WHERE article_no='14'"
        )
        report = ingest_service.ingest_text(
            conn, text=SAMPLE, source_key="india-code-constitution",
            source_file="sample.txt", language="en", dry_run=False,
        )
        assert report.articles_skipped_verified == 1
        assert conn.execute(
            "SELECT text_en FROM constitution_articles WHERE article_no='14'"
        ).fetchone()["text_en"] == "HUMAN VERIFIED"


def test_ingest_requires_a_known_source(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        with pytest.raises(ValueError):
            ingest_service.ingest_text(
                conn, text=SAMPLE, source_key="not-a-source", source_file="x.txt", dry_run=False
            )


def test_short_body_is_flagged_not_padded():
    text = "21. Protection of life and personal liberty.—No person shall be deprived.\n"
    articles, _ = ingest_service.parse_articles(text)
    assert len(articles) == 1
    assert len(articles[0].body) < ingest_service.MIN_BODY_CHARS
