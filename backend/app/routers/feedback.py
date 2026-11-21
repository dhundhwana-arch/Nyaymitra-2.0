"""Citizen feedback on an answer, article or department contact."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from ..deps import db_dependency
from ..errors import AppError
from ..models import FeedbackCreate

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", status_code=201)
def create_feedback(
    payload: FeedbackCreate,
    conn: sqlite3.Connection = Depends(db_dependency),
) -> dict:
    target = payload.target_ref.strip()
    if payload.target_type == "article" and not any(ch.isdigit() for ch in target):
        raise AppError("bad_request", "target_ref for an article must contain the article number.").to_http()
    if payload.target_type == "article":
        exists = conn.execute(
            "SELECT 1 FROM constitution_articles WHERE article_no = ? OR article_label = ?",
            (target, target),
        ).fetchone()
        if not exists and not target.isdigit():
            # Don't fail the citizen's report because of a label mismatch: record it anyway.
            pass
    cur = conn.execute(
        "INSERT INTO feedback (target_type, target_ref, reason, message) VALUES (?,?,?,?)",
        (payload.target_type, target, payload.reason, payload.message),
    )
    return {
        "status": "recorded",
        "id": int(cur.lastrowid),
        "message": "Thank you — this report is queued for human review.",
    }
