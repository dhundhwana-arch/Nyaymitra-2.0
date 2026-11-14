"""Triage: map a citizen's plain-language problem to navigation guidance.

This is deliberately a deterministic keyword model over curated guides — not an LLM
decision. It decides *where to go next*, never what the legal outcome should be.
"""
from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

_TOKEN_SPLIT = re.compile(r"[\s,.;:!?()\[\]{}\"'/\\–—-]+")

#: Maps the complaint category used by the intake form to a triage guide.
CATEGORY_TO_GUIDE = {
    "cyber_fraud": "cyber-fraud",
    "land_revenue": "land-boundary",
    "legal_aid": "legal-aid",
    "consumer": "consumer-complaint",
    "government_grievance": "government-grievance",
    "women_safety": "legal-aid",
    "labour": "legal-aid",
    "other": None,
}


def _loads(value: str | None) -> list:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:  # pragma: no cover - seed data is validated in tests
        return []


def shape_guide(row: sqlite3.Row, language: str = "gu") -> dict[str, Any]:
    language = language if language in {"en", "gu"} else "gu"
    return {
        "guide_key": row["guide_key"],
        "category_en": row["category_en"],
        "category_gu": row["category_gu"],
        "summary": row[f"summary_{language}"],
        "steps": _loads(row[f"steps_{language}"]),
        "documents": _loads(row[f"documents_{language}"]),
        "department_key": row["department_key"],
        "verification_status": row["verification_status"],
        "last_checked_at": row["last_checked_at"],
    }


def all_guides(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM triage_guides ORDER BY id").fetchall()


def get_guide(conn: sqlite3.Connection, key: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM triage_guides WHERE guide_key = ?", (key,)).fetchone()


def _keyword_in(keyword: str, text: str) -> bool:
    """Latin keywords must match as whole words ("rti" is not inside "property");
    Indic keywords keep substring matching because of inflected endings."""
    if not keyword:
        return False
    if keyword.isascii():
        return re.search(r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])", text) is not None
    return keyword in text


def match(conn: sqlite3.Connection, text: str, category: str | None = None) -> sqlite3.Row | None:
    if category and category in CATEGORY_TO_GUIDE and CATEGORY_TO_GUIDE[category]:
        row = get_guide(conn, CATEGORY_TO_GUIDE[category])
        if row:
            return row
    lowered = (text or "").lower()
    best: sqlite3.Row | None = None
    best_score = 0
    for row in all_guides(conn):
        score = sum(1 for kw in _loads(row["keywords"]) if _keyword_in(str(kw).lower(), lowered))
        if score > best_score:
            best, best_score = row, score
    return best


def guide_for_category(conn: sqlite3.Connection, category: str) -> sqlite3.Row | None:
    key = CATEGORY_TO_GUIDE.get(category)
    return get_guide(conn, key) if key else None


def keywords_for(conn: sqlite3.Connection, key: str) -> list[str]:
    row = get_guide(conn, key)
    return [str(k) for k in _loads(row["keywords"])] if row else []
