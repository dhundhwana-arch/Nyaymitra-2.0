"""Idempotent seed loading from ``data/seed/*.json``.

Seeding never overwrites a human decision: an existing row's ``verification_status``,
``last_checked_at`` and ``checked_by`` are preserved (only descriptive fields refresh).

Every import run is logged: imported, skipped and failed records are tracked so that
operators can verify seeding succeeded without querying the database manually.
"""
from __future__ import annotations

import gzip
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from ..config import Settings, get_settings
from ..db import get_db, transaction

log = logging.getLogger("nyaymitra.seed")

#: Fields that must be present and non-empty in each source row.
SOURCE_REQUIRED = ("source_key", "title", "publisher", "source_type")

#: Fields that must be present and non-empty in each article row.
ARTICLE_REQUIRED = ("article_key", "article_no", "article_label")

#: Fields that must be present and non-empty in each department row.
DEPARTMENT_REQUIRED = ("department_key", "name_en", "name_gu")

#: Fields that must be present and non-empty in each triage guide row.
TRIAGE_REQUIRED = ("guide_key", "category_en", "category_gu")

#: Allowed source_type values (must match the DB CHECK constraint).
VALID_SOURCE_TYPES = {"official", "official_mirror", "third_party", "owner_authored"}

#: Allowed text_status values.
VALID_TEXT_STATUSES = {"verified_source_text", "owner_authored_summary", "not_available"}

#: Allowed verification_status values.
VALID_VERIFICATION_STATUSES = {"verified", "requires_human_verification", "unverified", "outdated"}


class SeedValidationError(RuntimeError):
    """Raised when a seed record fails validation; the run is aborted before any write."""


class SeedReport:
    """Accumulates per-table import statistics for a single seeding run."""

    def __init__(self) -> None:
        self.tables: dict[str, dict[str, int]] = {}
        self.errors: list[str] = []

    def table(self, name: str) -> dict[str, int]:
        if name not in self.tables:
            self.tables[name] = {"imported": 0, "skipped": 0, "failed": 0}
        return self.tables[name]

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        log.error("seed: %s", message)

    def summary(self) -> dict[str, Any]:
        return {
            "tables": self.tables,
            "errors": self.errors,
            "total_imported": sum(t["imported"] for t in self.tables.values()),
            "total_skipped": sum(t["skipped"] for t in self.tables.values()),
            "total_failed": sum(t["failed"] for t in self.tables.values()),
            "ok": len(self.errors) == 0,
        }

    def log_summary(self) -> None:
        s = self.summary()
        log.info(
            "seed complete: imported=%d skipped=%d failed=%d errors=%d",
            s["total_imported"],
            s["total_skipped"],
            s["total_failed"],
            len(s["errors"]),
        )
        for name, stats in s["tables"].items():
            log.info(
                "seed table %s: imported=%d skipped=%d failed=%d",
                name,
                stats["imported"],
                stats["skipped"],
                stats["failed"],
            )
        for err in s["errors"]:
            log.error("seed error: %s", err)


def _load(path: Path) -> dict:
    if not path.exists():
        log.warning("seed file missing: %s", path)
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _validate_row(
    row: dict[str, Any], required: tuple[str, ...], table_name: str, row_index: int
) -> list[str]:
    """Return a list of validation error messages (empty if the row is valid)."""
    problems: list[str] = []
    for field in required:
        value = row.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            problems.append(
                f"{table_name}[{row_index}]: missing required field '{field}'"
            )
    if table_name == "legal_sources":
        st = row.get("source_type")
        if st and st not in VALID_SOURCE_TYPES:
            problems.append(
                f"{table_name}[{row_index}]: invalid source_type '{st}' "
                f"(must be one of {sorted(VALID_SOURCE_TYPES)})"
            )
    if table_name == "constitution_articles":
        ts = row.get("text_status")
        if ts and ts not in VALID_TEXT_STATUSES:
            problems.append(
                f"{table_name}[{row_index}]: invalid text_status '{ts}' "
                f"(must be one of {sorted(VALID_TEXT_STATUSES)})"
            )
        vs = row.get("verification_status")
        if vs and vs not in VALID_VERIFICATION_STATUSES:
            problems.append(
                f"{table_name}[{row_index}]: invalid verification_status '{vs}' "
                f"(must be one of {sorted(VALID_VERIFICATION_STATUSES)})"
            )
    return problems


def upsert_sources(
    conn: sqlite3.Connection, payload: dict, report: SeedReport
) -> dict[str, int]:
    stats = report.table("legal_sources")
    rows = payload.get("sources", [])
    for index, src in enumerate(rows):
        problems = _validate_row(src, SOURCE_REQUIRED, "legal_sources", index)
        if problems:
            stats["failed"] += 1
            report.add_error("; ".join(problems))
            continue
        try:
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
            stats["imported"] += 1
        except sqlite3.Error as exc:
            stats["failed"] += 1
            report.add_error(f"legal_sources[{index}]: {exc}")
    return stats


def upsert_articles(
    conn: sqlite3.Connection, payload: dict, report: SeedReport
) -> dict[str, int]:
    stats = report.table("constitution_articles")
    articles = payload.get("articles", [])
    for index, art in enumerate(articles):
        problems = _validate_row(art, ARTICLE_REQUIRED, "constitution_articles", index)
        if problems:
            stats["failed"] += 1
            report.add_error("; ".join(problems))
            continue
        source_id = conn.execute(
            "SELECT id FROM legal_sources WHERE source_key = ?", (art.get("source_key"),)
        ).fetchone()
        source_id = source_id["id"] if source_id else None
        try:
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
            stats["imported"] += 1
            if source_id:
                article_id = conn.execute(
                    "SELECT id FROM constitution_articles WHERE article_key = ?",
                    (art["article_key"],),
                ).fetchone()["id"]
                conn.execute(
                    """INSERT INTO article_sources (article_id, source_id, locator, note)
                       VALUES (?,?,?,?)
                       ON CONFLICT(article_id, source_id) DO UPDATE SET locator = excluded.locator""",
                    (article_id, source_id, art.get("source_locator"), art.get("notes")),
                )
        except sqlite3.Error as exc:
            stats["failed"] += 1
            report.add_error(f"constitution_articles[{index}]: {exc}")
    return stats


def upsert_departments(
    conn: sqlite3.Connection, payload: dict, report: SeedReport
) -> dict[str, int]:
    stats = report.table("departments")
    rows = payload.get("departments", [])
    for index, dep in enumerate(rows):
        problems = _validate_row(dep, DEPARTMENT_REQUIRED, "departments", index)
        if problems:
            stats["failed"] += 1
            report.add_error("; ".join(problems))
            continue
        source = conn.execute(
            "SELECT id FROM legal_sources WHERE source_key = ?", (dep.get("source_key"),)
        ).fetchone()
        try:
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
            stats["imported"] += 1
        except sqlite3.Error as exc:
            stats["failed"] += 1
            report.add_error(f"departments[{index}]: {exc}")
    return stats


def upsert_triage(
    conn: sqlite3.Connection, payload: dict, report: SeedReport
) -> dict[str, int]:
    stats = report.table("triage_guides")
    rows = payload.get("guides", [])
    for index, guide in enumerate(rows):
        problems = _validate_row(guide, TRIAGE_REQUIRED, "triage_guides", index)
        if problems:
            stats["failed"] += 1
            report.add_error("; ".join(problems))
            continue
        source = conn.execute(
            "SELECT id FROM legal_sources WHERE source_key = ?",
            (guide.get("source_key", "owner-authored-citizen-notes"),),
        ).fetchone()
        try:
            conn.execute(
                """
                INSERT INTO triage_guides
                    (guide_key, category_en, category_gu, summary_en, summary_gu, steps_en,
                     steps_gu, documents_en, documents_gu, keywords, department_key, source_id,
                     verification_status)
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
            stats["imported"] += 1
        except sqlite3.Error as exc:
            stats["failed"] += 1
            report.add_error(f"triage_guides[{index}]: {exc}")
    return stats


def import_legacy_chunks(
    conn: sqlite3.Connection, settings: Settings, report: SeedReport
) -> dict[str, int]:
    """Mirror the archived legacy rows into ``legacy_import_chunks`` (admin-only).

    Idempotent: skipped when the table already holds the archive.
    """
    stats = report.table("legacy_import_chunks")
    existing = conn.execute("SELECT COUNT(*) AS n FROM legacy_import_chunks").fetchone()["n"]
    if existing:
        stats["skipped"] = 1
        log.info("seed: legacy_import_chunks already populated (%d rows), skipping", existing)
        return stats
    archive = next(iter(sorted(settings.legacy_dir.glob("constitution_articles_legacy_*.jsonl.gz"))), None)
    if archive is None:
        stats["skipped"] = 1
        log.info("seed: no legacy archive found in %s, skipping", settings.legacy_dir)
        return stats
    inserted = 0
    failed = 0
    with gzip.open(archive, "rt", encoding="utf-8") as fh:
        for line in fh:
            record = json.loads(line)
            if "_table" in record:
                continue
            try:
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
            except sqlite3.Error as exc:
                failed += 1
                report.add_error(f"legacy_import_chunks: {exc}")
    stats["imported"] = inserted
    stats["failed"] = failed
    return stats


def seed_all(
    settings: Settings | None = None,
    *,
    include_legacy: bool = True,
    report: SeedReport | None = None,
) -> dict[str, Any]:
    """Run the full seed pipeline and return a verification report.

    The returned dict includes per-table imported/skipped/failed counts plus an
    ``ok`` flag that is False if any validation or database error occurred.
    """
    settings = settings or get_settings()
    seed_dir = settings.seed_dir
    report = report or SeedReport()

    log.info("seed: starting from %s", seed_dir)

    with get_db(settings.db_path) as conn:
        with transaction(conn):
            upsert_sources(conn, _load(seed_dir / "sources.json"), report)
            upsert_articles(conn, _load(seed_dir / "constitution_seed.json"), report)
            upsert_departments(conn, _load(seed_dir / "departments_seed.json"), report)
            upsert_triage(conn, _load(seed_dir / "triage_seed.json"), report)
            if include_legacy:
                import_legacy_chunks(conn, settings, report)

    report.log_summary()
    return report.summary()
