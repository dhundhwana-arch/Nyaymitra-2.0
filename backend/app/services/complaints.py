"""Complaint intake, deterministic summary and token-gated retrieval.

Privacy model
-------------
* The complainant receives a reference (``NYM-XXXXXX``) and a random access token.
* Only ``sha256(token)`` is stored; the plaintext token exists solely in the response.
* There is no endpoint that lists complaints to the public, and admin listings return
  metadata only (no free-text description, no contact details).
"""
from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from ..security import hash_token

CATEGORY_LABELS: dict[str, dict[str, str]] = {
    "cyber_fraud": {
        "en": "Online financial fraud / cyber crime",
        "gu": "ઓનલાઇન નાણાકીય છેતરપિંડી / સાયબર ગુનો",
    },
    "land_revenue": {
        "en": "Land records, boundary or revenue matter",
        "gu": "જમીન રેકોર્ડ, સીમા કે મહેસૂલી બાબત",
    },
    "legal_aid": {
        "en": "Need for free legal aid / lawyer",
        "gu": "મફત કાનૂની સહાય / વકીલની જરૂર",
    },
    "consumer": {"en": "Consumer complaint", "gu": "ગ્રાહક ફરિયાદ"},
    "government_grievance": {
        "en": "Government application or grievance",
        "gu": "સરકારી અરજી કે ફરિયાદ",
    },
    "women_safety": {"en": "Women's safety", "gu": "મહિલા સુરક્ષા"},
    "labour": {"en": "Labour / wages", "gu": "શ્રમ / વેતન"},
    "other": {"en": "Other", "gu": "અન્ય"},
}

NOTICE = (
    "Saved on this server under the reference below. NYAYMITRA does not file the complaint with "
    "any department. Use the reference and access token to view it again, then submit it yourself "
    "through the official channel listed in the next steps."
)

REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

#: Short window in which an *identical* submission is treated as a retry rather than a
#: new complaint. Deliberately short: a citizen may legitimately file the same problem
#: again later, so the window only covers double-clicks and timeouts.
DEFAULT_DUPLICATE_WINDOW_S = 600


class DuplicateSubmission(Exception):
    """Raised when this submission is a retry of one that already succeeded.

    Carries the existing reference so the client can show it instead of creating a
    second complaint. The access token is deliberately NOT returned again — the server
    only stores its hash, so a retry cannot leak a token to whoever sent it.
    """

    def __init__(self, reference: str, reason: str = "duplicate_submission") -> None:
        self.reference = reference
        self.reason = reason
        super().__init__(f"duplicate submission: {reference}")


_WHITESPACE = re.compile(r"\s+")


def fingerprint(payload: dict[str, Any]) -> str:
    """Stable hash of the substantive fields, used to detect an immediate retry."""
    parts = [
        str(payload.get("language") or ""),
        str(payload.get("category") or ""),
        _WHITESPACE.sub(" ", str(payload.get("title") or "")).strip().lower(),
        _WHITESPACE.sub(" ", str(payload.get("description") or "")).strip().lower(),
        str(payload.get("incident_date") or ""),
        _WHITESPACE.sub(" ", str(payload.get("location") or "")).strip().lower(),
        _WHITESPACE.sub(" ", str(payload.get("district") or "")).strip().lower(),
        _WHITESPACE.sub(" ", str(payload.get("state") or "")).strip().lower(),
    ]
    return hashlib.sha256("\x31".join(parts).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_reference(conn: sqlite3.Connection) -> str:
    for _ in range(12):
        suffix = "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(6))
        reference = f"NYM-{suffix}"
        exists = conn.execute(
            "SELECT 1 FROM complaints WHERE reference = ?", (reference,)
        ).fetchone()
        if not exists:
            return reference
    raise RuntimeError("could not allocate a unique complaint reference")


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?।])\s+")


def build_summary(*, language: str, category: str, title: str, description: str,
                  incident_date: str | None, location: str | None,
                  district: str | None, state: str | None) -> str:
    """Deterministic, extractive summary — no model, so nothing can be invented.

    It re-uses only the words the complainant wrote, plus the category label.
    """
    lang = "gu" if language == "gu" else "en"
    label = CATEGORY_LABELS.get(category, CATEGORY_LABELS["other"])[lang]
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(description.strip()) if s.strip()]
    body = " ".join(sentences[:2])
    place = ", ".join(part for part in (location, district, state) if part)
    if lang == "gu":
        parts = [f"શ્રેણી: {label}.", f"વિષય: {title}."]
        if body:
            parts.append(body)
        if incident_date:
            parts.append(f"બનાવની તારીખ: {incident_date}.")
        if place:
            parts.append(f"સ્થળ: {place}.")
        parts.append("આ સારાંશ તમારા જ લખાણમાંથી બનાવેલ છે; કોઈ કાનૂની નિર્ણય સામેલ નથી.")
    else:
        parts = [f"Category: {label}.", f"Subject: {title}."]
        if body:
            parts.append(body)
        if incident_date:
            parts.append(f"Incident date: {incident_date}.")
        if place:
            parts.append(f"Place: {place}.")
        parts.append("This summary is built only from your own words and contains no legal decision.")
    return " ".join(parts)


def create(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    document_refs: list[dict] | None = None,
    duplicate_window_s: int = DEFAULT_DUPLICATE_WINDOW_S,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Insert a complaint, refusing retries.

    Guards:

    1. ``client_request_id`` is unique — the same key can never create two rows, so a
       double-click or a timeout retry returns the reference of the complaint that was
       already created.
    2. When the client sends **no** key (curl, older clients), an identical payload
       inside ``duplicate_window_s`` is treated as a retry. With a key present this
       check is skipped on purpose: a shared kiosk may legitimately file two identical
       complaints for two people in the same session.
    """
    client_request_id = payload.get("client_request_id") or None
    if client_request_id:
        existing = conn.execute(
            "SELECT reference FROM complaints WHERE client_request_id = ?",
            (client_request_id,),
        ).fetchone()
        if existing:
            raise DuplicateSubmission(existing["reference"], "same_client_request_id")

    fp = fingerprint(payload)
    if not client_request_id:
        moment = now or datetime.now(timezone.utc)
        cutoff = (moment - timedelta(seconds=max(1, duplicate_window_s))).replace(
            microsecond=0
        ).isoformat()
        recent = conn.execute(
            "SELECT reference FROM complaints WHERE fingerprint = ? AND created_at >= ?"
            " ORDER BY id DESC LIMIT 1",
            (fp, cutoff),
        ).fetchone()
        if recent:
            raise DuplicateSubmission(recent["reference"], "identical_recent_submission")

    reference = new_reference(conn)
    token = secrets.token_urlsafe(24)
    summary = build_summary(
        language=payload["language"],
        category=payload["category"],
        title=payload["title"],
        description=payload["description"],
        incident_date=str(payload["incident_date"]) if payload.get("incident_date") else None,
        location=payload.get("location"),
        district=payload.get("district"),
        state=payload.get("state"),
    )
    now_text = _now()
    try:
        cur = conn.execute(
            """
            INSERT INTO complaints
                (reference, access_token_hash, language, category, title, description, summary,
                 incident_date, location, district, state, respondent, contact_phone, contact_email,
                 consent_given, status, submitted_at, created_at, updated_at,
                 client_request_id, fingerprint)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                reference,
                hash_token(token),
                payload["language"],
                payload["category"],
                payload["title"],
                payload["description"],
                summary,
                str(payload["incident_date"]) if payload.get("incident_date") else None,
                payload.get("location"),
                payload.get("district"),
                payload.get("state"),
                payload.get("respondent"),
                payload.get("contact_phone"),
                str(payload["contact_email"]) if payload.get("contact_email") else None,
                1 if payload.get("consent") else 0,
                "submitted",
                now_text,
                now_text,
                now_text,
                client_request_id,
                fp,
            ),
        )
    except sqlite3.IntegrityError:
        # Two concurrent retries can pass the checks above; the unique index is the
        # authority. Surface the winner's reference instead of a 500.
        existing = conn.execute(
            "SELECT reference FROM complaints WHERE client_request_id = ?",
            (client_request_id,),
        ).fetchone()
        if existing:
            raise DuplicateSubmission(existing["reference"], "same_client_request_id") from None
        raise
    complaint_id = int(cur.lastrowid)

    for ref in document_refs or []:
        conn.execute(
            """UPDATE documents SET complaint_id = ?, owner_token_hash = ?
               WHERE id = ? AND owner_token_hash = ?""",
            (complaint_id, hash_token(token), ref["id"], hash_token(ref["token"])),
        )

    return {
        "id": complaint_id,
        "reference": reference,
        "access_token": token,
        "status": "submitted",
        "created_at": now_text,
        "summary": summary,
        "category": payload["category"],
    }


def get_by_reference(conn: sqlite3.Connection, reference: str, token: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM complaints WHERE reference = ?", (reference.strip().upper(),)
    ).fetchone()
    if row is None:
        return None
    if not secrets.compare_digest(row["access_token_hash"], hash_token(token)):
        return None
    documents = [
        {
            "id": d["id"],
            "original_name": d["original_name"],
            "mime_type": d["mime_type"],
            "size_bytes": d["size_bytes"],
            "extraction_status": d["extraction_status"],
        }
        for d in conn.execute(
            "SELECT * FROM documents WHERE complaint_id = ? ORDER BY id", (row["id"],)
        )
    ]
    return {
        "reference": row["reference"],
        "language": row["language"],
        "category": row["category"],
        "title": row["title"],
        "description": row["description"],
        "summary": row["summary"],
        "incident_date": row["incident_date"],
        "location": row["location"],
        "district": row["district"],
        "state": row["state"],
        "respondent": row["respondent"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "documents": documents,
    }


def list_recent(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    """Admin view: metadata only. No description, no phone, no e-mail."""
    rows = conn.execute(
        """SELECT reference, category, language, status, incident_date, district, state, created_at
           FROM complaints ORDER BY id DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]
