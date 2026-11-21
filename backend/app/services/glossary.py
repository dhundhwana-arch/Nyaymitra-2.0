"""Plain-language legal glossary (citizen-facing, not statutory definitions)."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from ..config import get_settings

SOURCE_NOTE = (
    "Plain-language explanation written for citizens. It is not the statutory definition — "
    "check the Act itself or ask legal aid before relying on the precise legal meaning."
)


@lru_cache(maxsize=1)
def _load() -> dict:
    path = Path(get_settings().seed_dir) / "glossary.json"
    if not path.exists():
        return {"terms": []}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def reset_cache() -> None:
    _load.cache_clear()


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def lookup(term: str) -> dict | None:
    payload = _load()
    needle = _norm(term)
    if not needle:
        return None
    entries = payload.get("terms", [])
    # exact key / english term first
    for entry in entries:
        if needle in {_norm(entry["key"]), _norm(entry["term_en"]), _norm(entry["term_gu"])}:
            return entry
    # then prefix / containment against match aliases
    for entry in entries:
        candidates = [entry["key"], entry["term_en"], entry["term_gu"], *entry.get("match", [])]
        if any(needle == _norm(c) or (len(needle) >= 3 and needle in _norm(c)) for c in candidates):
            return entry
    return None


def all_terms() -> list[dict]:
    return list(_load().get("terms", []))


def as_response(term: str) -> dict:
    entry = lookup(term)
    if not entry:
        return {
            "term": term,
            "found": False,
            "explanation_en": None,
            "explanation_gu": None,
            "source_note": SOURCE_NOTE,
            "disclaimers": [
                "This term is not in the built-in glossary. Ask legal aid (15100) for the meaning "
                "in your own matter."
            ],
        }
    return {
        "term": entry["term_en"],
        "found": True,
        "explanation_en": entry["explanation_en"],
        "explanation_gu": entry["explanation_gu"],
        "source_note": SOURCE_NOTE,
        "disclaimers": [
            "Glossary explanation only — not legal advice about your case.",
            "Every glossary entry requires review by a qualified legal professional.",
        ],
    }
