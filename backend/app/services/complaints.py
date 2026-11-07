"""Complaint intake, deterministic summary and token-gated retrieval.

Privacy model
-------------
* The complainant receives a reference (``NYM-XXXXXX``) and a random access token.
* Only ``sha256(token)`` is stored; the plaintext token exists solely in the response.
* There is no endpoint that lists complaints to the public, and admin listings return
  metadata only (no free-text description, no contact details).
"""
from __future__ import annotations

import re
import secrets
import sqlite3
from datetime import datetime, timezone
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
) -> dict[str, Any]:
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
    now = _now()
    cur = conn.execute(
        """
        INSERT INTO complaints
            (reference, access_token_hash, language, category, title, description, summary,
             incident_date, location, district, state, respondent, contact_phone, contact_email,
             consent_given, status, submitted_at, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
            now,
            now,
            now,
        ),
    )
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
        "created_at": now,
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
