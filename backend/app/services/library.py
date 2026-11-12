"""Legal Library: one read-only listing over the datasets that already exist.

No new tables. Items are read from ``constitution_articles``, ``triage_guides``,
``departments`` and the curated glossary file. Each item says what kind of content it is
(official text vs. owner-written explanation) so a summary is never presented as law.
The quarantined ``legacy_import_chunks`` (Santali fragments) are deliberately excluded.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from . import constitution, glossary, textsearch

CATEGORIES = ("constitution", "guide", "department", "glossary")
OWNER_SUMMARY = "owner_authored_summary"


def _loads(value: str | None) -> list:
    try:
        data = json.loads(value or "[]")
        return data if isinstance(data, list) else []
    except ValueError:
        return []


def _source(conn: sqlite3.Connection, source_id: int | None, url: str | None = None) -> dict | None:
    src = constitution.get_source(conn, source_id)
    if not src and not url:
        return None
    src = src or {}
    return {
        "source_key": src.get("source_key"),
        "title": src.get("title"),
        "publisher": src.get("publisher"),
        "source_type": src.get("source_type"),
        "url": url or src.get("url"),
        "retrieved_on": src.get("retrieved_on"),
    }


def _item(category: str, key: str, **fields: Any) -> dict[str, Any]:
    body_en, body_gu = fields.get("body_en") or "", fields.get("body_gu") or ""
    return {
        "id": f"{category}:{key}",
        "category": category,
        "key": key,
        "label": fields.get("label"),
        "group": fields.get("group"),
        "title_en": fields.get("title_en"),
        "title_gu": fields.get("title_gu"),
        "body_en": body_en or None,
        "body_gu": body_gu or None,
        "list_en": fields.get("list_en") or [],
        "list_gu": fields.get("list_gu") or [],
        "languages": [lang for lang, body, title in (("en", body_en, fields.get("title_en")),
                                                      ("gu", body_gu, fields.get("title_gu"))) if body or title],
        "content_kind": fields.get("content_kind", OWNER_SUMMARY),
        "verification_status": fields.get("verification_status", "requires_human_verification"),
        "source": fields.get("source"),
        "source_locator": fields.get("source_locator"),
        "contact": fields.get("contact"),
    }


def _all_items(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for r in conn.execute("SELECT * FROM constitution_articles ORDER BY sort_order, id"):
        official = r["text_status"] == "verified_source_text"
        items.append(_item(
            "constitution", r["article_no"], label=r["article_label"],
            group=" — ".join(x for x in ((f"Part {r['part_no']}" if r["part_no"] else None), r["part_title"]) if x),
            title_en=r["title_en"], title_gu=r["title_gu"],
            body_en=(r["text_en"] if official else None) or r["citizen_explanation_en"],
            body_gu=(r["text_gu"] if official else None) or r["citizen_explanation_gu"],
            content_kind=r["text_status"], verification_status=r["verification_status"],
            source=_source(conn, r["source_id"], r["source_url"]),
            source_locator=(f"pages {r['source_pages']}" if r["source_pages"] else r["source_locator"]),
        ))
    for r in conn.execute("SELECT * FROM triage_guides ORDER BY id"):
        items.append(_item(
            "guide", r["guide_key"], title_en=r["category_en"], title_gu=r["category_gu"],
            body_en=r["summary_en"], body_gu=r["summary_gu"],
            list_en=_loads(r["steps_en"]), list_gu=_loads(r["steps_gu"]),
            verification_status=r["verification_status"], source=_source(conn, r["source_id"]),
        ))
    for r in conn.execute("SELECT * FROM departments ORDER BY id"):
        items.append(_item(
            "department", r["department_key"], group=r["jurisdiction"],
            title_en=r["name_en"], title_gu=r["name_gu"], body_en=r["purpose_en"], body_gu=r["purpose_gu"],
            verification_status=r["verification_status"], source=_source(conn, r["source_id"]),
            contact={"portal_url": r["portal_url"], "portal_label": r["portal_label"], "helpline": r["helpline"]},
        ))
    for term in glossary.all_terms():
        items.append(_item(
            "glossary", term["key"], title_en=term["term_en"], title_gu=term["term_gu"],
            body_en=term["explanation_en"], body_gu=term["explanation_gu"],
        ))
    return items


def _haystack(item: dict[str, Any]) -> str:
    parts = [item["label"], item["key"], item["group"], item["title_en"], item["title_gu"],
             item["body_en"], item["body_gu"], *item["list_en"], *item["list_gu"]]
    return " ".join(str(p) for p in parts if p).lower()


def _summary(item: dict[str, Any], language: str) -> dict[str, Any]:
    other = "en" if language == "gu" else "gu"
    body = item[f"body_{language}"] or item[f"body_{other}"] or ""
    return {
        "id": item["id"], "category": item["category"], "key": item["key"], "label": item["label"],
        "group": item["group"],
        "title": item[f"title_{language}"] or item[f"title_{other}"],
        "snippet": (body[:220] + "…") if len(body) > 220 else (body or None),
        "languages": item["languages"], "content_kind": item["content_kind"],
        "verification_status": item["verification_status"], "source": item["source"],
    }


def search(conn: sqlite3.Connection, *, query: str | None, language: str, category: str | None,
           content_language: str | None, page: int, page_size: int) -> dict[str, Any]:
    items = _all_items(conn)
    if content_language:
        items = [i for i in items if i[f"body_{content_language}"]]
    q = (query or "").strip()
    if q:
        tokens = textsearch.significant_tokens(q, min_len=2) or [q.lower()]
        need = len(tokens) if len(tokens) <= 2 else (len(tokens) + 1) // 2
        scored = []
        for n, i in enumerate(items):
            hits = textsearch.match_count(_haystack(i), tokens)
            if hits >= need:  # a title/label hit ranks above a hit in the body only
                title = " ".join(str(x) for x in (i["label"], i["title_en"], i["title_gu"]) if x)
                scored.append((hits + 2 * textsearch.match_count(title, tokens), n, i))
        scored.sort(key=lambda s: (-s[0], s[1]))
        items = [s[2] for s in scored]
    facets = {c: sum(1 for i in items if i["category"] == c) for c in CATEGORIES}
    if category:
        items = [i for i in items if i["category"] == category]
    start = (page - 1) * page_size
    return {
        "query": q or None, "language": language, "category": category,
        "content_language": content_language, "total": len(items), "page": page, "page_size": page_size,
        "facets": facets, "items": [_summary(i, language) for i in items[start:start + page_size]],
        "official_text_available": any(i["content_kind"] == "verified_source_text" for i in items),
        "notice": (
            "Everything listed is stored in the NYAYMITRA database. Items marked "
            "'owner_authored_summary' are explanations written by the project owner, not the "
            "official text of any law. Uploaded/OCR documents are private to their uploader and "
            "are not part of this public library."
        ),
    }


def get_item(conn: sqlite3.Connection, category: str, key: str) -> dict[str, Any] | None:
    for item in _all_items(conn):
        if item["category"] == category and item["key"].lower() == key.lower():
            return item
    return None
