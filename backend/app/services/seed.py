"""Idempotent seed loading from ``data/seed/*.json``.

Seeding never overwrites a human decision: an existing row's ``verification_status``,
``last_checked_at`` and ``checked_by`` are preserved (only descriptive fields refresh).
"""
from __future__ import annotations

import gzip
import json
import sqlite3
from pathlib import Path

from ..config import Settings, get_settings
from ..db import get_db, transaction


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def upsert_sources(conn: sqlite3.Connection, payload: dict) -> int:
    rows = payload.get("sources", [])
    for src in rows:
        conn.execute(
            """
            INSERT INTO legal_sources (source_key, title, publisher, source_type, url,
                                       document_ref, published_on, retrieved_on, licence_note, notes)
            VALUES (:source_key, :title, :publisher, :source_type, :url, :document_ref,
                    :published_on, :retrieved_on, :licence_note, :notes)
            ON CONFLICT(source_key) DO UPDATE SET
                title = excluded.title,
                publisher = excluded.publisher,
                source_type = excluded.source_type,
                url = excluded.url,
                document_ref = excluded.document_ref,
                published_on = excluded.published_on,
                retrieved_on = COALESCE(excluded.retrieved_on, legal_sources.retrieved_on),
                licence_note = excluded.licence_note,
                notes = excluded.notes
            """,
            {
                "source_key": src["source_key"],
                "title": src["title"],
                "publisher": src["publisher"],
                "source_type": src["source_type"],
                "url": src.get("url"),
                "document_ref": src.get("document_ref"),
                "published_on": src.get("published_on"),
                "retrieved_on": src.get("retrieved_on"),
                "licence_note": src.get("licence_note"),
                "notes": src.get("notes"),
            },
        )
    return len(rows)


def upsert_articles(conn: sqlite3.Connection, payload: dict) -> int:
    articles = payload.get("articles", [])
    for art in articles:
        source_id = conn.execute(
            "SELECT id FROM legal_sources WHERE source_key = ?", (art.get("source_key"),)
        ).fetchone()
        source_id = source_id["id"] if source_id else None
        conn.execute(
            """
            INSERT INTO constitution_articles
                (article_key, article_no, article_label, part_no, part_title, chapter_title,
                 title_en, title_gu, text_en, text_gu,
                 citizen_explanation_en, citizen_explanation_gu,
                 text_status, verification_status, source_id, source_locator, source_url,
                 last_checked_at, notes, sort_order)
            VALUES (:article_key, :article_no, :article_label, :part_no, :part_title, :chapter_title,
                    :title_en, :title_gu, :text_en, :text_gu,
                    :citizen_explanation_en, :citizen_explanation_gu,
                    :text_status, :verification_status, :source_id, :source_locator, :source_url,
                    :last_checked_at, :notes, :sort_order)
            ON CONFLICT(article_key) DO UPDATE SET
                article_no = excluded.article_no,
                article_label = excluded.article_label,
                part_no = excluded.part_no,
                part_title = excluded.part_title,
                chapter_title = excluded.chapter_title,
                title_en = COALESCE(excluded.title_en, constitution_articles.title_en),
                title_gu = COALESCE(excluded.title_gu, constitution_articles.title_gu),
                -- never let a seed overwrite text that a human already verified
                text_en = CASE WHEN constitution_articles.verification_status = 'verified'
                               THEN constitution_articles.text_en
                               ELSE COALESCE(excluded.text_en, constitution_articles.text_en) END,
                text_gu = CASE WHEN constitution_articles.verification_status = 'verified'
                               THEN constitution_articles.text_gu
                               ELSE COALESCE(excluded.text_gu, constitution_articles.text_gu) END,
                citizen_explanation_en = COALESCE(excluded.citizen_explanation_en, constitution_articles.citizen_explanation_en),
                citizen_explanation_gu = COALESCE(excluded.citizen_explanation_gu, constitution_articles.citizen_explanation_gu),
                text_status = CASE WHEN constitution_articles.text_status = 'verified_source_text'
                                   THEN constitution_articles.text_status
                                   ELSE excluded.text_status END,
                source_id = COALESCE(excluded.source_id, constitution_articles.source_id),
                source_locator = COALESCE(excluded.source_locator, constitution_articles.source_locator),
                source_url = COALESCE(excluded.source_url, constitution_articles.source_url),
                notes = COALESCE(excluded.notes, constitution_articles.notes),
                sort_order = excluded.sort_order,
                updated_at = datetime('now')
            """,
            {
                "article_key": art["article_key"],
                "article_no": art["article_no"],
                "article_label": art["article_label"],
                "part_no": art.get("part_no"),
                "part_title": art.get("part_title"),
                "chapter_title": art.get("chapter_title"),
                "title_en": art.get("title_en"),
                "title_gu": art.get("title_gu"),
                "text_en": art.get("text_en"),
                "text_gu": art.get("text_gu"),
                "citizen_explanation_en": art.get("citizen_explanation_en"),
                "citizen_explanation_gu": art.get("citizen_explanation_gu"),
                "text_status": art.get("text_status", "not_available"),
                "verification_status": art.get("verification_status", "requires_human_verification"),
                "source_id": source_id,
                "source_locator": art.get("source_locator"),
                "source_url": art.get("source_url"),
                "last_checked_at": art.get("last_checked_at"),
                "notes": art.get("notes"),
                "sort_order": art.get("sort_order", 0),
            },
        )
        if source_id:
            article_id = conn.execute(
                "SELECT id FROM constitution_articles WHERE article_key = ?", (art["article_key"],)
            ).fetchone()["id"]
            conn.execute(
                """INSERT INTO article_sources (article_id, source_id, locator, note)
                   VALUES (?,?,?,?)
                   ON CONFLICT(article_id, source_id) DO UPDATE SET locator = excluded.locator""",
                (article_id, source_id, art.get("source_locator"), art.get("notes")),
            )
    return len(articles)


def upsert_departments(conn: sqlite3.Connection, payload: dict) -> int:
    rows = payload.get("departments", [])
    for dep in rows:
        source = conn.execute(
            "SELECT id FROM legal_sources WHERE source_key = ?", (dep.get("source_key"),)
        ).fetchone()
        conn.execute(
            """
            INSERT INTO departments
                (department_key, name_en, name_gu, jurisdiction, purpose_en, purpose_gu,
                 portal_url, portal_label, helpline, email, address, source_id,
                 verification_status, verified_on)
            VALUES (:department_key, :name_en, :name_gu, :jurisdiction, :purpose_en, :purpose_gu,
                    :portal_url, :portal_label, :helpline, :email, :address, :source_id,
                    :verification_status, :verified_on)
            ON CONFLICT(department_key) DO UPDATE SET
                name_en = excluded.name_en,
                name_gu = excluded.name_gu,
                jurisdiction = excluded.jurisdiction,
                purpose_en = excluded.purpose_en,
                purpose_gu = excluded.purpose_gu,
                portal_url = excluded.portal_url,
                portal_label = excluded.portal_label,
                helpline = excluded.helpline,
                source_id = COALESCE(excluded.source_id, departments.source_id),
                updated_at = datetime('now')
            """,
            {
                "department_key": dep["department_key"],
                "name_en": dep["name_en"],
                "name_gu": dep["name_gu"],
                "jurisdiction": dep.get("jurisdiction"),
                "purpose_en": dep.get("purpose_en"),
                "purpose_gu": dep.get("purpose_gu"),
                "portal_url": dep.get("portal_url"),
                "portal_label": dep.get("portal_label"),
                "helpline": dep.get("helpline"),
                "email": dep.get("email"),
                "address": dep.get("address"),
                "source_id": source["id"] if source else None,
                "verification_status": dep.get("verification_status", "requires_human_verification"),
                "verified_on": dep.get("verified_on"),
            },
        )
    return len(rows)


def upsert_triage(conn: sqlite3.Connection, payload: dict) -> int:
    rows = payload.get("guides", [])
    for guide in rows:
        source = conn.execute(
            "SELECT id FROM legal_sources WHERE source_key = ?", (guide.get("source_key", "owner-authored-citizen-notes"),)
        ).fetchone()
        conn.execute(
            """
            INSERT INTO triage_guides
                (guide_key, category_en, category_gu, summary_en, summary_gu, steps_en, steps_gu,
                 documents_en, documents_gu, keywords, department_key, source_id, verification_status)
            VALUES (:guide_key, :category_en, :category_gu, :summary_en, :summary_gu, :steps_en,
                    :steps_gu, :documents_en, :documents_gu, :keywords, :department_key, :source_id,
                    :verification_status)
            ON CONFLICT(guide_key) DO UPDATE SET
                category_en = excluded.category_en,
                category_gu = excluded.category_gu,
                summary_en = excluded.summary_en,
                summary_gu = excluded.summary_gu,
                steps_en = excluded.steps_en,
                steps_gu = excluded.steps_gu,
                documents_en = excluded.documents_en,
                documents_gu = excluded.documents_gu,
                keywords = excluded.keywords,
                department_key = excluded.department_key,
                updated_at = datetime('now')
            """,
            {
                "guide_key": guide["guide_key"],
                "category_en": guide["category_en"],
                "category_gu": guide["category_gu"],
                "summary_en": guide.get("summary_en"),
                "summary_gu": guide.get("summary_gu"),
                "steps_en": json.dumps(guide.get("steps_en", []), ensure_ascii=False),
                "steps_gu": json.dumps(guide.get("steps_gu", []), ensure_ascii=False),
                "documents_en": json.dumps(guide.get("documents_en", []), ensure_ascii=False),
                "documents_gu": json.dumps(guide.get("documents_gu", []), ensure_ascii=False),
                "keywords": json.dumps(guide.get("keywords", []), ensure_ascii=False),
                "department_key": guide.get("department_key"),
                "source_id": source["id"] if source else None,
                "verification_status": guide.get("verification_status", "requires_human_verification"),
            },
        )
    return len(rows)


def import_legacy_chunks(conn: sqlite3.Connection, settings: Settings) -> int:
    """Mirror the archived legacy rows into ``legacy_import_chunks`` (admin-only).

    Idempotent: skipped when the table already holds the archive. This keeps the
    quarantined text inside the database for auditing without exposing it.
    """
    existing = conn.execute("SELECT COUNT(*) AS n FROM legacy_import_chunks").fetchone()["n"]
    if existing:
        return 0
    archive = next(iter(sorted(settings.legacy_dir.glob("constitution_articles_legacy_*.jsonl.gz"))), None)
    if archive is None:
        return 0
    inserted = 0
    with gzip.open(archive, "rt", encoding="utf-8") as fh:
        for line in fh:
            record = json.loads(line)
            if "_table" in record:
                continue
            conn.execute(
                """INSERT INTO legacy_import_chunks
                   (legacy_id, article_no, part, title, text, remedy_text, script, archive_ref)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    record.get("id"),
                    record.get("article_no"),
                    record.get("part"),
                    record.get("title_en"),
                    record.get("description_en"),
                    record.get("remedy_en"),
                    record.get("_script"),
                    archive.name,
                ),
            )
            inserted += 1
    return inserted


def seed_all(settings: Settings | None = None, *, include_legacy: bool = True) -> dict[str, int]:
    settings = settings or get_settings()
    seed_dir = settings.seed_dir
    result: dict[str, int] = {}
    with get_db(settings.db_path) as conn:
        with transaction(conn):
            result["sources"] = upsert_sources(conn, _load(seed_dir / "sources.json"))
            result["articles"] = upsert_articles(conn, _load(seed_dir / "constitution_seed.json"))
            result["departments"] = upsert_departments(conn, _load(seed_dir / "departments_seed.json"))
            result["triage"] = upsert_triage(conn, _load(seed_dir / "triage_seed.json"))
            if include_legacy:
                result["legacy_chunks"] = import_legacy_chunks(conn, settings)
    return result
