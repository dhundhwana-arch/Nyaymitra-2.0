"""Separate one language from a two-language (diglot) PDF by layout, never by guesswork.

The Legislative Department's "English" Constitution PDF is a Hindi–English diglot. How the
two languages are arranged (facing pages, two columns, or alternating blocks) is not known
until the file is opened, so each page is classified from the positions and scripts of its
words and the decision is reported page by page:

    single_language   only the wanted script on the page                -> kept
    other_language    only the other script                             -> dropped
    other_language_lines_removed  a few complete lines of the other script (e.g. a running
                      header) on a page of the wanted language            -> those lines dropped
    columns           the two scripts sit left/right of one vertical line -> wanted side kept
    rows              the two scripts sit above/below one horizontal line -> wanted part kept
    interleaved       scripts alternate with no clean line              -> wanted-only lines kept,
                                                                           page marked UNCERTAIN
    empty             no letters

Rules that are never relaxed: a word containing the other script is never emitted; a page
where separation is not clean is marked uncertain; any uncertain page blocks the import.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from ..languages import script_counts

Word = tuple[float, float, float, float, str]          # x0, y0, x1, y1, text
CLEAN = 0.985                                          # share of words on the right side of the line


@dataclass
class PageResult:
    page: int
    mode: str
    text: str = ""
    other_text: str = ""
    uncertain: bool = False
    wanted_words: int = 0
    other_words: int = 0
    dropped_wanted_words: int = 0        # wanted-script words that sat on the other side
    removed_other_words: int = 0         # other-script words that sat on the wanted side
    split_at: float | None = None
    purity: float | None = None
    notes: list[str] = field(default_factory=list)


def _kind(text: str, wanted: str, other: str) -> str:
    counts = script_counts(text)
    if counts.get(other):
        return "other"
    if counts.get(wanted):
        return "wanted"
    return "neutral"


def _lines(words: Iterable[Word]) -> str:
    """Rebuild reading order: group by baseline, then left to right."""
    words = sorted(words, key=lambda w: (round((w[1] + w[3]) / 2, 1), w[0]))
    lines: list[list[Word]] = []
    for word in words:
        middle, height = (word[1] + word[3]) / 2, max(1.0, word[3] - word[1])
        if lines and abs((lines[-1][-1][1] + lines[-1][-1][3]) / 2 - middle) <= 0.5 * height:
            lines[-1].append(word)
        else:
            lines.append([word])
    return "\n".join(" ".join(w[4] for w in sorted(line, key=lambda w: w[0])) for line in lines)


def _best_split(points: list[tuple[float, str]]) -> tuple[float, float, bool]:
    """Best single threshold separating 'wanted' from 'other' along one axis.

    Returns (threshold, purity, wanted_is_low_side).
    """
    points = sorted(points)
    total_w = sum(1 for _, k in points if k == "wanted")
    total_o = len(points) - total_w
    best = (0.0, 0.0, True)
    low_w = low_o = 0
    for index in range(len(points) - 1):
        if points[index][1] == "wanted":
            low_w += 1
        else:
            low_o += 1
        if points[index][0] == points[index + 1][0]:
            continue
        threshold = (points[index][0] + points[index + 1][0]) / 2
        correct_low = low_w + (total_o - low_o)        # wanted low, other high
        correct_high = low_o + (total_w - low_w)       # other low, wanted high
        for correct, wanted_low in ((correct_low, True), (correct_high, False)):
            purity = correct / len(points)
            if purity > best[1]:
                best = (threshold, purity, wanted_low)
    return best


def separate_page(words: list[Word], page: int = 1, wanted: str = "Latn", other: str = "Deva") -> PageResult:
    kinds = [_kind(w[4], wanted, other) for w in words]
    n_wanted, n_other = kinds.count("wanted"), kinds.count("other")
    result = PageResult(page=page, mode="empty", wanted_words=n_wanted, other_words=n_other)
    if n_wanted == 0 and n_other == 0:
        return result
    if n_other == 0:
        result.mode, result.text = "single_language", _lines(words)
        return result
    if n_wanted == 0:
        result.mode, result.other_text = "other_language", _lines(words)
        return result

    lettered = [(w, k) for w, k in zip(words, kinds) if k != "neutral"]
    minority = min(n_wanted, n_other) / (n_wanted + n_other)
    for axis, mode in ((0, "columns"), (1, "rows")):
        centre = lambda w: (w[axis] + w[axis + 2]) / 2  # noqa: E731
        threshold, purity, wanted_low = _best_split([(centre(w), k) for w, k in lettered])
        # A page that is almost all one language "splits" trivially; that is not a layout.
        if purity < CLEAN or minority < 0.05:
            continue
        on_wanted_side = lambda w: (centre(w) < threshold) == wanted_low  # noqa: E731
        keep = [w for w, k in zip(words, kinds) if on_wanted_side(w) and k != "other"]
        rest = [w for w, k in zip(words, kinds) if not on_wanted_side(w) and k != "wanted"]
        result.mode, result.split_at, result.purity = mode, round(threshold, 1), round(purity, 4)
        result.removed_other_words = sum(1 for w, k in zip(words, kinds) if on_wanted_side(w) and k == "other")
        result.dropped_wanted_words = sum(1 for w, k in zip(words, kinds) if not on_wanted_side(w) and k == "wanted")
        result.text, result.other_text = _lines(keep), _lines(rest)
        if result.removed_other_words:
            result.uncertain = True
            result.notes.append("other-language words were found inside the wanted area and removed")
        if result.dropped_wanted_words > max(3, 0.03 * n_wanted):
            result.uncertain = True
            result.notes.append("many wanted-language words lie in the other area (not emitted)")
        return result

    # No clean line. Keep only lines made purely of the wanted script, and say so.
    rows: dict[float, list[tuple[Word, str]]] = {}
    for w, k in zip(words, kinds):
        rows.setdefault(round((w[1] + w[3]) / 2 / 3), []).append((w, k))
    keep: list[Word] = []
    for row in rows.values():
        if any(k == "other" for _, k in row):
            result.dropped_wanted_words += sum(1 for _, k in row if k == "wanted")
            result.removed_other_words += sum(1 for _, k in row if k == "other")
        else:
            keep += [w for w, _ in row]
    result.text = _lines(keep)
    if minority < 0.05 and n_other < n_wanted and result.dropped_wanted_words == 0:
        # e.g. a running header in the other language: whole lines removed, nothing of the
        # wanted language lost, no line contained both scripts.
        result.mode = "other_language_lines_removed"
        result.notes.append("a few complete lines in the other language were removed")
        return result
    result.mode, result.uncertain = "interleaved", True
    result.notes.append("the two languages are not separated by a single line on this page")
    return result


def summarise(pages: list[PageResult], wanted: str = "Latn", other: str = "Deva") -> dict[str, Any]:
    modes: dict[str, int] = {}
    for p in pages:
        modes[p.mode] = modes.get(p.mode, 0) + 1
    leaked = sum(script_counts(p.text).get(other, 0) for p in pages)
    uncertain = [p.page for p in pages if p.uncertain]
    blocking = []
    if leaked:
        blocking.append("mixed_language_content")
    if uncertain:
        blocking.append("uncertain_column_extraction")
    if not any(p.text.strip() for p in pages):
        blocking.append("no_text_in_wanted_language")
    return {
        "pages": len(pages), "page_modes": modes, "uncertain_pages": uncertain,
        "other_script_letters_in_output": leaked,
        "wanted_words_not_emitted": sum(p.dropped_wanted_words for p in pages),
        "other_words_removed_from_wanted_area": sum(p.removed_other_words for p in pages),
        "blocking_reasons": blocking, "reliable": not blocking,
        "per_page": [{k: v for k, v in asdict(p).items() if k not in ("text", "other_text")} for p in pages],
    }


def extract_pdf(path: Path, wanted: str = "Latn", other: str = "Deva") -> tuple[list[PageResult], dict[str, Any]]:
    """Read word boxes with PyMuPDF (an optional tool dependency, not used by the server)."""
    try:
        import pymupdf  # type: ignore
    except ImportError as exc:                                   # pragma: no cover
        raise RuntimeError("layout-aware extraction needs PyMuPDF: pip install pymupdf") from exc
    results: list[PageResult] = []
    with pymupdf.open(str(path)) as document:
        for number, page in enumerate(document, start=1):
            words = [(w[0], w[1], w[2], w[3], w[4]) for w in page.get_text("words")]
            results.append(separate_page(words, number, wanted, other))
    return results, summarise(results, wanted, other)


def compare_numbering(wanted_pages: list[str], other_pages: list[str]) -> dict[str, Any]:
    """Article numbers found in each language of the same book should agree."""
    from . import ingest

    def bases(pages: list[str]) -> set[int]:
        out = set()
        for article in ingest.parse_articles(pages)[0]:
            digits = "".join(ch for ch in article.article_no if ch.isdigit())
            if digits:
                out.add(int(digits))
        return out

    a, b = bases(wanted_pages), bases(other_pages)
    return {"compared": "base numbers only (letter suffixes are written differently in each script)",
            "wanted_language_numbers": len(a), "other_language_numbers": len(b),
            "only_in_wanted": sorted(a - b), "only_in_other": sorted(b - a), "agree": a == b and bool(a)}
