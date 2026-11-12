"""Government department and official complaint-channel directory."""
from __future__ import annotations

import sqlite3
from typing import Any

NOTICE = (
    "Contact details are shown with their verification status. Where the status is "
    "'requires_human_verification' or 'unverified', confirm the number or portal on the official "
    "government website before relying on it."
)


def list_departments(
    conn: sqlite3.Connection,
    *,
    jurisdiction: str | None = None,
    limit: int = 50,
) -> list[dict]:
    # Explicit column list: ``d.*, s.*`` produced two ``id`` columns and made row
    # access depend on join order.
    sql = (
        "SELECT d.department_key, d.name_en, d.name_gu, d.jurisdiction, d.purpose_en,"
        " d.purpose_gu, d.portal_url, d.portal_label, d.helpline, d.verification_status,"
        " d.verified_on, s.source_key, s.title, s.publisher, s.source_type, s.url,"
        " s.document_ref, s.published_on, s.retrieved_on"
        " FROM departments d LEFT JOIN legal_sources s ON s.id = d.source_id"
    )
    args: list[Any] = []
    if jurisdiction:
        sql += " WHERE d.jurisdiction = ?"
        args.append(jurisdiction)
    sql += " ORDER BY d.department_key LIMIT ?"
    args.append(limit)
    return [_split_row(r) for r in conn.execute(sql, args)]


def _split_row(row: sqlite3.Row) -> dict:
    # the join produces duplicate column names; read the ones we need explicitly
    dep = {
        "department_key": row["department_key"],
        "name_en": row["name_en"],
        "name_gu": row["name_gu"],
        "jurisdiction": row["jurisdiction"],
        "purpose_en": row["purpose_en"],
        "purpose_gu": row["purpose_gu"],
        "portal_url": row["portal_url"],
        "portal_label": row["portal_label"],
        "helpline": row["helpline"],
        "verification_status": row["verification_status"],
        "verified_on": row["verified_on"],
    }
    source = None
    try:
        if row["source_key"]:
            source = {
                "source_key": row["source_key"],
                "title": row["title"],
                "publisher": row["publisher"],
                "source_type": row["source_type"],
                "url": row["url"],
                "document_ref": row["document_ref"],
                "published_on": row["published_on"],
                "retrieved_on": row["retrieved_on"],
                "last_checked_at": row["verified_on"],
            }
    except (IndexError, KeyError):  # pragma: no cover - defensive
        source = None
    dep["source"] = source
    return dep


def get_department(conn: sqlite3.Connection, key: str) -> dict | None:
    rows = [d for d in list_departments(conn, limit=200) if d["department_key"] == key]
    return rows[0] if rows else None


def get_many(conn: sqlite3.Connection, keys: list[str]) -> list[dict]:
    if not keys:
        return []
    wanted = set(keys)
    return [d for d in list_departments(conn, limit=200) if d["department_key"] in wanted]
