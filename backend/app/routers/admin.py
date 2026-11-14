"""Administration and monitoring (role-based: monitor read-only, admin may mutate)."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query, Request

from ..config import Settings
from ..db import backup_database
from ..deps import db_dependency, require_role, settings_dependency
from ..errors import AppError
from ..models import VerificationUpdate
from ..security import client_ip, hash_ip
from ..metrics import metrics
from ..services import complaints, monitoring, provider_health, review

router = APIRouter(prefix="/admin", tags=["admin"])

read_only = require_role("monitor")
admin_only = require_role("admin")


@router.get("/metrics", dependencies=[Depends(read_only)])
def process_metrics() -> dict:
    """In-process counters for operational monitoring.

    No labels contain personal data: no IP addresses, no question text, no references.
    Counters reset when the process restarts; this is a liveness/health signal, not a
    long-term time series (ship stdout logs to your log store for that).
    """
    return metrics.snapshot()


@router.get("/stats", dependencies=[Depends(read_only)])
def stats(conn: sqlite3.Connection = Depends(db_dependency)) -> dict:
    return monitoring.stats(conn)


@router.get("/queries", dependencies=[Depends(read_only)])
def queries(limit: int = Query(50, ge=1, le=200), conn: sqlite3.Connection = Depends(db_dependency)) -> dict:
    return {"items": monitoring.recent_queries(conn, limit), "note": "Query text is redacted on write."}


@router.get("/answers", dependencies=[Depends(read_only)])
def answers(limit: int = Query(50, ge=1, le=200), conn: sqlite3.Connection = Depends(db_dependency)) -> dict:
    return {"items": monitoring.recent_answers(conn, limit)}


@router.get("/errors", dependencies=[Depends(read_only)])
def errors(limit: int = Query(50, ge=1, le=200), conn: sqlite3.Connection = Depends(db_dependency)) -> dict:
    return {"items": monitoring.recent_errors(conn, limit)}


@router.get("/audit", dependencies=[Depends(read_only)])
def audit(limit: int = Query(100, ge=1, le=500), conn: sqlite3.Connection = Depends(db_dependency)) -> dict:
    return {"items": monitoring.audit_trail(conn, limit)}


@router.get("/complaints", dependencies=[Depends(read_only)])
def complaint_index(limit: int = Query(50, ge=1, le=200), conn: sqlite3.Connection = Depends(db_dependency)) -> dict:
    return {
        "items": complaints.list_recent(conn, limit),
        "note": "Metadata only. Complaint text and contact details are not exposed to admins by design.",
    }


@router.get("/documents", dependencies=[Depends(read_only)])
def document_index(
    limit: int = Query(50, ge=1, le=200), conn: sqlite3.Connection = Depends(db_dependency)
) -> dict:
    rows = conn.execute(
        """SELECT id, original_name, mime_type, size_bytes, sha256, extraction_status,
                  ocr_confidence, created_at, complaint_id
           FROM documents ORDER BY id DESC LIMIT ?""",
        (limit,),
    )
    return {
        "items": [dict(row) for row in rows],
        "note": (
            "Metadata only. Extracted text and file contents are never exposed to admins; "
            "citizens retrieve their own document with the one-time token."
        ),
    }


@router.get("/sources", dependencies=[Depends(read_only)])
def sources(conn: sqlite3.Connection = Depends(db_dependency)) -> dict:
    rows = conn.execute(
        """SELECT s.source_key, s.title, s.publisher, s.source_type, s.url, s.retrieved_on,
                  (SELECT COUNT(*) FROM constitution_articles a WHERE a.source_id = s.id) AS articles,
                  (SELECT COUNT(*) FROM departments d WHERE d.source_id = s.id) AS departments
           FROM legal_sources s ORDER BY s.source_key"""
    ).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.get("/verification-queue", dependencies=[Depends(read_only)])
def verification_queue(conn: sqlite3.Connection = Depends(db_dependency)) -> dict:
    articles = conn.execute(
        """SELECT article_key, article_label, text_status, verification_status, last_checked_at
           FROM constitution_articles
           WHERE verification_status != 'verified' OR last_checked_at IS NULL
           ORDER BY sort_order"""
    ).fetchall()
    departments = conn.execute(
        """SELECT department_key, name_en, verification_status, verified_on
           FROM departments WHERE verification_status != 'verified' OR verified_on IS NULL
           ORDER BY department_key"""
    ).fetchall()
    return {
        "articles": [dict(r) for r in articles],
        "departments": [dict(r) for r in departments],
        "note": "Work queue for docs/LEGAL_VERIFICATION_CHECKLIST.md — every row needs a human sign-off.",
    }


@router.get("/ai/health", dependencies=[Depends(read_only)])
def ai_health(
    probe: bool = Query(True, description="also call the providers /models endpoint"),
    settings: Settings = Depends(settings_dependency),
) -> dict:
    """Is a live model configured, and is its endpoint reachable right now?"""
    return provider_health.health(settings, probe=probe)


@router.get("/ai/usage", dependencies=[Depends(read_only)])
def ai_usage(
    days: int = Query(30, ge=1, le=365),
    conn: sqlite3.Connection = Depends(db_dependency),
) -> dict:
    return monitoring.usage_summary(conn, days=days)


@router.get("/review-packet", dependencies=[Depends(read_only)])
def review_packet(
    format: str = Query("json", pattern="^(json|markdown)$"),
    kinds: str | None = Query(None,
              description="comma separated: article,department,triage,glossary"),
    conn: sqlite3.Connection = Depends(db_dependency),
) -> dict:
    wanted = None
    if kinds:
        wanted = tuple(part.strip() for part in kinds.split(",") if part.strip())
        invalid = set(wanted) - set(review.CHECKLIST)
        if invalid:
            raise AppError("validation_error", details={"unknown_kinds": sorted(invalid)})
    packet = review.build(conn, kinds=wanted)
    if format == "markdown":
        return {"format": "markdown", "total": packet["total"],
                "markdown": review.to_markdown(packet), "counts": packet["counts"]}
    return packet


@router.get("/legacy-chunks", dependencies=[Depends(read_only)])
def legacy_chunks(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(db_dependency),
) -> dict:
    rows = conn.execute(
        """SELECT id, legacy_id, article_no, script, substr(text, 1, 400) AS excerpt, archive_ref
           FROM legacy_import_chunks ORDER BY id LIMIT ? OFFSET ?""",
        (limit, offset),
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM legacy_import_chunks").fetchone()[0]
    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "note": (
            "Quarantined legacy import. These rows are NOT articles: 1732 of 2125 were unlabelled "
            "PDF chunks, 1905 were Santhali (Ol Chiki), and every row carried a generated 'remedy'. "
            "Never serve this content to citizens. See docs/REPOSITORY_AUDIT.md section 6."
        ),
    }


@router.patch("/articles/{article_id}/verification", dependencies=[Depends(admin_only)])
def update_verification(
    article_id: int,
    payload: VerificationUpdate,
    request: Request,
    conn: sqlite3.Connection = Depends(db_dependency),
    settings: Settings = Depends(settings_dependency),
) -> dict:
    row = conn.execute(
        "SELECT * FROM constitution_articles WHERE id = ?", (article_id,)
    ).fetchone()
    if row is None:
        raise AppError("not_found").to_http()
    if payload.verification_status == "verified":
        if not payload.checked_by or not payload.last_checked_at:
            raise AppError(
                "bad_request",
                "Verifying an article requires checked_by (the reviewer) and last_checked_at.",
            ).to_http()
        if row["text_status"] != "verified_source_text":
            raise AppError(
                "conflict",
                "Cannot verify an article whose authoritative text has not been loaded.",
            ).to_http()
    conn.execute(
        """UPDATE constitution_articles
           SET verification_status = ?, last_checked_at = COALESCE(?, last_checked_at),
               checked_by = COALESCE(?, checked_by), notes = COALESCE(?, notes),
               updated_at = datetime('now')
           WHERE id = ?""",
        (
            payload.verification_status,
            payload.last_checked_at.isoformat() if payload.last_checked_at else None,
            payload.checked_by,
            payload.notes,
            article_id,
        ),
    )
    monitoring.audit(
        conn,
        actor="admin",
        action="article.verification_update",
        target=str(article_id),
        detail={
            "from": row["verification_status"],
            "to": payload.verification_status,
            "checked_by": payload.checked_by,
        },
        ip_hash=hash_ip(client_ip(request, settings)),
    )
    return {"status": "updated", "article_id": article_id, "verification_status": payload.verification_status}


@router.post("/backup", dependencies=[Depends(admin_only)])
def backup(
    request: Request,
    settings: Settings = Depends(settings_dependency),
    conn: sqlite3.Connection = Depends(db_dependency),
) -> dict:
    target = backup_database(settings.backup_dir, settings.db_path)
    monitoring.audit(
        conn,
        actor="admin",
        action="database.backup",
        target=target.name,
        ip_hash=hash_ip(client_ip(request, settings)),
    )
    return {"status": "created", "file": target.name, "verified": True}
