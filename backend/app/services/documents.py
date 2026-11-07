"""Document upload, validation and text extraction.

Files are stored under a random name inside ``settings.storage_dir``; the user-supplied
filename is kept only as a display label. Extraction is best-effort and never invents
text: when OCR is unavailable the record says so.
"""
from __future__ import annotations

import hashlib
import io
import logging
import secrets
import sqlite3
from pathlib import Path
from typing import Any

from ..config import Settings
from ..errors import AppError
from ..security import hash_token, sanitize_original_name, storage_name_for, validate_upload

log = logging.getLogger(__name__)

MAX_EXTRACT_PAGES = 5
MAX_EXTRACT_CHARS = 20_000
MAX_EXTRACT_SOURCE_BYTES = 8 * 1024 * 1024


def _extract_pdf_text(content: bytes) -> tuple[str | None, str]:
    if len(content) > MAX_EXTRACT_SOURCE_BYTES:
        return None, "too_large"
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover - dependency is pinned
        return None, "extraction_failed"
    try:
        reader = PdfReader(io.BytesIO(content))
        chunks: list[str] = []
        for page in reader.pages[:MAX_EXTRACT_PAGES]:
            chunks.append(page.extract_text() or "")
            if sum(len(c) for c in chunks) > MAX_EXTRACT_CHARS:
                break
        text = "\n".join(chunks).strip()
        if not text:
            # A PDF with no text layer is a scan: extracting it needs OCR, which is not
            # installed. Say so instead of returning an empty document.
            return None, "ocr_unavailable"
        return text[:MAX_EXTRACT_CHARS], "extracted"
    except Exception as exc:  # noqa: BLE001 - third-party parser can raise anything
        log.warning("pdf extraction failed: %s", type(exc).__name__)
        return None, "extraction_failed"


def save_upload(
    conn: sqlite3.Connection,
    settings: Settings,
    *,
    filename: str | None,
    content_type: str | None,
    content: bytes,
    document_kind: str = "evidence",
) -> dict[str, Any]:
    head = content[:64]
    check = validate_upload(
        original_name=filename,
        declared_mime=content_type,
        size=len(content),
        head=head,
        settings=settings,
    )
    if not check.ok:
        raise AppError(check.code or "unsupported_media_type", check.message)

    mime = check.mime or "application/octet-stream"
    stored_name = storage_name_for(mime)
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    target = (settings.storage_dir / stored_name).resolve()
    if settings.storage_dir.resolve() not in target.parents:
        raise AppError("bad_request", "Invalid storage path.")
    target.write_bytes(content)

    digest = hashlib.sha256(content).hexdigest()
    token = secrets.token_urlsafe(24)
    extracted, status = (None, "not_processed")
    confidence = None
    if mime == "application/pdf":
        extracted, status = _extract_pdf_text(content)
    else:
        status = "ocr_unavailable"  # image OCR is not installed (see KNOWN_LIMITATIONS)

    cur = conn.execute(
        """INSERT INTO documents (stored_name, original_name, mime_type, size_bytes, sha256,
                                 document_kind, owner_token_hash, extracted_text,
                                 extraction_status, ocr_confidence)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            stored_name,
            sanitize_original_name(filename),
            mime,
            len(content),
            digest,
            document_kind if document_kind in {"evidence", "identity", "legal_notice", "other"} else "other",
            hash_token(token),
            extracted,
            status,
            confidence,
        ),
    )
    return {
        "id": int(cur.lastrowid),
        "original_name": sanitize_original_name(filename),
        "mime_type": mime,
        "size_bytes": len(content),
        "sha256": digest,
        "extraction_status": status,
        "ocr_confidence": confidence,
        "created_at": "",
        "access_token": token,
    }


def get_for_owner(conn: sqlite3.Connection, document_id: int, token: str) -> dict | None:
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
    if row is None or not secrets.compare_digest(row["owner_token_hash"], hash_token(token)):
        return None
    return dict(row)


def attach(conn: sqlite3.Connection, document_id: int, token: str, complaint_id: int,
           complaint_token: str) -> bool:
    cur = conn.execute(
        """UPDATE documents SET complaint_id = ?, owner_token_hash = ?
           WHERE id = ? AND owner_token_hash = ?""",
        (complaint_id, hash_token(complaint_token), document_id, hash_token(token)),
    )
    return cur.rowcount > 0


def delete_file(settings: Settings, stored_name: str) -> None:
    path = (settings.storage_dir / stored_name).resolve()
    if settings.storage_dir.resolve() in path.parents and path.exists():
        path.unlink()
