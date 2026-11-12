"""Constitution search and retrieval.

Search is FTS5-backed with a LIKE fallback. Retrieval results are the *only* legal
material the AI layer is allowed to use (see ``app/ai/rag.py``).
"""
from __future__ import annotations

import re
import sqlite3
import time
from typing import Any

from . import textsearch

DISCLAIMERS = [
    "This is legal information and navigation help, not legal advice.",
    "NYAYMITRA is not a court, a judge or a lawyer and does not decide cases.",
    "Always check the original text at the official source before relying on it.",
]

#: Articles a citizen-facing assistant is expected to cover. Used only to *report*
#: gaps — never to invent text.
EXPECTED_ARTICLES = ["12", "14", "15", "19", "20", "21", "21A", "22", "32", "39A", "226", "300A"]

_TOKEN_RE = textsearch.TOKEN_RE


def _fts_match_expression(query: str) -> str | None:
    tokens = [t for t in _TOKEN_RE.findall(query) if len(t) >= 2]
    if not tokens:
        return None
    # Quote every token so that FTS5 operators in user input cannot change the query.
    return " OR ".join('"' + t.replace('"', '""') + '"' for t in tokens[:12])


def _snippet(row: sqlite3.Row, language: str, query: str | None, width: int = 220) -> str | None:
    language = language if language in {"en", "gu"} else "en"
    candidates = [
        row[f"text_{language}"],
        row[f"citizen_explanation_{language}"],
        row[f"text_{'gu' if language == 'en' else 'en'}"],
        row[f"citizen_explanation_{'gu' if language == 'en' else 'en'}"],
        row.get("title_en") if isinstance(row, dict) else row["title_en"],
    ]
    text = next((c for c in candidates if c), None)
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    if query:
        token = next((t for t in _TOKEN_RE.findall(query) if len(t) >= 2), None)
        if token:
            idx = text.lower().find(token.lower())
            if idx > width // 2:
                start = max(0, idx - width // 2)
                return "…" + text[start:start + width] + "…"
    return text[:width] + ("…" if len(text) > width else "")


def _row_to_summary(row: sqlite3.Row, language: str, query: str | None) -> dict[str, Any]:
    return {
        "id": row["id"],
        "article_no": row["article_no"],
        "article_label": row["article_label"],
        "part_no": row["part_no"],
        "part_title": row["part_title"],
        "title_en": row["title_en"],
        "title_gu": row["title_gu"],
        "text_status": row["text_status"],
        "verification_status": row["verification_status"],
        "last_checked_at": row["last_checked_at"],
        "snippet": _snippet(row, language, query),
    }


def search(
    conn: sqlite3.Connection,
    *,
    query: str | None,
    language: str = "gu",
    page: int = 1,
    page_size: int = 20,
    part_no: str | None = None,
    verification_status: str | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    offset = (page - 1) * page_size
    notice: str | None = None
    params: list[Any] = []
    where: list[str] = []
    if part_no:
        where.append("a.part_no = ?")
        params.append(part_no)
    if verification_status:
        where.append("a.verification_status = ?")
        params.append(verification_status)

    rows: list[sqlite3.Row]
    total: int
    expression = _fts_match_expression(query) if query else None

    if expression:
        clause = " AND ".join(where)
        base = (
            "FROM constitution_fts JOIN constitution_articles a ON a.id = constitution_fts.rowid "
            "WHERE constitution_fts MATCH ?"
        )
        args = [expression, *params]
        if clause:
            base += " AND " + clause
        try:
            total = conn.execute(f"SELECT COUNT(*) {base}", args).fetchone()[0]
            rows = conn.execute(
                f"SELECT a.*, bm25(constitution_fts) AS rank {base} ORDER BY rank LIMIT ? OFFSET ?",
                [*args, page_size, offset],
            ).fetchall()
        except sqlite3.OperationalError:
            expression = None  # fall through to LIKE
    if not expression:
        if query:
            like = f"%{query.strip()}%"
            where.append(
                "(a.article_label LIKE ? OR a.article_no LIKE ? OR a.title_en LIKE ? OR a.title_gu LIKE ?"
                " OR a.text_en LIKE ? OR a.text_gu LIKE ? OR a.citizen_explanation_en LIKE ?"
                " OR a.citizen_explanation_gu LIKE ?)"
            )
            params.extend([like] * 8)
            notice = "Searched with substring matching (the full-text index returned no usable expression)."
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        total = conn.execute(f"SELECT COUNT(*) FROM constitution_articles a{clause}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT a.* FROM constitution_articles a{clause} ORDER BY a.sort_order, a.id LIMIT ? OFFSET ?",
            [*params, page_size, offset],
        ).fetchall()

    took = int((time.perf_counter() - start) * 1000)
    if total == 0 and query:
        notice = notice or (
            "No article in the current verified corpus matches that search. "
            "The corpus is incomplete: only curated entries are loaded, so try a plain-language "
            "question in the assistant instead, or browse the articles that are available."
        )
    return {
        "query": query,
        "language": language,
        "total": total,
        "page": page,
        "page_size": page_size,
        "took_ms": took,
        "items": [_row_to_summary(r, language, query) for r in rows],
        "notice": notice,
    }


def _searchable(row: sqlite3.Row) -> str:
    return " ".join(
        str(row[field] or "")
        for field in (
            "article_label", "title_en", "title_gu", "text_en", "text_gu",
            "citizen_explanation_en", "citizen_explanation_gu",
        )
    )


def retrieve_for_ai(conn: sqlite3.Connection, query: str, limit: int = 4) -> list[sqlite3.Row]:
    """Top-k rows used as grounding context, precision over recall.

    * significant tokens only (stopwords and 1-2 character particles are dropped)
    * AND matching first, OR only as a fallback
    * every candidate must actually contain enough of the query's content words

    If nothing qualifies, an EMPTY list is returned on purpose: falling back to "the first
    N articles" would present unrelated provisions as if they answered the question, which
    is exactly the false grounding this project must avoid.
    """
    significant = textsearch.significant_tokens(query)
    if not significant:
        return []
    rows: list[sqlite3.Row] = []
    for operator in ("AND", "OR"):
        expression = textsearch.fts_expression(significant, operator)
        if not expression:
            break
        try:
            rows = list(
                conn.execute(
                    "SELECT a.* FROM constitution_fts JOIN constitution_articles a "
                    "ON a.id = constitution_fts.rowid WHERE constitution_fts MATCH ? "
                    "ORDER BY bm25(constitution_fts) LIMIT 20",
                    (expression,),
                ).fetchall()
            )
        except sqlite3.OperationalError:
            rows = []
        if rows:
            break

    threshold = 1 if len(significant) == 1 else max(2, (len(significant) + 1) // 2)
    scored: list[tuple[int, sqlite3.Row]] = []
    for row in rows:
        score = textsearch.match_count(_searchable(row), significant)
        if score >= threshold:
            scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [row for _, row in scored[:limit]]


def get_source(conn: sqlite3.Connection, source_id: int | None) -> dict | None:
    if not source_id:
        return None
    row = conn.execute("SELECT * FROM legal_sources WHERE id = ?", (source_id,)).fetchone()
    return dict(row) if row else None


def get_article(conn: sqlite3.Connection, identifier: str | int) -> dict | None:
    if isinstance(identifier, int) or str(identifier).isdigit():
        # "21" means Article 21, not row id 21. Row ids are never part of the public API.
        row = conn.execute(
            "SELECT * FROM constitution_articles WHERE article_no = ? COLLATE NOCASE", (str(identifier),)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM constitution_articles WHERE article_key = ? OR article_no = ? COLLATE NOCASE",
            (str(identifier), str(identifier)),
        ).fetchone()
    if row is None:
        return None
    data = dict(row)
    summary = _row_to_summary(row, "en", None)
    sources = [
        dict(r)
        for r in conn.execute(
            """SELECT s.*, aps.locator AS link_locator FROM article_sources aps
               JOIN legal_sources s ON s.id = aps.source_id WHERE aps.article_id = ?
               ORDER BY s.source_type""",
            (row["id"],),
        )
    ]
    primary = get_source(conn, row["source_id"])
    merged = summary | {
        "chapter_title": data["chapter_title"],
        "text_en": data["text_en"],
        "text_gu": data["text_gu"],
        "citizen_explanation_en": data["citizen_explanation_en"],
        "citizen_explanation_gu": data["citizen_explanation_gu"],
        "source_locator": data["source_locator"],
        "source_pages": data["source_pages"] if "source_pages" in data.keys() else None,
        "source_url": data["source_url"] or (primary or {}).get("url"),
        "notes": data["notes"],
        "sources": [
            {
                "source_key": s["source_key"],
                "title": s["title"],
                "publisher": s["publisher"],
                "source_type": s["source_type"],
                "url": s["url"],
                "document_ref": s["document_ref"],
                "published_on": s["published_on"],
                "retrieved_on": s["retrieved_on"],
                "last_checked_at": data["last_checked_at"],
            }
            for s in sources
        ],
        "disclaimers": DISCLAIMERS
        + (
            ["The authoritative text of this article has not been loaded yet — only a human-written "
             "explanation is available."]
            if data["text_status"] != "verified_source_text"
            else []
        ),
    }
    return merged


def parts(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """SELECT part_no, part_title, COUNT(*) AS article_count
           FROM constitution_articles GROUP BY part_no, part_title
           ORDER BY MIN(sort_order)"""
    ).fetchall()
    return [dict(r) for r in rows]


def coverage(conn: sqlite3.Connection) -> dict:
    def scalar(sql: str, *args: Any) -> int:
        return int(conn.execute(sql, args).fetchone()[0])

    present = {
        r["article_no"].upper()
        for r in conn.execute("SELECT article_no FROM constitution_articles")
    }
    return {
        "total_articles": scalar("SELECT COUNT(*) FROM constitution_articles"),
        "verified_text": scalar(
            "SELECT COUNT(*) FROM constitution_articles WHERE text_status = 'verified_source_text'"
        ),
        "owner_summaries": scalar(
            "SELECT COUNT(*) FROM constitution_articles WHERE text_status = 'owner_authored_summary'"
        ),
        "text_unavailable": scalar(
            "SELECT COUNT(*) FROM constitution_articles WHERE text_status = 'not_available'"
        ),
        "requires_human_verification": scalar(
            "SELECT COUNT(*) FROM constitution_articles "
            "WHERE verification_status = 'requires_human_verification'"
        ),
        "parts": parts(conn),
        "missing_standard_articles": [a for a in EXPECTED_ARTICLES if a.upper() not in present],
        "expected_article_count": 395,
        "note": (
            "The Constitution as published in 1950 had 395 articles; later amendments inserted and "
            "repealed articles, so the total is not a fixed number. Only articles actually loaded in "
            "this database are served — missing articles are reported here rather than filled in."
        ),
    }
