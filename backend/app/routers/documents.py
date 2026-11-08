"""Document upload, metadata and owner-only download."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse

from ..config import Settings
from ..deps import db_dependency, settings_dependency
from ..errors import AppError
from ..models import DocumentOut
from ..services import documents

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    document_kind: str = Form("evidence"),
    conn: sqlite3.Connection = Depends(db_dependency),
    settings: Settings = Depends(settings_dependency),
) -> dict:
    # Read with a hard cap so a huge body cannot exhaust memory before validation.
    chunk = await file.read(settings.max_upload_bytes + 1)
    if len(chunk) > settings.max_upload_bytes:
        raise AppError(
            "payload_too_large",
            f"File exceeds {settings.max_upload_bytes // (1024 * 1024)} MB.",
        ).to_http()
    record = documents.save_upload(
        conn,
        settings,
        filename=file.filename,
        content_type=file.content_type,
        content=chunk,
        document_kind=document_kind,
    )
    return record


@router.get("/{document_id}", response_model=DocumentOut)
def document_metadata(
    document_id: int,
    token: str = Query(..., min_length=10, max_length=200),
    conn: sqlite3.Connection = Depends(db_dependency),
) -> dict:
    row = documents.get_for_owner(conn, document_id, token)
    if row is None:
        raise AppError("not_found", "No document matches that id and token.").to_http()
    return {
        "id": row["id"],
        "original_name": row["original_name"],
        "mime_type": row["mime_type"],
        "size_bytes": row["size_bytes"],
        "sha256": row["sha256"],
        "extraction_status": row["extraction_status"],
        "ocr_confidence": row["ocr_confidence"],
        "created_at": row["created_at"],
        "access_token": None,
    }


@router.get("/{document_id}/content")
def document_content(
    document_id: int,
    token: str = Query(..., min_length=10, max_length=200),
    conn: sqlite3.Connection = Depends(db_dependency),
    settings: Settings = Depends(settings_dependency),
):
    row = documents.get_for_owner(conn, document_id, token)
    if row is None:
        raise AppError("not_found", "No document matches that id and token.").to_http()
    path = (settings.storage_dir / row["stored_name"]).resolve()
    if settings.storage_dir.resolve() not in path.parents or not path.exists():
        raise AppError("not_found", "The stored file is no longer available.").to_http()
    return FileResponse(
        path,
        media_type=row["mime_type"],
        filename=row["original_name"],
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
        },
    )
