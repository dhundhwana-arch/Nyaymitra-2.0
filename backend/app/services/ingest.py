"""Constitution ingestion with validation.

This replaces the four legacy one-shot scripts (audit §5.7). The difference is that every
extracted article is *validated* before it reaches the database:

* the article number must parse and be plausible (1–500, optional letter suffix)
* duplicate numbers are reported, never silently inserted
* bodies shorter than :data:`MIN_BODY_CHARS` are treated as extraction failures
* missing numbers inside the observed range are reported, never invented
* a crude OCR/encoding confidence is recorded for PDF text
* rows already marked ``verified`` are never overwritten

Nothing here runs automatically: `scripts/ingest_constitution.py` must be pointed at an
official source document supplied by the project owner.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

MIN_BODY_CHARS = 40
MAX_ARTICLE_NUMBER = 500

HEADING_RE = re.compile(
    r"(?m)^[ \t]*(?P<num>\d{1,3}[A-Z]?)\.[ \t]+(?P<rest>[^\n]{0,400})$"
)
EM_DASH = "\u2014"
REPLACEMENT = "\ufffd"


@dataclass
class ParsedArticle:
    article_no: str
    title: str
    body: str
    line_no: int


@dataclass
class IngestReport:
    source_file: str
    source_key: str
    language: str
    characters: int = 0
    ocr_confidence: float = 0.0
    articles_found: int = 0
    articles_written: int = 0
    articles_skipped_verified: int = 0
    duplicates: list[str] = field(default_factory=list)
    malformed: list[str] = field(default_factory=list)
    short_bodies: list[str] = field(default_factory=list)
    missing_numbers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def read_source(path: Path) -> tuple[str, str]:
    """Return ``(text, kind)`` for a .pdf / .txt / .md source."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages), "pdf"
    if suffix in {".txt", ".md", ".json"}:
        return path.read_text(encoding="utf-8", errors="replace"), "text"
    raise ValueError(f"unsupported source type: {suffix} (expected .pdf, .txt or .md)")


def ocr_confidence(text: str) -> float:
    """Very rough quality signal for extracted PDF text (0..1).

    Counts replacement characters and control noise against the amount of real
    letter content. It is a *warning indicator*, not a substitute for human review.
    """
    if not text:
        return 0.0
    letters = sum(1 for ch in text if ch.isalpha())
    noise = text.count(REPLACEMENT) + sum(
        1 for ch in text if ord(ch) < 32 and ch not in "\n\r\t"
    )
    return round(max(0.0, min(1.0, 1.0 - (noise / max(1, letters + noise)))), 3)


def parse_articles(text: str) -> tuple[list[ParsedArticle], list[str]]:
    """Parse ``N. Title.—body`` headings into article records.

    The heading style matches the text layer of the official India Code PDFs
    ("14. Equality before law.—The State shall not deny …").
    """
    lines = text.splitlines()
    headings: list[tuple[int, str, str]] = []  # (line index, number, rest)
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if not match:
            continue
        number = match.group("num").strip()
        try:
            if int(re.match(r"\d+", number).group()) > MAX_ARTICLE_NUMBER:
                continue
        except AttributeError:
            continue
        headings.append((index, number, match.group("rest").strip()))

    articles: list[ParsedArticle] = []
    malformed: list[str] = []
    for position, (index, number, rest) in enumerate(headings):
        end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        if EM_DASH in rest:
            title, first_line_body = rest.split(EM_DASH, 1)
        else:
            # No em dash: keep a short title and treat the whole line as body start.
            title, first_line_body = rest[:120], rest
        body_lines = [first_line_body.strip()] + [ln.strip() for ln in lines[index + 1:end]]
        body = "\n".join(ln for ln in body_lines if ln).strip()
        title = re.sub(r"\s+", " ", title).strip(" .:;")
        if not title:
            malformed.append(number)
            title = f"Article {number}"
        articles.append(ParsedArticle(article_no=number, title=title, body=body, line_no=index + 1))
    return articles, malformed


def find_duplicates(articles: Iterable[ParsedArticle]) -> list[str]:
    seen: dict[str, int] = {}
    for article in articles:
        seen[article.article_no] = seen.get(article.article_no, 0) + 1
    return sorted(number for number, count in seen.items() if count > 1)


def find_missing(articles: Iterable[ParsedArticle]) -> list[str]:
    numbers = set()
    for article in articles:
        match = re.match(r"(\d+)", article.article_no)
        if match:
            numbers.add(int(match.group(1)))
    if not numbers:
        return []
    highest = max(numbers)
    return [str(n) for n in range(1, highest + 1) if n not in numbers]


def ingest_text(
    conn: sqlite3.Connection,
    *,
    text: str,
    source_key: str,
    source_file: str,
    language: str = "en",
    dry_run: bool = True,
) -> IngestReport:
    report = IngestReport(
        source_file=source_file, source_key=source_key, language=language, characters=len(text)
    )
    report.ocr_confidence = ocr_confidence(text)
    if report.ocr_confidence < 0.9:
        report.warnings.append(
            "low_text_quality: extracted text contains replacement or control characters; "
            "check the source document and consider re-exporting the PDF text layer."
        )

    articles, malformed = parse_articles(text)
    report.articles_found = len(articles)
    report.malformed = malformed
    report.duplicates = find_duplicates(articles)
    report.short_bodies = [a.article_no for a in articles if len(a.body) < MIN_BODY_CHARS]
    report.missing_numbers = find_missing(articles)

    if report.duplicates:
        report.warnings.append(
            "duplicate_article_numbers: only the first occurrence of each number is kept; "
            "review manually (this is how the legacy duplicate Article 222 was handled)."
        )
    if report.short_bodies:
        report.warnings.append(
            "short_bodies: these articles parsed with too little text — the text was stored "
            "as-is (never padded or invented) and flagged for review."
        )
    if report.missing_numbers:
        report.warnings.append(
            "missing_articles: numbers absent from the source text are reported, not filled in."
        )
    if dry_run:
        return report

    source = conn.execute(
        "SELECT id FROM legal_sources WHERE source_key = ?", (source_key,)
    ).fetchone()
    if source is None:
        raise ValueError(f"unknown source_key {source_key!r}: add it to data/seed/sources.json first")
    source_id = source["id"]

    seen_numbers: set[str] = set()
    for article in articles:
        if article.article_no in seen_numbers:
            continue
        seen_numbers.add(article.article_no)
        existing = conn.execute(
            "SELECT id, verification_status FROM constitution_articles WHERE article_no = ?",
            (article.article_no,),
        ).fetchone()
        text_column = "text_gu" if language == "gu" else "text_en"
        title_column = "title_gu" if language == "gu" else "title_en"
        if existing and existing["verification_status"] == "verified":
            report.articles_skipped_verified += 1
            continue
        payload_body = article.body[:20000]
        if existing:
            conn.execute(
                f"""UPDATE constitution_articles
                    SET {text_column} = COALESCE(NULLIF(?, ''), {text_column}),
                        {title_column} = COALESCE(NULLIF(?, ''), {title_column}),
                        text_status = 'verified_source_text',
                        source_id = ?, source_locator = ?, updated_at = datetime('now')
                    WHERE id = ?""",
                (payload_body, article.title, source_id,
                 f"parsed from {source_file} line {article.line_no}", existing["id"]),
            )
        else:
            conn.execute(
                """INSERT INTO constitution_articles
                   (article_key, article_no, article_label, title_en, title_gu,
                    text_en, text_gu, text_status, verification_status, source_id,
                    source_locator, source_url, sort_order, notes)
                   VALUES (?,?,?,?,?,?,?,'verified_source_text','requires_human_verification',
                           ?,?,?,?,?)""",
                (
                    f"article-{article.article_no.lower()}",
                    article.article_no,
                    f"Article {article.article_no}",
                    article.title if language == "en" else None,
                    article.title if language == "gu" else None,
                    payload_body if language == "en" else None,
                    payload_body if language == "gu" else None,
                    source_id,
                    f"parsed from {source_file} line {article.line_no}",
                    None,
                    int(re.match(r"\d+", article.article_no).group()),
                    (
                        "Imported from the supplied source document. Text status is "
                        "verified_source_text (it came from the document) but the article has "
                        "NOT been checked by a legal professional: verification_status stays "
                        "requires_human_verification."
                    ),
                ),
            )
        report.articles_written += 1

    conn.execute(
        """INSERT INTO ingest_runs (source_key, source_file, finished_at, articles_found,
                                    articles_written, duplicates, missing_numbers, report_json, status)
           VALUES (?,?,datetime('now'),?,?,?,?,?, 'completed')""",
        (
            source_key,
            source_file,
            report.articles_found,
            report.articles_written,
            len(report.duplicates),
            json.dumps(report.missing_numbers),
            json.dumps(report.as_dict(), ensure_ascii=False),
        ),
    )
    return report
