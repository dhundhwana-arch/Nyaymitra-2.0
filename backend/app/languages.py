"""Language registry, script detection and Unicode normalisation.

One place that knows which languages the product targets: the 22 languages of the Eighth
Schedule to the Constitution of India plus English. Everything else (API, assistant,
ingestion, frontend selector) reads this registry instead of hard-coding language lists.

Four things are kept strictly apart and never inferred from one another:

* interface translation   – labels of the app itself (web/locales/<code>.json)
* machine translation     – any text produced by a model, always labelled as such
* official text           – text taken from a published source (article_texts.content_status)
* verified text           – text a human has checked (verification_status = 'verified')

Codes are BCP 47 / ISO 639 (two-letter where one exists, otherwise ISO 639-3); scripts are
ISO 15924. Where a language is written in more than one script the registry names the one
this prototype uses and says so in ``script_note``.
"""
from __future__ import annotations

import json
import unicodedata
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

CONTENT_LANGUAGES: tuple[str, ...] = ("gu", "en")   # languages the seed content is written in
DEFAULT_CONTENT_LANGUAGE = "en"

# The ten labels without which a user cannot find their way around the app.
ESSENTIAL_UI_KEYS: tuple[str, ...] = (
    "navHome", "navAssistant", "navComplaint", "navLibrary", "navLegal",
    "navDepartments", "navGlossary", "navAbout", "search", "langLabel",
)


@dataclass(frozen=True)
class Language:
    code: str            # code used by the API and the frontend
    tag: str             # full BCP 47 tag including script where it matters
    iso639_3: str
    english_name: str
    native_name: str
    script: str          # ISO 15924
    direction: str       # 'ltr' | 'rtl'
    eighth_schedule: bool = True
    script_note: str | None = None


_L = Language
REGISTRY: tuple[Language, ...] = (
    _L("as", "as", "asm", "Assamese", "অসমীয়া", "Beng", "ltr"),
    _L("bn", "bn", "ben", "Bengali", "বাংলা", "Beng", "ltr"),
    _L("brx", "brx-Deva", "brx", "Bodo", "बर'", "Deva", "ltr"),
    _L("doi", "doi-Deva", "doi", "Dogri", "डोगरी", "Deva", "ltr"),
    _L("gu", "gu", "guj", "Gujarati", "ગુજરાતી", "Gujr", "ltr"),
    _L("hi", "hi", "hin", "Hindi", "हिन्दी", "Deva", "ltr"),
    _L("kn", "kn", "kan", "Kannada", "ಕನ್ನಡ", "Knda", "ltr"),
    _L("ks", "ks-Arab", "kas", "Kashmiri", "کٲشُر", "Arab", "rtl",
       script_note="Perso-Arabic script used here; Kashmiri is also written in Devanagari."),
    _L("kok", "kok-Deva", "kok", "Konkani", "कोंकणी", "Deva", "ltr",
       script_note="Devanagari used here; Konkani is also written in Roman and Kannada scripts."),
    _L("mai", "mai-Deva", "mai", "Maithili", "मैथिली", "Deva", "ltr"),
    _L("ml", "ml", "mal", "Malayalam", "മലയാളം", "Mlym", "ltr"),
    _L("mni", "mni-Beng", "mni", "Manipuri", "মৈতৈলোন্", "Beng", "ltr",
       script_note="Bengali script used here; Meetei Mayek (Mtei) input is detected but no Meetei Mayek interface text exists."),
    _L("mr", "mr", "mar", "Marathi", "मराठी", "Deva", "ltr"),
    _L("ne", "ne", "nep", "Nepali", "नेपाली", "Deva", "ltr"),
    _L("or", "or", "ori", "Odia", "ଓଡ଼ିଆ", "Orya", "ltr"),
    _L("pa", "pa-Guru", "pan", "Punjabi", "ਪੰਜਾਬੀ", "Guru", "ltr"),
    _L("sa", "sa", "san", "Sanskrit", "संस्कृतम्", "Deva", "ltr"),
    _L("sat", "sat-Olck", "sat", "Santali", "ᱥᱟᱱᱛᱟᱲᱤ", "Olck", "ltr",
       script_note="Ol Chiki script used here."),
    _L("sd", "sd-Arab", "snd", "Sindhi", "سنڌي", "Arab", "rtl",
       script_note="Perso-Arabic script used here; Sindhi in India is also written in Devanagari."),
    _L("ta", "ta", "tam", "Tamil", "தமிழ்", "Taml", "ltr"),
    _L("te", "te", "tel", "Telugu", "తెలుగు", "Telu", "ltr"),
    _L("ur", "ur", "urd", "Urdu", "اردو", "Arab", "rtl"),
    _L("en", "en", "eng", "English", "English", "Latn", "ltr", eighth_schedule=False),
)
BY_CODE: dict[str, Language] = {lang.code: lang for lang in REGISTRY}
CODES: tuple[str, ...] = tuple(BY_CODE)

# (first, last, ISO 15924)
_SCRIPT_RANGES: tuple[tuple[int, int, str], ...] = (
    (0x0041, 0x005A, "Latn"), (0x0061, 0x007A, "Latn"), (0x00C0, 0x024F, "Latn"),
    (0x0900, 0x097F, "Deva"), (0xA8E0, 0xA8FF, "Deva"),
    (0x0980, 0x09FF, "Beng"), (0x0A00, 0x0A7F, "Guru"), (0x0A80, 0x0AFF, "Gujr"),
    (0x0B00, 0x0B7F, "Orya"), (0x0B80, 0x0BFF, "Taml"), (0x0C00, 0x0C7F, "Telu"),
    (0x0C80, 0x0CFF, "Knda"), (0x0D00, 0x0D7F, "Mlym"),
    (0x0600, 0x06FF, "Arab"), (0x0750, 0x077F, "Arab"), (0x08A0, 0x08FF, "Arab"),
    (0xFB50, 0xFDFF, "Arab"), (0xFE70, 0xFEFF, "Arab"),
    (0x1C50, 0x1C7F, "Olck"), (0xABC0, 0xABFF, "Mtei"),
)
_UNIQUE_SCRIPT: dict[str, str] = {
    "Latn": "en", "Gujr": "gu", "Guru": "pa", "Orya": "or", "Taml": "ta", "Telu": "te",
    "Knda": "kn", "Mlym": "ml", "Olck": "sat", "Mtei": "mni",
}
_ASSAMESE_ONLY = frozenset("ৰৱ")
_SINDHI_ONLY = frozenset("ٻڀڄڃڇڏڊڍڌڳڱڻڪٺٿڦ")
_KASHMIRI_ONLY = frozenset("ٲٳۄۆؠ\u0655\u065F")


def is_known(code: str | None) -> bool:
    return bool(code) and code in BY_CODE


def get(code: str) -> Language:
    return BY_CODE[code]


def content_language(code: str | None) -> str:
    """The language seed content is served in for a requested interface language."""
    return code if code in CONTENT_LANGUAGES else DEFAULT_CONTENT_LANGUAGE


def script_of(ch: str) -> str | None:
    cp = ord(ch)
    for first, last, script in _SCRIPT_RANGES:
        if first <= cp <= last:
            return script if ch.isalpha() or unicodedata.category(ch).startswith("M") else None
    return None


def script_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ch in text or "":
        script = script_of(ch)
        if script:
            counts[script] = counts.get(script, 0) + 1
    return counts


def normalize_digits(text: str) -> str:
    """Every Unicode decimal digit (Gujarati, Devanagari, Arabic-Indic, Ol Chiki …) -> ASCII."""
    if not text or text.isascii():
        return text or ""
    out = []
    for ch in text:
        if not ch.isascii() and unicodedata.category(ch) == "Nd":
            out.append(str(unicodedata.digit(ch)))
        else:
            out.append(ch)
    return "".join(out)


def normalize_text(text: str) -> str:
    """Canonical form for storage comparison and search: NFC, digits unified, ZW marks kept.

    Zero-width joiner/non-joiner are meaningful in Indic and Perso-Arabic orthography and are
    deliberately NOT stripped. NFC (not NFKC) is used so that no letter is replaced by a
    compatibility look-alike.
    """
    return normalize_digits(unicodedata.normalize("NFC", text or ""))


def detect(text: str, hint: str | None = None) -> dict[str, Any]:
    """Identify script (reliable) and language (only as reliable as the script allows).

    Scripts shared by several target languages cannot be told apart from a short question
    without a statistical model, so the caller's selected language (``hint``) decides when
    it is written in the detected script; otherwise the most widely used language of that
    script is returned with ``confidence='low'`` and the alternatives are listed.
    """
    counts = script_counts(text)
    if not counts:
        fallback = hint if is_known(hint) else DEFAULT_CONTENT_LANGUAGE
        return {"language": fallback, "script": None, "confidence": "none",
                "candidates": [fallback], "method": "no_letters"}
    script = max(counts, key=lambda s: (counts[s], s != "Latn"))
    candidates = [l.code for l in REGISTRY if l.script == script]
    if script == "Mtei":
        candidates = ["mni"]
    if is_known(hint) and hint in candidates:
        return {"language": hint, "script": script, "confidence": "high" if len(candidates) == 1 else "medium",
                "candidates": candidates, "method": "script+selected_language"}
    if script in _UNIQUE_SCRIPT:
        return {"language": _UNIQUE_SCRIPT[script], "script": script, "confidence": "high",
                "candidates": candidates, "method": "script"}
    letters = set(text)
    if script == "Beng":
        if letters & _ASSAMESE_ONLY:
            return {"language": "as", "script": script, "confidence": "medium",
                    "candidates": candidates, "method": "script+distinctive_letters"}
        return {"language": "bn", "script": script, "confidence": "low",
                "candidates": candidates, "method": "script_default"}
    if script == "Arab":
        if letters & _SINDHI_ONLY:
            return {"language": "sd", "script": script, "confidence": "medium",
                    "candidates": candidates, "method": "script+distinctive_letters"}
        if letters & _KASHMIRI_ONLY:
            return {"language": "ks", "script": script, "confidence": "medium",
                    "candidates": candidates, "method": "script+distinctive_letters"}
        return {"language": "ur", "script": script, "confidence": "low",
                "candidates": candidates, "method": "script_default"}
    return {"language": "hi", "script": script, "confidence": "low",
            "candidates": candidates, "method": "script_default"}


# ------------------------------------------------------------------ interface catalogues
@lru_cache(maxsize=8)
def _load_locales(locales_dir: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    base = Path(locales_dir)
    if not base.is_dir():
        return out
    for path in sorted(base.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and isinstance(data.get("strings"), dict):
            out[path.stem] = data
    return out


def ui_status(code: str, locales_dir: Path) -> dict[str, Any]:
    locales = _load_locales(str(locales_dir))
    reference = locales.get("en", {}).get("strings", {})
    entry = locales.get(code)
    if entry is None:
        return {"catalogue": False, "keys": 0, "reference_keys": len(reference), "coverage": 0.0,
                "essential_present": 0, "essential_total": len(ESSENTIAL_UI_KEYS),
                "missing_essential": list(ESSENTIAL_UI_KEYS), "translation_status": "UNAVAILABLE",
                "review": None, "confidence": None}
    strings = {k: v for k, v in entry["strings"].items() if isinstance(v, str) and v.strip()}
    meta = entry.get("_meta", {})
    missing = [k for k in ESSENTIAL_UI_KEYS if k not in strings]
    present = len([k for k in strings if k in reference]) if reference else len(strings)
    return {
        "catalogue": True, "keys": present, "reference_keys": len(reference),
        "coverage": round(present / len(reference), 3) if reference else 0.0,
        "essential_present": len(ESSENTIAL_UI_KEYS) - len(missing),
        "essential_total": len(ESSENTIAL_UI_KEYS), "missing_essential": missing,
        "translation_status": meta.get("translation_status", "MACHINE_TRANSLATED"),
        "review": meta.get("review", "none"), "confidence": meta.get("confidence"),
    }


def describe(conn, locales_dir: Path) -> list[dict[str, Any]]:
    """Registry + availability computed from what is really in the database and catalogues."""
    text_counts: dict[str, dict[str, int]] = {}
    for row in conn.execute(
        "SELECT language, content_status, verification_status, COUNT(*) AS n FROM article_texts"
        " WHERE body IS NOT NULL AND TRIM(body) <> '' GROUP BY 1,2,3"
    ):
        bucket = text_counts.setdefault(row["language"], {"official": 0, "ocr": 0, "machine": 0, "verified": 0, "total": 0})
        bucket["total"] += row["n"]
        if row["content_status"] in ("OFFICIAL_SOURCE", "HUMAN_REVIEWED", "VERIFIED"):
            bucket["official"] += row["n"]
        elif row["content_status"] == "OCR_REVIEW_REQUIRED":
            bucket["ocr"] += row["n"]
        elif row["content_status"] == "MACHINE_TRANSLATED":
            bucket["machine"] += row["n"]
        if row["verification_status"] == "verified":
            bucket["verified"] += row["n"]
    legacy = conn.execute(
        """SELECT
             SUM(CASE WHEN text_status='verified_source_text' AND TRIM(COALESCE(text_en,''))<>'' THEN 1 ELSE 0 END) AS en_text,
             SUM(CASE WHEN text_status='verified_source_text' AND TRIM(COALESCE(text_gu,''))<>'' THEN 1 ELSE 0 END) AS gu_text,
             SUM(CASE WHEN TRIM(COALESCE(citizen_explanation_en,''))<>'' THEN 1 ELSE 0 END) AS en_sum,
             SUM(CASE WHEN TRIM(COALESCE(citizen_explanation_gu,''))<>'' THEN 1 ELSE 0 END) AS gu_sum
           FROM constitution_articles"""
    ).fetchone()
    summaries = {"en": legacy["en_sum"] or 0, "gu": legacy["gu_sum"] or 0}
    legacy_text = {"en": legacy["en_text"] or 0, "gu": legacy["gu_text"] or 0}

    out = []
    for lang in REGISTRY:
        ui = ui_status(lang.code, locales_dir)
        counts = text_counts.get(lang.code, {"official": 0, "ocr": 0, "machine": 0, "verified": 0, "total": 0})
        official = max(counts["official"], 0)
        # Text imported before migration 005 has no article_texts row; count it once.
        if lang.code in legacy_text and counts["total"] == 0:
            official = legacy_text[lang.code]
        sample = summaries.get(lang.code, 0)
        statuses = []
        if ui["catalogue"] and not ui["missing_essential"]:
            statuses.append("UI_READY")
        elif ui["catalogue"]:
            statuses.append("UI_PARTIAL")
        if sample:
            statuses.append("SAMPLE_CONTENT_AVAILABLE")
        if official:
            statuses.append("OFFICIAL_TEXT_AVAILABLE")
        if counts["verified"]:
            statuses.append("HUMAN_VERIFIED")
        if lang.code in CONTENT_LANGUAGES:
            statuses.append("ASSISTANT_SUPPORTED")
        out.append({
            **asdict(lang),
            "statuses": statuses,
            "ui": ui,
            "content": {
                "owner_summaries": sample,
                "official_text_articles": official,
                "ocr_review_required_articles": counts["ocr"],
                "machine_translated_articles": counts["machine"],
                "human_verified_articles": counts["verified"],
                "fallback_language": None if lang.code in CONTENT_LANGUAGES else DEFAULT_CONTENT_LANGUAGE,
            },
            "assistant": {
                "input_script_detected": True,
                "answers_in_language": lang.code in CONTENT_LANGUAGES,
                "answer_language": content_language(lang.code),
            },
        })
    return out
