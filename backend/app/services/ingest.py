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
import hashlib
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

MIN_BODY_CHARS = 40
MAX_BODY_CHARS = 8000
from ..languages import BY_CODE, normalize_digits

MAX_ARTICLE_NUMBER = 500

HEADING_RE = re.compile(r"(?m)^[ \t]*(?P<num>\d{1,3}[A-Z]{0,2})\.[ \t]+(?P<rest>[^\n]{0,400})$")
# "PART III", "PART IVA", and the same heading in Indic scripts ("ભાગ ૩", "भाग 4क" is NOT
# matched: a lettered Part in another script cannot be mapped to IVA/IXA without a table).
_PART_WORDS = r"(?:PART|ભાગ|भाग|ভাগ|ਭਾਗ|ଭାଗ|பகுதி|భాగం|ಭಾಗ|ഭാഗം|حصہ)"
_CHAPTER_WORDS = r"(?:CHAPTER|પ્રકરણ|अध्याय|প্রকরণ|অধ্যায়|ਅਧਿਆਇ|ଅଧ୍ୟାୟ|அத்தியாயம்|అధ్యాయం|ಅಧ್ಯಾಯ|അദ്ധ്യായം|باب)"
PART_RE = re.compile(
    r"(?m)^[ \t]*" + _PART_WORDS + r"[ \t]+(?P<no>[IVXLC]+[AB]?|\d{1,2})(?![\w])[ \t]*(?:[—–:-][ \t]*)?(?P<title>.*)$"
)
CHAPTER_RE = re.compile(
    r"(?m)^[ \t]*" + _CHAPTER_WORDS + r"[ \t]+(?P<no>[IVXLC]+|\d{1,2})(?![\w])[ \t]*(?:[—–:-][ \t]*)?(?P<title>.*)$"
)
EMBEDDED_HEADING_RE = re.compile(r"(?m)^[ \t]*\d{1,3}[A-Z]{0,2}\.[ \t]+\S")
PAGE_HEADER_RE = re.compile(
    r"(?m)^[ \t]*(?:THE CONSTITUTION OF INDIA|PART[ \t]+[IVXLC]+\b|CHAPTER[ \t]+[IVXLC]+\b)[ \t]*$"
)
EM_DASH = "\u2014"

EXTRACTION_METHODS = ("text_layer", "ocr", "manual_entry", "structured_import", "machine_translation")
_ROMAN = ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))


def _roman(value: int) -> str:
    out = ""
    for number, numeral in _ROMAN:
        while value >= number:
            out += numeral
            value -= number
    return out


def _part_number(raw: str) -> str:
    """'III' stays 'III'; a Part numbered in digits of any script ('૩', '3') becomes 'III'."""
    raw = normalize_digits(raw.strip())
    return _roman(int(raw)) if raw.isdigit() and 0 < int(raw) < 40 else raw


def content_status_for(extraction_method: str) -> str:
    """What the text may be called. OCR output is never labelled as official source text."""
    if extraction_method == "ocr":
        return "OCR_REVIEW_REQUIRED"
    if extraction_method == "machine_translation":
        return "MACHINE_TRANSLATED"
    return "OFFICIAL_SOURCE"
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
    # Set by the structured importer (CSV/JSON); None for text parsed from a document.
    pages: str | None = None            # page reference exactly as supplied, e.g. "45-46"
    locator: str | None = None          # where in the file this record came from
    normalized_body: str | None = None  # derived copy; ``body`` is always the original
    normalization: list | None = None   # operations that produced ``normalized_body``

    @property
    def pages_label(self) -> str:
        if self.pages is not None:
            return self.pages
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
    detached_marks_per_1000: float = 0.0
    script_mismatch: str | None = None
    extraction_method: str = "text_layer"
    content_status: str = "OFFICIAL_SOURCE"
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
    run_id: int | None = None

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


def detached_marks_per_1000(text: str) -> float:
    """Combining vowel signs that follow a space, per 1000 letters.

    In correctly encoded Indic text a dependent sign is attached to its consonant, so this is
    ~0. PDFs typeset with legacy fonts produce a text layer such as "ભારતન ું સુંવિધાન"
    (detached and substituted signs); that text looks plausible but is not the published
    wording and must not be imported as official text.
    """
    import unicodedata
    letters = detached = 0
    previous = ""
    for ch in text:
        category = unicodedata.category(ch)
        if category[0] == "L":
            letters += 1
        elif category in ("Mn", "Mc") and previous in (" ", "\t", "\n", ""):
            detached += 1
        previous = ch
    return round(1000.0 * detached / max(1, letters), 2)


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
        # Digits of any script are unified for the *number only*; the body is stored untouched.
        number = normalize_digits(match.group("num").strip())
        digits = re.match(r"\d+", number)
        if not digits or int(digits.group()) < 1 or int(digits.group()) > MAX_ARTICLE_NUMBER:
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
                current_part = (_part_number(part_match.group("no")), part_title)
                current_chapter = None
                continue
            chapter_match = CHAPTER_RE.match(text)
            if chapter_match:
                current_chapter = re.sub(
                    r"\s+", " ", chapter_match.group("title") or ""
                ).strip(" .:;-—") or f"Chapter {chapter_match.group('no').strip()}"
        # A PART/CHAPTER heading after this article's text opens the next article's structure:
        # it ends this body (it is not part of the article) and is scanned on the next turn.
        body_end = end
        for probe in range(index + 1, end):
            if PART_RE.match(lines[probe][1]) or CHAPTER_RE.match(lines[probe][1]):
                body_end = probe
                break
        scan_start = body_end

        if EM_DASH in rest:
            title, first_line_body = rest.split(EM_DASH, 1)
        else:
            title, first_line_body = rest[:120], rest
        body_lines = [first_line_body.strip()] + [ln.strip() for ln in (t for _, t in lines[index + 1:body_end])]
        body = "\n".join(ln for ln in body_lines if ln).strip()
        title = re.sub(r"\s+", " ", title).strip(" .:;")
        if not title:
            malformed.append(number)
            title = f"Article {number}"

        page_start = lines[index][0]
        # Page of the last line that has text (a blank line at the top of the next page is not content).
        page_end = next((lines[i][0] for i in range(body_end - 1, index, -1) if lines[i][1].strip()), page_start)
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
    if report.detached_marks_per_1000 > 2.0:
        reasons.append("broken_indic_text_layer")
    if report.script_mismatch:
        reasons.append("script_mismatch")
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


JOURNAL_ARTICLE_COLUMNS = (
    "text_en", "text_gu", "title_en", "title_gu", "part_no", "part_title", "chapter_title",
    "text_status", "source_id", "source_locator", "source_pages", "updated_at",
)


def rollback_run(conn: sqlite3.Connection, run_id: int, *, force: bool = False) -> dict:
    """Undo exactly what one import run wrote, using its journal.

    A text that was changed again after the run (its checksum no longer matches what the run
    wrote) is left alone and reported as a conflict unless ``force``. Owner explanations are
    never touched: they are not in the journal.
    """
    run = conn.execute("SELECT id, status FROM ingest_runs WHERE id = ?", (run_id,)).fetchone()
    if run is None:
        raise ValueError(f"no import run with id {run_id}")
    if run["status"] == "rolled_back":
        raise ValueError(f"run {run_id} has already been rolled back")
    changes = conn.execute("SELECT * FROM import_changes WHERE run_id = ? ORDER BY id DESC", (run_id,)).fetchall()
    result = {"run_id": run_id, "changes": len(changes), "restored": 0, "removed_texts": 0,
              "removed_articles": 0, "conflicts": []}
    for change in changes:
        current = conn.execute("SELECT content_sha256 FROM article_texts WHERE article_id = ? AND language = ?",
                               (change["article_id"], change["language"])).fetchone()
        if (current is None or current["content_sha256"] != change["new_sha256"]) and not force:
            result["conflicts"].append({"article_no": change["article_no"], "language": change["language"],
                                        "reason": "changed_after_this_run"})
            continue
        conn.execute("DELETE FROM article_texts WHERE article_id = ? AND language = ?",
                     (change["article_id"], change["language"]))
        if change["prev_text_json"]:
            prev = json.loads(change["prev_text_json"])
            columns = ", ".join(prev)
            conn.execute(f"INSERT INTO article_texts ({columns}) VALUES ({', '.join('?' for _ in prev)})",
                         tuple(prev.values()))
            result["restored"] += 1
        else:
            result["removed_texts"] += 1
        if change["created_article"]:
            row = conn.execute(
                "SELECT (SELECT COUNT(*) FROM article_texts WHERE article_id = a.id) AS texts,"
                " TRIM(COALESCE(citizen_explanation_en,'') || COALESCE(citizen_explanation_gu,'')) AS summary"
                " FROM constitution_articles a WHERE id = ?", (change["article_id"],)).fetchone()
            if row is not None and row["texts"] == 0 and not row["summary"]:
                conn.execute("DELETE FROM constitution_articles WHERE id = ?", (change["article_id"],))
                result["removed_articles"] += 1
        elif change["prev_article_json"]:
            prev = json.loads(change["prev_article_json"])
            conn.execute(
                f"UPDATE constitution_articles SET {', '.join(k + ' = ?' for k in prev)} WHERE id = ?",
                (*prev.values(), change["article_id"]))
    if not result["conflicts"]:
        conn.execute("UPDATE ingest_runs SET status = 'rolled_back' WHERE id = ?", (run_id,))
    return result


def write_articles(
    conn: sqlite3.Connection,
    articles: list[ParsedArticle],
    report,
    *,
    source_key: str,
    source_file: str,
    language: str,
    replace_existing: bool = False,
    extraction_method: str = "text_layer",
    edition: str | None = None,
    run_id: int | None = None,
) -> None:
    """The one place that writes article text (used by the document and structured importers).

    Rules: never 'verified'; never touches owner explanations; identical text is 'unchanged';
    different text is a conflict unless ``replace_existing``; a human-verified row is skipped;
    each language keeps its own provenance. ``report`` needs the articles_* counters.
    """
    source = conn.execute(
        "SELECT id, source_type FROM legal_sources WHERE source_key = ?", (source_key,)
    ).fetchone()
    if source is None:
        raise ValueError(f"unknown source_key {source_key!r}: add it to data/seed/sources.json first")
    source_id = source["id"]
    content_status = content_status_for(extraction_method)
    if content_status == "OFFICIAL_SOURCE" and source["source_type"] != "official":
        raise ValueError(
            f"source {source_key!r} is registered as {source['source_type']!r}, not 'official': "
            "its text cannot be stored as OFFICIAL_SOURCE"
        )

    core = language in ("en", "gu")          # languages that also have legacy columns
    text_column = "text_gu" if language == "gu" else "text_en"
    title_column = "title_gu" if language == "gu" else "title_en"

    def upsert_text(article_id: int, article: ParsedArticle, body: str, locator: str) -> None:
        conn.execute(
            """INSERT INTO article_texts
                 (article_id, language, title, body, part_title, chapter_title, source_id,
                  source_locator, source_pages, edition, extraction_method, content_status,
                  verification_status, content_sha256, body_normalized, normalization_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'requires_human_verification',?,?,?)
               ON CONFLICT(article_id, language) DO UPDATE SET
                 title = excluded.title, body = excluded.body, part_title = excluded.part_title,
                 chapter_title = excluded.chapter_title, source_id = excluded.source_id,
                 source_locator = excluded.source_locator, source_pages = excluded.source_pages,
                 edition = excluded.edition, extraction_method = excluded.extraction_method,
                 content_status = excluded.content_status,
                 verification_status = 'requires_human_verification',
                 content_sha256 = excluded.content_sha256,
                 body_normalized = excluded.body_normalized,
                 normalization_json = excluded.normalization_json, updated_at = datetime('now')""",
            (article_id, language, article.title, body, article.part_title, article.chapter_title,
             source_id, locator, article.pages_label or None, edition, extraction_method, content_status,
             hashlib.sha256(body.encode("utf-8")).hexdigest(), article.normalized_body,
             json.dumps(article.normalization, ensure_ascii=False) if article.normalization else None),
        )

    seen_numbers: set[str] = set()
    for article in articles:
        if article.article_no in seen_numbers:
            continue
        seen_numbers.add(article.article_no)
        existing = conn.execute(
            f"SELECT id, verification_status, {text_column} AS legacy_text, text_en"
            " FROM constitution_articles WHERE article_no = ?",
            (article.article_no,),
        ).fetchone()
        prior = None
        if existing:
            prior = conn.execute(
                "SELECT body, verification_status FROM article_texts WHERE article_id = ? AND language = ?",
                (existing["id"], language),
            ).fetchone()
        prev_article = prev_text = None
        if run_id is not None and existing:
            prev_article = {k: v for k, v in dict(conn.execute(
                "SELECT * FROM constitution_articles WHERE id = ?", (existing["id"],)).fetchone()).items()
                if k in JOURNAL_ARTICLE_COLUMNS}
            full = conn.execute("SELECT * FROM article_texts WHERE article_id = ? AND language = ?",
                                (existing["id"], language)).fetchone()
            prev_text = dict(full) if full else None
        payload_body = article.body[:20000]
        locator = article.locator or f"pages {article.pages_label} of {source_file} (line {article.line_no})"

        if (existing and core and existing["verification_status"] == "verified") or (
            prior and prior["verification_status"] == "verified"
        ):
            report.articles_skipped_verified += 1
            continue
        existing_text = ((existing["legacy_text"] if core else None) if existing else None) or (
            prior["body"] if prior else None
        ) or ""
        if existing_text.strip():
            if existing_text.strip() == payload_body.strip():
                if prior is None:      # imported before migration 005: add the provenance record
                    upsert_text(existing["id"], article, payload_body, locator)
                report.articles_unchanged += 1
                continue
            if not replace_existing:
                report.articles_conflicting += 1
                continue
        if existing and core:
            # The single legacy source slot follows English; another language only fills it
            # when no English text is present. Per-language provenance lives in article_texts.
            owns_slot = language == "en" or not (existing["text_en"] or "").strip()
            conn.execute(
                f"""UPDATE constitution_articles
                    SET {text_column} = COALESCE(NULLIF(?, ''), {text_column}),
                        {title_column} = COALESCE(NULLIF(?, ''), {title_column}),
                        part_no = COALESCE(part_no, ?),
                        part_title = CASE WHEN ? THEN COALESCE(?, part_title) ELSE COALESCE(part_title, ?) END,
                        chapter_title = CASE WHEN ? THEN COALESCE(?, chapter_title) ELSE COALESCE(chapter_title, ?) END,
                        text_status = 'verified_source_text',
                        source_id = CASE WHEN ? THEN ? ELSE source_id END,
                        source_locator = CASE WHEN ? THEN ? ELSE source_locator END,
                        source_pages = CASE WHEN ? THEN ? ELSE source_pages END,
                        updated_at = datetime('now')
                    WHERE id = ?""",
                (
                    payload_body, article.title, article.part_no,
                    language == "en", article.part_title, article.part_title,
                    language == "en", article.chapter_title, article.chapter_title,
                    owns_slot, source_id, owns_slot, locator, owns_slot, article.pages_label,
                    existing["id"],
                ),
            )
            article_id = existing["id"]
        elif existing:
            article_id = existing["id"]
        else:
            cursor = conn.execute(
                """INSERT INTO constitution_articles
                   (article_key, article_no, article_label, part_no, part_title, chapter_title,
                    title_en, title_gu, text_en, text_gu, text_status, verification_status,
                    source_id, source_locator, source_pages, source_url, sort_order, notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,'requires_human_verification',
                           ?,?,?,?,?,?)""",
                (
                    f"article-{article.article_no.lower()}",
                    article.article_no,
                    f"Article {article.article_no}",
                    article.part_no,
                    article.part_title if language == "en" else None,
                    article.chapter_title if language == "en" else None,
                    article.title if language == "en" else None,
                    article.title if language == "gu" else None,
                    payload_body if language == "en" else None,
                    payload_body if language == "gu" else None,
                    "verified_source_text" if core else "not_available",
                    source_id if core else None,
                    locator if core else None,
                    article.pages_label if core else None,
                    None,
                    int(m.group()) if (m := re.match(r"\d+", article.article_no)) else 0,
                    (
                        "Imported from the supplied source document. text_status "
                        "'verified_source_text' only means the text came from that document; "
                        "see article_texts.content_status for how it was extracted. The article "
                        "has NOT been checked by a legal professional: verification_status stays "
                        "requires_human_verification."
                    ),
                ),
            )
            article_id = cursor.lastrowid
        upsert_text(article_id, article, payload_body, locator)
        if run_id is not None:
            conn.execute(
                """INSERT INTO import_changes (run_id, article_id, article_no, language, created_article,
                                               prev_article_json, prev_text_json, new_sha256)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (run_id, article_id, article.article_no, language, 0 if existing else 1,
                 json.dumps(prev_article, ensure_ascii=False) if prev_article else None,
                 json.dumps(prev_text, ensure_ascii=False) if prev_text else None,
                 hashlib.sha256(payload_body.encode("utf-8")).hexdigest()),
            )
        report.articles_written += 1


def ingest_text(
    conn: sqlite3.Connection,
    *,
    text: str | list[str],
    source_key: str,
    source_file: str,
    language: str = "en",
    dry_run: bool = True,
    replace_existing: bool = False,
    extraction_method: str = "text_layer",
    edition: str | None = None,
) -> IngestReport:
    """Parse and (unless dry-run) write an article set.

    ``replace_existing`` allows identical-number rows with *different* text to be updated —
    but never a row a human has verified, and never silently: conflicts are counted and
    reported either way.
    """
    if language not in BY_CODE:
        raise ValueError(f"unknown language {language!r}: not in the language registry")
    if extraction_method not in EXTRACTION_METHODS:
        raise ValueError(f"extraction_method must be one of {', '.join(EXTRACTION_METHODS)}")
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
    report.extraction_method = extraction_method
    report.content_status = content_status_for(extraction_method)
    report.detached_marks_per_1000 = detached_marks_per_1000(joined)
    if report.detached_marks_per_1000 > 2.0:
        report.warnings.append(
            "broken_indic_text_layer: vowel signs are detached from their consonants — the text "
            "layer comes from a legacy font and does not reproduce the printed wording."
        )
    from ..languages import script_counts  # local import: avoids a cycle at module import
    counts = script_counts(joined)
    expected = BY_CODE[language].script
    if counts and language != "en":
        share = counts.get(expected, 0) / max(1, sum(counts.values()))
        if share < 0.3:
            dominant = max(counts, key=counts.get)
            report.script_mismatch = f"expected {expected}, found mostly {dominant} ({share:.0%} {expected})"
            report.warnings.append("script_mismatch: " + report.script_mismatch)
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

    run_id = conn.execute(
        "INSERT INTO ingest_runs (source_key, source_file, status) VALUES (?,?,'running')",
        (source_key, source_file),
    ).lastrowid
    report.run_id = run_id
    write_articles(conn, articles, report, source_key=source_key, source_file=source_file,
                   language=language, replace_existing=replace_existing,
                   extraction_method=extraction_method, edition=edition, run_id=run_id)

    conn.execute(
        """UPDATE ingest_runs SET finished_at = datetime('now'), articles_found = ?,
                                  articles_written = ?, duplicates = ?, missing_numbers = ?,
                                  report_json = ?, status = ? WHERE id = ?""",
        (
            report.articles_found,
            report.articles_written,
            len(report.duplicates),
            json.dumps(report.missing_numbers),
            json.dumps(report.as_dict(), ensure_ascii=False),
            "completed" if report.quality_ok else "completed_with_warnings",
            run_id,
        ),
    )
    return report
