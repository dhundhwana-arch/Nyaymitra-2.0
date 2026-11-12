"""Constitution ingestion with validation, provenance and quality gates.

Replaces the four legacy one-shot scripts (audit §5.7). Every extracted article is
validated *before* it reaches the database:

* the article number must parse and be plausible (1–500, optional letter suffix)
* page numbers, Part and Chapter headings are carried along for provenance
* duplicate numbers are reported, never silently inserted
* bodies that look like they swallowed the next article (embedded headings, page
  headers, implausible length) are flagged as boundary problems
* missing numbers inside the observed range are reported, never invented
* text quality (replacement characters) is measured for PDFs
* rows already verified by a human are never overwritten
* existing non-empty text is never replaced unless the caller asks explicitly, so a
  partial or badly-extracted PDF cannot silently destroy good data
* re-running the same document is idempotent: identical text counts as unchanged

Nothing here runs automatically: ``scripts/ingest_constitution.py`` must be pointed at an
official source document supplied by the project owner, and it is dry-run by default.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

MIN_BODY_CHARS = 40
MAX_BODY_CHARS = 8000
MAX_ARTICLE_NUMBER = 500

HEADING_RE = re.compile(r"(?m)^[ \t]*(?P<num>\d{1,3}[A-Z]?)\.[ \t]+(?P<rest>[^\n]{0,400})$")
PART_RE = re.compile(r"(?m)^[ \t]*PART[ \t]+(?P<no>[IVXLC]+)\b[ \t]*(?:[—–:-][ \t]*)?(?P<title>.*)$")
CHAPTER_RE = re.compile(
    r"(?m)^[ \t]*CHAPTER[ \t]+(?P<no>[IVXLC]+)\b[ \t]*(?:[—–:-][ \t]*)?(?P<title>.*)$"
)
EMBEDDED_HEADING_RE = re.compile(r"(?m)^[ \t]*\d{1,3}[A-Z]?\.[ \t]+\S")
PAGE_HEADER_RE = re.compile(
    r"(?m)^[ \t]*(?:THE CONSTITUTION OF INDIA|PART[ \t]+[IVXLC]+\b|CHAPTER[ \t]+[IVXLC]+\b)[ \t]*$"
)
EM_DASH = "\u2014"
REPLACEMENT = "\ufffd"


@dataclass
class ParsedArticle:
    article_no: str
    title: str
    body: str
    line_no: int
    page_start: int = 1
    page_end: int = 1
    part_no: str | None = None
    part_title: str | None = None
    chapter_title: str | None = None

    @property
    def pages_label(self) -> str:
        if self.page_end and self.page_end != self.page_start:
            return f"{self.page_start}-{self.page_end}"
        return str(self.page_start)


@dataclass
class IngestReport:
    source_file: str
    source_key: str
    language: str
    characters: int = 0
    pages: int = 0
    ocr_confidence: float = 0.0
    articles_found: int = 0
    articles_written: int = 0
    articles_unchanged: int = 0
    articles_conflicting: int = 0
    articles_skipped_verified: int = 0
    duplicates: list[str] = field(default_factory=list)
    malformed: list[str] = field(default_factory=list)
    short_bodies: list[str] = field(default_factory=list)
    boundary_issues: list[dict] = field(default_factory=list)
    missing_numbers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    quality_ok: bool = True
    blocking_reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def read_pages(path: Path) -> tuple[list[str], str]:
    """Return ``(pages, kind)`` for a .pdf / .txt / .md source.

    Page boundaries are preserved so an article can record which pages it came from.
    """
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return [(page.extract_text() or "") for page in reader.pages], "pdf"
    if suffix in {".txt", ".md", ".json"}:
        return [path.read_text(encoding="utf-8", errors="replace")], "text"
    raise ValueError(f"unsupported source type: {suffix} (expected .pdf, .txt or .md)")


def read_source(path: Path) -> tuple[str, str]:
    """Backwards-compatible helper returning the joined text."""
    pages, kind = read_pages(path)
    return "\n".join(pages), kind


def ocr_confidence(text: str) -> float:
    """Very rough quality signal for extracted PDF text (0..1).

    Counts replacement characters and control noise against real letter content. It is a
    *warning indicator*, not a substitute for human review.
    """
    if not text:
        return 0.0
    letters = sum(1 for ch in text if ch.isalpha())
    noise = text.count(REPLACEMENT) + sum(1 for ch in text if ord(ch) < 32 and ch not in "\n\r\t")
    return round(max(0.0, min(1.0, 1.0 - (noise / max(1, letters + noise)))), 3)


def parse_articles(text_or_pages: str | list[str]) -> tuple[list[ParsedArticle], list[str]]:
    """Parse ``N. Title.—body`` headings into article records.

    Handles the text layer of the official India Code PDFs
    ("14. Equality before law.—The State shall not deny …") and keeps the Part/Chapter and
    page each article came from, so provenance survives ingestion.
    """
    pages = [text_or_pages] if isinstance(text_or_pages, str) else list(text_or_pages)
    lines: list[tuple[int, str]] = []
    for page_index, page in enumerate(pages, start=1):
        for line in page.splitlines():
            lines.append((page_index, line))

    heading_positions: list[tuple[int, str, str]] = []
    for index, (_, line) in enumerate(lines):
        match = HEADING_RE.match(line)
        if not match:
            continue
        number = match.group("num").strip()
        digits = re.match(r"\d+", number)
        if not digits or int(digits.group()) > MAX_ARTICLE_NUMBER:
            continue
        heading_positions.append((index, number, match.group("rest").strip()))

    articles: list[ParsedArticle] = []
    malformed: list[str] = []
    current_part: tuple[str, str] | None = None
    current_chapter: str | None = None
    scan_start = 0

    for position, (index, number, rest) in enumerate(heading_positions):
        end = heading_positions[position + 1][0] if position + 1 < len(heading_positions) else len(lines)

        # Structure headings that appear before this article belong to it.
        for scan in range(scan_start, index):
            text = lines[scan][1]
            part_match = PART_RE.match(text)
            if part_match:
                part_title = re.sub(
                    r"\s+", " ", part_match.group("title") or ""
                ).strip(" .:;-—")
                if not part_title:
                    # The title usually sits on the next line: "PART III" / "FUNDAMENTAL RIGHTS".
                    for lookahead in range(scan + 1, index):
                        candidate = lines[lookahead][1].strip()
                        if not candidate:
                            continue
                        if HEADING_RE.match(candidate) or PART_RE.match(candidate) or CHAPTER_RE.match(candidate):
                            break
                        part_title = re.sub(r"\s+", " ", candidate).strip(" .:;-—")
                        break
                current_part = (part_match.group("no").strip(), part_title)
                current_chapter = None
                continue
            chapter_match = CHAPTER_RE.match(text)
            if chapter_match:
                current_chapter = re.sub(
                    r"\s+", " ", chapter_match.group("title") or ""
                ).strip(" .:;-—") or f"Chapter {chapter_match.group('no').strip()}"
        scan_start = end

        if EM_DASH in rest:
            title, first_line_body = rest.split(EM_DASH, 1)
        else:
            title, first_line_body = rest[:120], rest
        body_lines = [first_line_body.strip()] + [ln.strip() for ln in (t for _, t in lines[index + 1:end])]
        body = "\n".join(ln for ln in body_lines if ln).strip()
        title = re.sub(r"\s+", " ", title).strip(" .:;")
        if not title:
            malformed.append(number)
            title = f"Article {number}"

        page_start = lines[index][0]
        page_end = lines[end - 1][0] if end - 1 >= index else page_start
        articles.append(
            ParsedArticle(
                article_no=number,
                title=title,
                body=body,
                line_no=index + 1,
                page_start=page_start,
                page_end=page_end,
                part_no=current_part[0] if current_part else None,
                part_title=current_part[1] if current_part else None,
                chapter_title=current_chapter,
            )
        )
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


def boundary_issues(articles: Iterable[ParsedArticle]) -> list[dict]:
    """Flag bodies that probably swallowed text belonging to the next article.

    This is a heuristic warning, never an automatic edit: the reviewer decides. It exists
    because a wrong boundary silently mis-attributes law, which is the worst failure mode
    this project has.
    """
    issues: list[dict] = []
    for article in articles:
        reasons = []
        if len(article.body) > MAX_BODY_CHARS:
            reasons.append("oversized_body")
        if EMBEDDED_HEADING_RE.search(article.body):
            reasons.append("embedded_article_heading")
        if PAGE_HEADER_RE.search(article.body):
            reasons.append("page_header_inside_body")
        if reasons:
            issues.append({"article_no": article.article_no, "reasons": reasons})
    return issues


def assess_quality(report: IngestReport) -> None:
    """Decide whether this extraction is good enough to trust (never auto-approve)."""
    reasons: list[str] = []
    if report.articles_found == 0:
        reasons.append("no_articles_found")
    if report.ocr_confidence < 0.9:
        reasons.append("low_text_quality")
    if report.duplicates:
        reasons.append("duplicate_article_numbers")
    if report.malformed:
        reasons.append("articles_without_titles")
    if report.boundary_issues:
        reasons.append("suspicious_article_boundaries")
    if report.articles_found >= 5 and len(report.short_bodies) > max(1, report.articles_found * 0.1):
        reasons.append("many_short_bodies")
    report.blocking_reasons = reasons
    report.quality_ok = not reasons


def ingest_text(
    conn: sqlite3.Connection,
    *,
    text: str | list[str],
    source_key: str,
    source_file: str,
    language: str = "en",
    dry_run: bool = True,
    replace_existing: bool = False,
) -> IngestReport:
    """Parse and (unless dry-run) write an article set.

    ``replace_existing`` allows identical-number rows with *different* text to be updated —
    but never a row a human has verified, and never silently: conflicts are counted and
    reported either way.
    """
    pages = [text] if isinstance(text, str) else list(text)
    joined = "\n".join(pages)
    report = IngestReport(
        source_file=source_file,
        source_key=source_key,
        language=language,
        characters=len(joined),
        pages=len(pages),
    )
    report.ocr_confidence = ocr_confidence(joined)
    if report.ocr_confidence < 0.9:
        report.warnings.append(
            "low_text_quality: extracted text contains replacement or control characters; "
            "check the source document and consider re-exporting the PDF text layer."
        )

    articles, malformed = parse_articles(pages)
    report.articles_found = len(articles)
    report.malformed = malformed
    report.duplicates = find_duplicates(articles)
    report.short_bodies = [a.article_no for a in articles if len(a.body) < MIN_BODY_CHARS]
    report.boundary_issues = boundary_issues(articles)
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
    if report.boundary_issues:
        report.warnings.append(
            "suspicious_article_boundaries: an article body contains another article heading, "
            "a page header, or is implausibly long — check the PDF text layer before trusting it."
        )
    if report.missing_numbers:
        report.warnings.append(
            "missing_articles: numbers absent from the source text are reported, not filled in."
        )
    assess_quality(report)
    if dry_run:
        return report

    source = conn.execute(
        "SELECT id FROM legal_sources WHERE source_key = ?", (source_key,)
    ).fetchone()
    if source is None:
        raise ValueError(f"unknown source_key {source_key!r}: add it to data/seed/sources.json first")
    source_id = source["id"]

    text_column = "text_gu" if language == "gu" else "text_en"
    title_column = "title_gu" if language == "gu" else "title_en"

    seen_numbers: set[str] = set()
    for article in articles:
        if article.article_no in seen_numbers:
            continue
        seen_numbers.add(article.article_no)
        existing = conn.execute(
            f"SELECT id, verification_status, {text_column} AS existing_text"
            " FROM constitution_articles WHERE article_no = ?",
            (article.article_no,),
        ).fetchone()
        payload_body = article.body[:20000]
        locator = f"pages {article.pages_label} of {source_file} (line {article.line_no})"

        if existing and existing["verification_status"] == "verified":
            report.articles_skipped_verified += 1
            continue
        if existing and (existing["existing_text"] or "").strip():
            if existing["existing_text"].strip() == payload_body.strip():
                report.articles_unchanged += 1
                continue
            if not replace_existing:
                report.articles_conflicting += 1
                continue
        if existing:
            conn.execute(
                f"""UPDATE constitution_articles
                    SET {text_column} = COALESCE(NULLIF(?, ''), {text_column}),
                        {title_column} = COALESCE(NULLIF(?, ''), {title_column}),
                        part_no = COALESCE(?, part_no),
                        part_title = COALESCE(?, part_title),
                        chapter_title = COALESCE(?, chapter_title),
                        text_status = 'verified_source_text',
                        source_id = ?, source_locator = ?, source_pages = ?,
                        updated_at = datetime('now')
                    WHERE id = ?""",
                (
                    payload_body,
                    article.title,
                    article.part_no,
                    article.part_title,
                    article.chapter_title,
                    source_id,
                    locator,
                    article.pages_label,
                    existing["id"],
                ),
            )
        else:
            conn.execute(
                """INSERT INTO constitution_articles
                   (article_key, article_no, article_label, part_no, part_title, chapter_title,
                    title_en, title_gu, text_en, text_gu, text_status, verification_status,
                    source_id, source_locator, source_pages, source_url, sort_order, notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,'verified_source_text','requires_human_verification',
                           ?,?,?,?,?,?)""",
                (
                    f"article-{article.article_no.lower()}",
                    article.article_no,
                    f"Article {article.article_no}",
                    article.part_no,
                    article.part_title,
                    article.chapter_title,
                    article.title if language == "en" else None,
                    article.title if language == "gu" else None,
                    payload_body if language == "en" else None,
                    payload_body if language == "gu" else None,
                    source_id,
                    locator,
                    article.pages_label,
                    None,
                    int(re.match(r"\d+", article.article_no).group()),
                    (
                        "Imported from the supplied source document. text_status is "
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
           VALUES (?,?,datetime('now'),?,?,?,?,?, ?)""",
        (
            source_key,
            source_file,
            report.articles_found,
            report.articles_written,
            len(report.duplicates),
            json.dumps(report.missing_numbers),
            json.dumps(report.as_dict(), ensure_ascii=False),
            "completed" if report.quality_ok else "completed_with_warnings",
        ),
    )
    return report
