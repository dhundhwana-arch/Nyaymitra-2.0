"""Review packet: everything a qualified reviewer must check, in one document.

The verification queue in the admin console is a work list for the operator. This module
builds the *reviewer's* packet: for each item, what is currently stored, where it came from
(so it can be opened in the source PDF), what the reviewer is being asked to confirm, and the
fields that a sign-off has to fill in.

It is deliberately boring and deterministic: same database in, same packet out, ordered by
kind and label, so two people can diff two packets and see exactly what changed.

No personal data is included. Complaints, documents and query logs are never read here.
"""
from __future__ import annotations

import json
from typing import Any

from . import glossary

CHECKLIST = {
    "article": [
        "The article text matches the official source word for word (or the summary says it is a summary).",
        "The article number and Part are correct, including suffix numbers such as 21A.",
        "The Gujarati text, if present, matches the official Gujarati edition.",
        "The citizen explanation does not overstate what the article guarantees.",
    ],
    "department": [
        "The department exists and is the right body for the stated purpose.",
        "The portal URL resolves to the official domain (not a look-alike).",
        "The phone number / e-mail is current and answered by that department.",
        "The jurisdiction label (central / state / district / taluka) is correct.",
    ],
    "triage": [
        "The steps describe the real procedure, in the right order.",
        "The documents listed are the ones actually required.",
        "The department suggested is the correct first stop.",
        "No step promises an outcome or a timeline that the law does not guarantee.",
    ],
    "glossary": [
        "The explanation is accurate and would not mislead a non-lawyer.",
        "Where the term has a statutory definition, the entry says it is not the statutory wording.",
        "The Gujarati entry says the same thing as the English entry.",
    ],
}

UNVERIFIED = ("requires_human_verification", "unverified", "outdated")


def _parse_json_list(raw: str | None) -> list[str]:
    try:
        value = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def _articles(conn) -> list[dict]:
    rows = conn.execute(
        """SELECT a.article_key, a.article_no, a.article_label, a.part_no, a.part_title,
                  a.title_en, a.title_gu, a.text_status, a.verification_status,
                  a.notes, a.checked_by, a.last_checked_at, a.source_pages, a.source_locator,
                  s.source_key, s.title AS source_title, s.url AS source_url
           FROM constitution_articles a
           LEFT JOIN legal_sources s ON s.id = a.source_id
           WHERE a.verification_status != 'verified'
           ORDER BY a.sort_order, a.article_no"""
    ).fetchall()
    items = []
    for row in rows:
        items.append({
            "kind": "article",
            "ref": row["article_label"] or row["article_no"],
            "key": row["article_key"],
            "part": row["part_no"],
            "title_en": row["title_en"],
            "title_gu": row["title_gu"],
            "text_status": row["text_status"],
            "verification_status": row["verification_status"],
            "notes": row["notes"],
            "previously_checked_by": row["checked_by"],
            "last_checked_at": row["last_checked_at"],
            "source": {
                "key": row["source_key"],
                "title": row["source_title"],
                "url": row["source_url"],
                "pages": row["source_pages"],
                "locator": row["source_locator"],
            },
            "has_authoritative_text": row["text_status"] == "verified_source_text",
            "checklist": CHECKLIST["article"],
            "sign_off_fields": ["checked_by", "checked_on", "source_consulted", "notes"],
        })
    return items


def _departments(conn) -> list[dict]:
    rows = conn.execute(
        """SELECT d.department_key, d.name_en, d.name_gu, d.jurisdiction, d.purpose_en,
                  d.portal_url, d.helpline, d.email, d.address, d.verification_status,
                  d.verified_on, d.verified_by, s.source_key, s.url AS source_url
           FROM departments d
           LEFT JOIN legal_sources s ON s.id = d.source_id
           WHERE d.verification_status != 'verified'
           ORDER BY d.department_key"""
    ).fetchall()
    return [
        {
            "kind": "department",
            "ref": row["department_key"],
            "key": row["department_key"],
            "name_en": row["name_en"],
            "name_gu": row["name_gu"],
            "jurisdiction": row["jurisdiction"],
            "purpose_en": row["purpose_en"],
            "contact": {
                "portal_url": row["portal_url"],
                "helpline": row["helpline"],
                "email": row["email"],
                "address": row["address"],
            },
            "verification_status": row["verification_status"],
            "verified_on": row["verified_on"],
            "verified_by": row["verified_by"],
            "source": {"key": row["source_key"], "url": row["source_url"]},
            "checklist": CHECKLIST["department"],
            "sign_off_fields": ["checked_by", "checked_on", "source_consulted", "notes"],
        }
        for row in rows
    ]


def _triage(conn) -> list[dict]:
    rows = conn.execute(
        """SELECT t.guide_key, t.category_en, t.category_gu, t.summary_en, t.steps_en,
                  t.documents_en, t.department_key, t.verification_status,
                  t.last_checked_at, s.source_key, s.url AS source_url
           FROM triage_guides t
           LEFT JOIN legal_sources s ON s.id = t.source_id
           WHERE t.verification_status != 'verified'
           ORDER BY t.guide_key"""
    ).fetchall()
    return [
        {
            "kind": "triage",
            "ref": row["guide_key"],
            "key": row["guide_key"],
            "category_en": row["category_en"],
            "category_gu": row["category_gu"],
            "summary_en": row["summary_en"],
            "steps": _parse_json_list(row["steps_en"]),
            "documents": _parse_json_list(row["documents_en"]),
            "department_key": row["department_key"],
            "verification_status": row["verification_status"],
            "last_checked_at": row["last_checked_at"],
            "source": {"key": row["source_key"], "url": row["source_url"]},
            "checklist": CHECKLIST["triage"],
            "sign_off_fields": ["checked_by", "checked_on", "source_consulted", "notes"],
        }
        for row in rows
    ]


def _glossary_items() -> list[dict]:
    """Glossary entries are seed data with no per-row verification column.

    They are included so the reviewer sees them, but the packet is explicit that marking them
    verified is not possible yet — the honest status is "not reviewable in the product".
    """
    try:
        entries = glossary.all_terms()
    except Exception:  # noqa: BLE001 - a missing seed file must not break the packet
        return []
    items = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        term = entry.get("term_en") or entry.get("term") or entry.get("key")
        items.append({
            "kind": "glossary",
            "ref": term,
            "key": entry.get("key") or term,
            "term_en": entry.get("term_en") or entry.get("term"),
            "term_gu": entry.get("term_gu"),
            "explanation_en": entry.get("explanation_en"),
            "explanation_gu": entry.get("explanation_gu"),
            "verification_status": "not_reviewable_in_product",
            "checklist": CHECKLIST["glossary"],
            "sign_off_fields": ["checked_by", "checked_on", "notes"],
        })
    return items


def build(conn, *, kinds: tuple[str, ...] | None = None) -> dict:
    """Build the packet. ``kinds`` limits which item types are included."""
    wanted = kinds or ("article", "department", "triage", "glossary")
    items: list[dict[str, Any]] = []
    if "article" in wanted:
        items.extend(_articles(conn))
    if "department" in wanted:
        items.extend(_departments(conn))
    if "triage" in wanted:
        items.extend(_triage(conn))
    if "glossary" in wanted:
        items.extend(_glossary_items())

    by_kind: dict[str, int] = {}
    for item in items:
        by_kind[item["kind"]] = by_kind.get(item["kind"], 0) + 1

    return {
        "generated_at": _now(conn),
        "items": items,
        "counts": by_kind,
        "total": len(items),
        "instructions": [
            "Every item below is unverified. Nothing here is presented to citizens as checked.",
            "Open the source document at the locator given and compare against the stored text.",
            "Record who checked it, when, and which source was consulted; a sign-off without a"
            " source is not a sign-off.",
            "If an item cannot be checked, change its status to 'unverified' with a note — do not"
            " leave it looking checked.",
            "Glossary entries cannot be marked verified in the product yet; report corrections to"
            " the maintainer instead.",
        ],
        "disclaimer": (
            "Research prototype. Legal content has not been verified by a qualified reviewer, and"
            " this packet is a work order, not a verification record."
        ),
    }


def _now(conn) -> str:
    row = conn.execute("SELECT datetime('now') AS now").fetchone()
    return row["now"] if row else ""


def to_markdown(packet: dict) -> str:
    """Render the packet as a reviewable document (checkboxes, sources, sign-off lines)."""
    lines = [
        "# Review packet — legal content verification",
        "",
        f"Generated: {packet['generated_at']} (UTC, from the database)",
        "",
        f"Items requiring review: **{packet['total']}** — "
        + ", ".join(f"{kind}: {count}" for kind, count in sorted(packet["counts"].items())),
        "",
        "> " + packet["disclaimer"],
        "",
        "## How to use this packet",
        "",
    ]
    lines += [f"{index}. {step}" for index, step in enumerate(packet["instructions"], start=1)]

    for kind in ("article", "department", "triage", "glossary"):
        group = [item for item in packet["items"] if item["kind"] == kind]
        if not group:
            continue
        lines += ["", f"## {kind.capitalize()}s ({len(group)})", ""]
        for item in group:
            lines += _item_markdown(item)
    lines.append("")
    return "\n".join(lines)


def _item_markdown(item: dict) -> list[str]:
    lines = [f"### {item['ref']} — {item.get('title_en') or item.get('name_en') or item.get('category_en') or ''}".rstrip(" —")]
    lines.append("")
    if item["kind"] == "article":
        lines.append(f"- Part: {item.get('part') or 'unassigned'} · "
                     f"text status: `{item.get('text_status')}` · "
                     f"authoritative text: {'yes' if item.get('has_authoritative_text') else 'no'}")
    if item.get("source"):
        source = item["source"]
        location = source.get("locator") or (f"pages {source['pages']}" if source.get("pages") else "location not recorded")
        lines.append(f"- Source: {source.get('title') or source.get('key') or 'unknown'} — {location}")
        if source.get("url"):
            lines.append(f"- Source URL: {source['url']}")
    if item.get("contact"):
        contact = {key: value for key, value in item["contact"].items() if value}
        if contact:
            lines.append("- Contact on record: " + "; ".join(f"{k}={v}" for k, v in contact.items()))
    if item.get("steps"):
        lines.append("- Steps on record: " + " → ".join(item["steps"]))
    if item.get("documents"):
        lines.append("- Documents on record: " + ", ".join(item["documents"]))
    lines.append(f"- Current status: `{item['verification_status']}`")
    lines.append("")
    lines.append("Checklist:")
    lines += [f"- [ ] {question}" for question in item["checklist"]]
    lines.append("")
    lines.append("Sign-off:")
    lines += [f"- {field}: ______________________" for field in item["sign_off_fields"]]
    lines.append("")
    return lines
