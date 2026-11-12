"""Split page text into article candidates.

IMPORTANT: every string stored in ``title_raw`` / ``text_raw`` / ``label_raw`` is an
exact slice of the PDF text layer.  Nothing is translated, transliterated,
normalised (no NFC/NFKC), trimmed inside, or "repaired".  Canonical numbers
(``base_no``) are derived *alongside* the raw label purely for comparison.

The heading heuristics below are conservative on purpose: when they cannot
recognise the layout they find few/no articles and the quality gates fail,
rather than guessing.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

MAX_ARTICLE_NO = 395  # last article number of the Constitution of India

# "14. Equality before law.—The State ..."  /  "1[21A. Right to education.—"
# Gujarati digits (૦-૯) and Gujarati-letter suffixes are accepted as written.
HEADING_RE = re.compile(
    r"^[ \t]*(?:[0-9]{1,2}[ \t]*\[|\[)?[ \t]*"
    r"(?P<num>[0-9]{1,3}|[\u0AE6-\u0AEF]{1,3})"
    r"(?P<suf>[-\u2010\u2011]?(?:[A-Z]{1,2}|[\u0A95-\u0AB9]{1,2}))?"
    r"\.[ \t]*(?P<rest>\S.*)$"
)
# Official texts separate marginal heading and body with ".—"; contents pages do not.
SEPARATOR_RE = re.compile(r"[.\u0964]?[ \t]*[\u2014\u2013\u2015]|\.[ \t]*-(?=\S)")
# English footnotes ("1. Subs. by the Constitution (...) Act ...") look like headings.
FOOTNOTE_RE = re.compile(
    r"^(Subs\.|Ins\.|Added|Omitted|Rep\.|Cl\.|Sub-cl|The words|The word|See |Now |Art\.|"
    r"Proviso|Explanation |Paragraph|Entry|Part |Certain words|Original|In its application|"
    r"The brackets|Renumbered|Amended|Sub-s|S\. |Ss\. |Date |w\.e\.f)"
)
# Articles end where the Schedules begin.
SCHEDULE_START = {
    "en": re.compile(r"^[ \t\[0-9]*FIRST[ \t]+SCHEDULE[ \t\]]*$"),
    "gu": re.compile(r"^[ \t\[0-9\u0AE6-\u0AEF]*પહેલી[ \t]+અનુસૂચિ[ \t\]]*$"),
}
LOOKAHEAD_LINES = 2  # a heading may wrap before its ".—"


@dataclass
class Article:
    language: str
    label_raw: str        # number exactly as printed, e.g. "21A" or "૨૧ક"
    base_no: int          # numeric part only (comparison aid)
    suffix_raw: str       # suffix exactly as printed ("" if none)
    title_raw: str
    text_raw: str
    page_start: int       # 1-based PDF page
    page_end: int
    occurrence: int = 1   # >1 when the same label was matched again (duplicate)
    out_of_order: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def extract_articles(pages: list[str], language: str) -> dict:
    """Return {"articles": [Article], "rejected": [...], "body_end_page": int|None}."""
    lines: list[tuple[int, str]] = []
    for pno, text in enumerate(pages, start=1):
        for line in text.split("\n"):
            lines.append((pno, line))

    sched_re = SCHEDULE_START.get(language)
    heads: list[dict] = []
    rejected: list[dict] = []
    body_end_idx, body_end_page = len(lines), None

    for i, (pno, line) in enumerate(lines):
        if sched_re and heads and sched_re.match(line) and max(h["base_no"] for h in heads) >= MAX_ARTICLE_NO - 5:
            body_end_idx, body_end_page = i, pno
            break
        m = HEADING_RE.match(line)
        if not m:
            continue
        base = int(m.group("num"))  # int() understands Gujarati digits
        if not 1 <= base <= MAX_ARTICLE_NO:
            continue
        rest = m.group("rest")
        cont = []
        for _, nxt in lines[i + 1:i + 1 + LOOKAHEAD_LINES]:
            if HEADING_RE.match(nxt):  # never borrow a separator from the next entry
                break
            cont.append(nxt)
        window = "\n".join([rest] + cont)
        sep = SEPARATOR_RE.search(window)
        cand = {"page": pno, "line": line, "base_no": base}
        if FOOTNOTE_RE.match(rest):
            rejected.append({**cand, "reason": "looks like a footnote"})
            continue
        if not sep:
            rejected.append({**cand, "reason": "no heading/body separator (contents entry or list item)"})
            continue
        heads.append({"idx": i, "page": pno, "base_no": base,
                      "label_raw": m.group("num") + (m.group("suf") or ""),
                      "suffix_raw": m.group("suf") or "",
                      "title_raw": window[:sep.start()]})

    articles: list[Article] = []
    seen: dict[str, int] = {}
    prev_base = 0
    for n, h in enumerate(heads):
        end = heads[n + 1]["idx"] if n + 1 < len(heads) else body_end_idx
        chunk = lines[h["idx"]:end]
        seen[h["label_raw"]] = seen.get(h["label_raw"], 0) + 1
        articles.append(Article(
            language=language, label_raw=h["label_raw"], base_no=h["base_no"],
            suffix_raw=h["suffix_raw"], title_raw=h["title_raw"],
            text_raw="\n".join(l for _, l in chunk),
            page_start=h["page"], page_end=chunk[-1][0] if chunk else h["page"],
            occurrence=seen[h["label_raw"]], out_of_order=h["base_no"] < prev_base,
        ))
        prev_base = max(prev_base, h["base_no"])
    return {"articles": articles, "rejected": rejected, "body_end_page": body_end_page}
