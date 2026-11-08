"""Retention: delete personal data that is older than the configured window.

Complaints and uploaded documents are personal data. ``NYAYMITRA_PII_RETENTION_DAYS``
declares how long they may be kept; this module is what actually enforces it. It is
invoked by ``scripts/purge_data.py`` (dry-run by default) and never runs implicitly.

What is deleted
---------------
* complaints older than the cutoff,
* their documents (rows and files) — including documents newer than the cutoff,
  because an orphaned attachment can no longer be retrieved by anyone,
* query logs and their answers older than the cutoff (operational metadata).

What is kept: ``audit_log``, ``error_log`` and ``ingest_runs`` — these are the audit
trail and contain no citizen free text. The purge itself writes one audit row with
counts only, so the deletion is accountable without re-storing the data.
"""
from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..config import Settings
from . import monitoring

log = logging.getLogger(__name__)


def _cutoff(now: datetime | None, days: int) -> str:
    moment = now or datetime.now(timezone.utc)
    return (moment - timedelta(days=max(0, days))).replace(microsecond=0).isoformat()


def plan(conn: sqlite3.Connection, cutoff: str) -> dict[str, Any]:
    """Work out what a purge at ``cutoff`` would remove. Reads only."""
    complaints = conn.execute(
        "SELECT id, reference FROM complaints WHERE created_at < ?", (cutoff,)
    ).fetchall()
    complaint_ids = [row["id"] for row in complaints]
    if complaint_ids:
        placeholders = ",".join("?" for _ in complaint_ids)
        documents = conn.execute(
            f"""SELECT id, stored_name FROM documents
                WHERE created_at < ? OR complaint_id IN ({placeholders})""",
            [cutoff, *complaint_ids],
        ).fetchall()
    else:
        documents = conn.execute(
            "SELECT id, stored_name FROM documents WHERE created_at < ?", (cutoff,)
        ).fetchall()
    query_logs = conn.execute(
        "SELECT id FROM query_logs WHERE created_at < ?", (cutoff,)
    ).fetchall()
    return {
        "complaint_ids": complaint_ids,
        "references": [row["reference"] for row in complaints],
        "documents": [(row["id"], row["stored_name"]) for row in documents],
        "query_log_ids": [row["id"] for row in query_logs],
    }


def purge(
    conn: sqlite3.Connection,
    settings: Settings,
    *,
    days: int | None = None,
    dry_run: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Delete personal data older than ``days`` (default: configured retention)."""
    retention_days = settings.pii_retention_days if days is None else days
    cutoff = _cutoff(now, retention_days)
    work = plan(conn, cutoff)

    report: dict[str, Any] = {
        "dry_run": dry_run,
        "retention_days": retention_days,
        "cutoff": cutoff,
        "complaints": len(work["complaint_ids"]),
        "documents": len(work["documents"]),
        "query_logs": len(work["query_log_ids"]),
        "files_deleted": 0,
        "files_missing": 0,
    }
    if dry_run:
        return report

    storage_root = Path(settings.storage_dir).resolve()
    for _, stored_name in work["documents"]:
        target = (storage_root / stored_name).resolve()
        if storage_root not in target.parents:
            # Never delete outside the storage directory, whatever the row says.
            log.error("retention skipped an out-of-tree document path")
            continue
        try:
            target.unlink()
            report["files_deleted"] += 1
        except FileNotFoundError:
            report["files_missing"] += 1
        except OSError as exc:  # pragma: no cover - filesystem dependent
            log.warning("retention could not delete a document file: %s", type(exc).__name__)

    for document_id, _ in work["documents"]:
        conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    for complaint_id in work["complaint_ids"]:
        conn.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
    for query_log_id in work["query_log_ids"]:
        conn.execute("DELETE FROM ai_answers WHERE query_log_id = ?", (query_log_id,))
        conn.execute("DELETE FROM query_logs WHERE id = ?", (query_log_id,))

    monitoring.audit(
        conn,
        actor="retention-job",
        action="retention.purge",
        target=f"cutoff:{cutoff}",
        detail=(
            f"complaints={report['complaints']} documents={report['documents']} "
            f"query_logs={report['query_logs']} files={report['files_deleted']}"
        ),
    )
    return report
