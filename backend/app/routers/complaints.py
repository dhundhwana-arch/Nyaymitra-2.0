"""Complaint intake and token-gated retrieval."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from ..deps import db_dependency
from ..errors import AppError
from ..models import ComplaintCreate, ComplaintCreated, ComplaintOut, ComplaintPreview, ComplaintPreviewRequest
from ..security import hash_ip
from ..services import complaints, departments, triage

router = APIRouter(prefix="/complaints", tags=["complaints"])

NOTICE = complaints.NOTICE


@router.post("", response_model=ComplaintCreated, status_code=201)
def create_complaint(
    payload: ComplaintCreate,
    conn: sqlite3.Connection = Depends(db_dependency),
) -> dict:
    data = payload.model_dump()
    document_refs = []
    for doc in payload.documents:
        if not isinstance(doc, dict) or "id" not in doc or "token" not in doc:
            raise AppError("bad_request", "Each document entry needs an id and a token.").to_http()
        document_refs.append({"id": int(doc["id"]), "token": str(doc["token"])})

    created = complaints.create(conn, data, document_refs=document_refs)

    guide_row = triage.guide_for_category(conn, payload.category)
    guide = triage.shape_guide(guide_row, payload.language) if guide_row else None
    deps = departments.get_many(
        conn, [guide["department_key"]] if guide and guide["department_key"] else []
    )
    return {
        "reference": created["reference"],
        "access_token": created["access_token"],
        "status": created["status"],
        "created_at": created["created_at"],
        "summary": created["summary"],
        "category": created["category"],
        "next_steps": guide["steps"] if guide else [],
        "departments": deps,
        "notice": NOTICE,
    }


@router.post("/preview", response_model=ComplaintPreview)
def preview_complaint(payload: ComplaintPreviewRequest) -> dict:
    """Build the summary the user must confirm. Nothing is written to the database."""
    summary = complaints.build_summary(
        language=payload.language,
        category=payload.category,
        title=payload.title,
        description=payload.description,
        incident_date=str(payload.incident_date) if payload.incident_date else None,
        location=payload.location,
        district=payload.district,
        state=payload.state,
    )
    checks = []
    if not payload.location:
        checks.append("missing_location")
    if not payload.incident_date:
        checks.append("missing_incident_date")
    if len(payload.description.split()) < 25:
        checks.append("brief_description")
    return {
        "summary": summary,
        "category": payload.category,
        "word_count": len(payload.description.split()),
        "checks": checks,
    }


@router.get("/{reference}", response_model=ComplaintOut)
def get_complaint(
    reference: str,
    token: str = Query(..., min_length=10, max_length=200),
    conn: sqlite3.Connection = Depends(db_dependency),
) -> dict:
    record = complaints.get_by_reference(conn, reference, token)
    if record is None:
        # Same response for "not found" and "wrong token": no enumeration oracle.
        raise AppError(
            "not_found", "No complaint matches that reference and access token."
        ).to_http()
    return record
