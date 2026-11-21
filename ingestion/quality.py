"""Coverage, duplicate, missing-number, text-layer (OCR) quality and cross-language reports."""
from __future__ import annotations

import unicodedata
from collections import Counter

from .extract import MAX_ARTICLE_NO, Article

GUJARATI = (0x0A80, 0x0AFF)
THRESHOLDS = {
    "max_empty_page_ratio": 0.05,       # image-only pages => the PDF needs OCR
    "max_replacement_char_ratio": 0.0005,
    "max_private_use_ratio": 0.0005,    # PUA glyphs => legacy non-Unicode font
    "min_gujarati_letter_ratio": 0.60,  # gu only: low ratio => legacy-font mojibake
    "max_dotted_circle_ratio": 0.0005,  # U+25CC => broken matra/conjunct order
}


def _is_gu(ch: str) -> bool:
    return GUJARATI[0] <= ord(ch) <= GUJARATI[1]


def text_quality(pages: list[str], language: str) -> dict:
    total = sum(len(p) for p in pages)
    c = Counter()
    empty_pages, pages_without_gu = [], []
    for pno, text in enumerate(pages, start=1):
        if not text.strip():
            empty_pages.append(pno)
            continue
        has_gu = False
        for ch in text:
            cat = unicodedata.category(ch)
            if ch == "\ufffd":
                c["replacement"] += 1
            elif cat == "Co":
                c["private_use"] += 1
            elif cat == "Cc" and ch not in "\n\r\t":
                c["control"] += 1
            elif ch == "\u25cc":
                c["dotted_circle"] += 1
            if cat[0] == "L":
                c["letters"] += 1
                if _is_gu(ch):
                    c["gu_letters"] += 1
                    has_gu = True
                elif "LATIN" in unicodedata.name(ch, "") and ord(ch) > 0x7F:
                    c["latin_extended_letters"] += 1
        if language == "gu" and not has_gu:
            pages_without_gu.append(pno)
    ratio = lambda n: (n / total) if total else 0.0
    m = {
        "language": language,
        "page_count": len(pages),
        "total_chars": total,
        "empty_pages": empty_pages,
        "empty_page_ratio": len(empty_pages) / len(pages) if pages else 1.0,
        "replacement_chars": c["replacement"],
        "private_use_chars": c["private_use"],
        "control_chars": c["control"],
        "dotted_circles": c["dotted_circle"],
        "latin_extended_letters": c["latin_extended_letters"],
        "gujarati_letter_ratio": (c["gu_letters"] / c["letters"]) if c["letters"] else 0.0,
        "pages_without_gujarati": pages_without_gu if language == "gu" else None,
    }
    failures = []
    if total == 0:
        failures.append("no text layer at all (scanned PDF: OCR required)")
    if m["empty_page_ratio"] > THRESHOLDS["max_empty_page_ratio"]:
        failures.append(f"{len(empty_pages)} of {len(pages)} pages have no text layer")
    if ratio(c["replacement"]) > THRESHOLDS["max_replacement_char_ratio"]:
        failures.append(f"{c['replacement']} U+FFFD replacement characters")
    if ratio(c["private_use"]) > THRESHOLDS["max_private_use_ratio"]:
        failures.append(f"{c['private_use']} private-use characters (legacy font encoding)")
    if ratio(c["dotted_circle"]) > THRESHOLDS["max_dotted_circle_ratio"]:
        failures.append(f"{c['dotted_circle']} dotted circles (broken combining-mark order)")
    if language == "gu" and m["gujarati_letter_ratio"] < THRESHOLDS["min_gujarati_letter_ratio"]:
        failures.append(f"only {m['gujarati_letter_ratio']:.1%} of letters are Gujarati Unicode "
                        "(legacy non-Unicode font or wrong document)")
    m.update({"thresholds": THRESHOLDS, "failures": failures, "passed": not failures})
    return m


def coverage_report(articles: list[Article], language: str) -> dict:
    labels = Counter(a.label_raw for a in articles)
    bases = {a.base_no for a in articles}
    return {
        "language": language,
        "candidates_extracted": len(articles),
        "distinct_labels": len(labels),
        "distinct_base_numbers": len(bases),
        "expected_base_range": [1, MAX_ARTICLE_NO],
        "base_number_coverage": len(bases) / MAX_ARTICLE_NO,
        "missing_base_numbers": [n for n in range(1, MAX_ARTICLE_NO + 1) if n not in bases],
        "duplicates": [{"label_raw": l, "count": n,
                        "pages": [a.page_start for a in articles if a.label_raw == l]}
                       for l, n in labels.items() if n > 1],
        "out_of_order": [{"label_raw": a.label_raw, "page": a.page_start} for a in articles if a.out_of_order],
        "suffixed_labels": sorted({a.label_raw for a in articles if a.suffix_raw}),
        "empty_titles": [a.label_raw for a in articles if not a.title_raw.strip()],
    }


def compare_numbering(en: list[Article], gu: list[Article]) -> dict:
    """Report differences only. Never renumbers or maps anything."""
    def plain(arts):
        return {a.base_no for a in arts if not a.suffix_raw}

    def suffixed(arts):
        d: dict[int, list[str]] = {}
        for a in arts:
            if a.suffix_raw and a.label_raw not in d.setdefault(a.base_no, []):
                d[a.base_no].append(a.label_raw)
        return d

    pe, pg, se, sg = plain(en), plain(gu), suffixed(en), suffixed(gu)
    ambiguous = []
    for base in sorted(set(se) | set(sg)):
        e, g = se.get(base, []), sg.get(base, [])
        ambiguous.append({
            "base_no": base, "en_labels": e, "gu_labels": g,
            "status": "count_matches_mapping_unconfirmed" if len(e) == len(g) else "count_mismatch",
            "note": "Latin vs Gujarati suffix letters are not mapped automatically; a human must pair these.",
        })
    return {
        "plain_numbers_in_both": len(pe & pg),
        "plain_only_in_en": sorted(pe - pg),
        "plain_only_in_gu": sorted(pg - pe),
        "suffixed_articles_needing_human_mapping": ambiguous,
        "identical_plain_numbering": pe == pg,
    }
