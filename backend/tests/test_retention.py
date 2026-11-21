"""Retention purge: dry run, apply, file removal, audit trail, safety."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.app.db import get_db
from backend.app.services import retention

NOW = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)


def _insert_complaint(conn, reference: str, created_at: str) -> int:
    cur = conn.execute(
        """INSERT INTO complaints
           (reference, access_token_hash, language, category, title, description, summary,
            consent_given, status, submitted_at, created_at, updated_at)
           VALUES (?, 'x', 'en', 'other', 'Old complaint', 'text', 'summary', 1, 'submitted', ?, ?, ?)""",
        (reference, created_at, created_at, created_at),
    )
    return int(cur.lastrowid)


def _insert_document(conn, settings, stored_name: str, created_at: str, complaint_id: int | None):
    path = Path(settings.storage_dir) / stored_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4 retention test")
    conn.execute(
        """INSERT INTO documents
           (stored_name, original_name, mime_type, size_bytes, sha256, owner_token_hash,
            complaint_id, extraction_status, created_at)
           VALUES (?, 'x.pdf', 'application/pdf', 10, 'h', 't', ?, 'extracted', ?)""",
        (stored_name, complaint_id, created_at),
    )
    return path


def test_dry_run_deletes_nothing(isolated_settings):
    old = (NOW - timedelta(days=400)).isoformat()
    with get_db(isolated_settings.db_path) as conn:
        complaint_id = _insert_complaint(conn, "NYM-OLD001", old)
        path = _insert_document(conn, isolated_settings, "old-file.pdf", old, complaint_id)

        report = retention.purge(conn, isolated_settings, days=180, dry_run=True, now=NOW)

        assert report["complaints"] == 1
        assert report["documents"] == 1
        assert report["files_deleted"] == 0
        assert conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
        assert path.exists(), "a dry run must not touch the filesystem"


def test_apply_removes_old_data_and_keeps_recent(isolated_settings):
    old = (NOW - timedelta(days=400)).isoformat()
    recent = (NOW - timedelta(days=5)).isoformat()
    with get_db(isolated_settings.db_path) as conn:
        old_id = _insert_complaint(conn, "NYM-OLD002", old)
        recent_id = _insert_complaint(conn, "NYM-NEW002", recent)
        old_file = _insert_document(conn, isolated_settings, "old-2.pdf", old, old_id)
        new_file = _insert_document(conn, isolated_settings, "new-2.pdf", recent, recent_id)

        report = retention.purge(conn, isolated_settings, days=180, dry_run=False, now=NOW)

        assert report["complaints"] == 1
        assert report["files_deleted"] == 1
        assert not old_file.exists()
        assert new_file.exists(), "recent data must survive"
        references = {r["reference"] for r in conn.execute("SELECT reference FROM complaints")}
        assert references == {"NYM-NEW002"}
        assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1


def test_attachment_of_a_purged_complaint_is_removed_even_if_newer(isolated_settings):
    old = (NOW - timedelta(days=400)).isoformat()
    with get_db(isolated_settings.db_path) as conn:
        complaint_id = _insert_complaint(conn, "NYM-OLD003", old)
        # Document uploaded today, attached to a complaint that is past retention.
        path = _insert_document(conn, isolated_settings, "fresh-3.pdf", NOW.isoformat(), complaint_id)

        report = retention.purge(conn, isolated_settings, days=180, dry_run=False, now=NOW)
        assert report["documents"] == 1
        assert not path.exists()


def test_purge_writes_an_audit_row_without_personal_data(isolated_settings):
    old = (NOW - timedelta(days=400)).isoformat()
    with get_db(isolated_settings.db_path) as conn:
        _insert_complaint(conn, "NYM-OLD004", old)
        retention.purge(conn, isolated_settings, days=180, dry_run=False, now=NOW)
        row = conn.execute(
            "SELECT * FROM audit_log WHERE action = 'retention.purge' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert row is not None
        assert row["actor"] == "retention-job"
        assert "NYM-OLD004" not in (row["detail"] or "")
        assert "complaints=1" in (row["detail"] or "")


def test_query_logs_and_answers_are_purged(isolated_settings):
    old = (NOW - timedelta(days=400)).isoformat()
    with get_db(isolated_settings.db_path) as conn:
        cur = conn.execute(
            """INSERT INTO query_logs (request_id, language, query_text, query_hash, status, created_at)
               VALUES ('req-old', 'en', '[redacted]', 'h', 'ok', ?)""",
            (old,),
        )
        conn.execute(
            """INSERT INTO ai_answers (query_log_id, provider, grounded, degraded, citations_json,
                                       answer_text, warnings_json, created_at)
               VALUES (?, 'offline', 1, 0, '[]', 'answer', '[]', ?)""",
            (cur.lastrowid, old),
        )
        report = retention.purge(conn, isolated_settings, days=180, dry_run=False, now=NOW)
        assert report["query_logs"] == 1
        assert conn.execute("SELECT COUNT(*) FROM query_logs").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM ai_answers").fetchone()[0] == 0


def test_purge_refuses_to_delete_outside_the_storage_directory(isolated_settings):
    old = (NOW - timedelta(days=400)).isoformat()
    with get_db(isolated_settings.db_path) as conn:
        conn.execute(
            """INSERT INTO documents
               (stored_name, original_name, mime_type, size_bytes, sha256, owner_token_hash,
                extraction_status, created_at)
               VALUES ('../../escape.pdf', 'x.pdf', 'application/pdf', 1, 'h', 't', 'extracted', ?)""",
            (old,),
        )
        report = retention.purge(conn, isolated_settings, days=180, dry_run=False, now=NOW)
        assert report["files_deleted"] == 0
        # the row is still deleted — only the unsafe file path is skipped
        assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0


def test_retention_window_zero_purges_everything_older_than_now(isolated_settings):
    with get_db(isolated_settings.db_path) as conn:
        _insert_complaint(conn, "NYM-OLD005", (NOW - timedelta(minutes=5)).isoformat())
        report = retention.purge(conn, isolated_settings, days=0, dry_run=False, now=NOW)
        assert report["complaints"] == 1
