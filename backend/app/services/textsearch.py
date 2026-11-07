"""Language-aware tokenisation helpers shared by search and retrieval.

Gujarati (and Hindi) text has no whitespace-delimited morphology, so naive OR-matching on
every token produces false hits on particles like "છે" or "માંથી". We therefore drop
stopwords, prefer AND matching, and post-filter candidates by how many query tokens they
actually contain.
"""
from __future__ import annotations

import re

TOKEN_RE = re.compile(r"[\w\u0A80-\u0AFF\u0900-\u097F]+", re.UNICODE)

STOPWORDS: frozenset[str] = frozenset(
    {
        # Gujarati function words
        "છે", "છો", "હતું", "હતો", "માં", "માંથી", "ને", "અને", "કે", "કેમ", "પર", "થી", "માટે",
        "શું", "કેવી", "કેવું", "કરવું", "કરવી", "કરો", "હું", "તમે", "તમારા", "તમારો", "મારા",
        "મારો", "મને", "એક", "આ", "તે", "પણ", "જ", "શકે", "થાય", "જોઈએ", "કોઈ", "હોય", "જ્યારે",
        # Hindi function words
        "है", "हैं", "का", "की", "के", "को", "में", "से", "और", "क्या", "कैसे", "करना", "मैं", "मेरा",
        # English function words
        "the", "and", "for", "what", "how", "who", "which", "when", "where", "why", "is", "are",
        "was", "were", "can", "could", "should", "would", "will", "i", "my", "me", "we", "you",
        "to", "of", "in", "on", "at", "with", "do", "does", "did", "a", "an", "about", "if",
        "not", "no", "it", "this", "that", "there", "be", "been", "have", "has", "had", "from",
        "please", "tell", "know", "want", "need", "any", "some",
    }
)


def tokens(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "")]


def significant_tokens(text: str, *, min_len: int = 3, limit: int = 8) -> list[str]:
    seen: list[str] = []
    for token in tokens(text):
        if len(token) < min_len or token in STOPWORDS:
            continue
        if token not in seen:
            seen.append(token)
    # longest first: in Indic languages the content word is usually the longer token
    seen.sort(key=len, reverse=True)
    return seen[:limit]


def fts_expression(tokens_in: list[str], operator: str = "AND") -> str | None:
    if not tokens_in:
        return None
    quoted = ['"' + t.replace('"', '""') + '"' for t in tokens_in[:8]]
    return f" {operator} ".join(quoted)


def match_count(text: str, tokens_in: list[str]) -> int:
    haystack = (text or "").lower()
    return sum(1 for token in tokens_in if token in haystack)
