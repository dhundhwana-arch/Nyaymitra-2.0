"""Flexible importer for article-wise Constitution data (CSV, TSV, JSON, JSONL, TXT, folders).

The layout of the owner's files is not known in advance, so nothing here assumes column
names. The steps are separate and each produces a report:

1. ``read_records``   – load rows without interpreting them
2. ``infer_mapping``  – work out which column is what, from header names and content.
                        If two columns compete for a field, or a required field was found
                        only by looking at the content, the result is ``needs_mapping`` and
                        the caller must supply an explicit mapping. Nothing is guessed.
3. ``build_records``  – normalise *identifiers* (article number, Part, pages, language);
                        the text itself is carried through untouched
4. ``validate``       – per-record checks; every rejection has a reason
5. ``quality_report`` – the data-quality dashboard for this file and language
6. ``apply``          – backup is the caller's job; this writes inside one transaction
                        through ``ingest.write_articles`` (same rules as the document importer)

Text is never corrected. For OCR an optional, separate normalised copy can be produced
(``normalise_ocr``); the original stays in ``body``.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .. import languages
from ..languages import normalize_digits, script_counts
from . import ingest

FIELDS = ("article_no", "text", "title", "part_no", "part_title", "chapter", "language", "pages",
          "page_start", "page_end", "source", "extraction_method", "verification_status", "edition")
REQUIRED = ("article_no", "text")
IMPORT_METHODS = ("text_layer", "ocr", "manual_entry")      # what a structured file may declare


def _norm_header(name: str) -> str:
    # \w does not include Indic vowel signs (combining marks), so filter by Unicode category.
    text = unicodedata.normalize("NFC", str(name)).lower()
    return "".join(ch for ch in text if unicodedata.category(ch)[0] in ("L", "M", "N"))


# Header names seen in practice, compared after lower-casing and removing separators.
_ALIASES: dict[str, tuple[str, ...]] = {
    "article_no": ("articleno", "articlenumber", "article", "artno", "art", "articleid", "number", "no", "num",
                   "અનુચ્છેદ", "અનુચ્છેદનંબર", "અનુચ્છેદક્રમાંક", "કલમ", "ક્રમાંક", "अनुच्छेद"),
    "text": ("text", "articletext", "body", "content", "fulltext", "description", "ocrtext", "rawtext",
             "લખાણ", "પાઠ", "વિગત", "पाठ"),
    "title": ("title", "articletitle", "heading", "name", "marginalnote", "marginalheading", "શીર્ષક", "મથાળું", "शीर्षक"),
    "part_no": ("part", "partno", "partnumber", "ભાગ", "भाग"),
    "part_title": ("parttitle", "partname", "partheading", "ભાગશીર્ષક"),
    "chapter": ("chapter", "chaptertitle", "chapterno", "chaptername", "પ્રકરણ", "अध्याय"),
    "language": ("language", "lang", "languagecode", "locale", "ભાષા", "भाषा"),
    "pages": ("page", "pages", "pageno", "pagenumber", "pdfpage", "pdfpages", "pageref", "pagerange", "પાન", "પાનું", "પૃષ્ઠ"),
    "page_start": ("pagestart", "startpage", "frompage", "firstpage"),
    "page_end": ("pageend", "endpage", "topage", "lastpage"),
    "source": ("source", "sourcefile", "sourcedocument", "sourcekey", "file", "filename", "pdf", "સ્રોત"),
    "extraction_method": ("extractionmethod", "method", "extraction", "extractedby"),
    "verification_status": ("verificationstatus", "verified", "status", "reviewstatus"),
    "edition": ("edition", "ason", "version"),
}
_LANG_SUFFIX = re.compile(r"^(?P<base>.+?)[._\- ](?P<lang>[a-z]{2,3})$", re.IGNORECASE)
_ARTICLE_VALUE = re.compile(r"^\s*(?:article|art\.?|અનુચ્છેદ|अनुच्छेद|કલમ)?\s*[-:._]?\s*0*(\d{1,3})\s*-?\s*([A-Za-z]{0,2})\s*\.?\s*$",
                            re.IGNORECASE)
_PREAMBLE = re.compile(r"^\s*(preamble|આમુખ|उद्देशिका|प्रस्तावना)\s*$", re.IGNORECASE)
_ROMAN = re.compile(r"^[IVXLC]+[AB]?$")
_PAGE_MARKERS = (
    re.compile(r"(?mi)^\s*[-=*_#]{2,}\s*(?:page|pg|પાન|પૃષ્ઠ)\s*[:#]?\s*(\d{1,4})\s*[-=*_#]{2,}\s*$"),
    re.compile(r"(?mi)^\s*\[\s*(?:page|pg)\s*[:#]?\s*(\d{1,4})\s*\]\s*$"),
    re.compile(r"(?mi)^\s*<<<?\s*(?:page|pg)\s*[:#]?\s*(\d{1,4})\s*>>>?\s*$"),
)


class MappingRequired(Exception):
    """The file cannot be interpreted safely without an explicit mapping."""

    def __init__(self, report: dict[str, Any]):
        super().__init__(report.get("message", "mapping required"))
        self.report = report


# ------------------------------------------------------------------------------- reading
def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_dir():
        for child in sorted(p for p in path.rglob("*") if p.is_file()):
            digest.update(child.name.encode("utf-8"))
            digest.update(child.read_bytes())
    else:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
    return digest.hexdigest()


def _decode(raw: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeError:
            continue
    raise ValueError("file is not UTF-8 or UTF-16 text; legacy encodings are not converted automatically")


def _flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, dict):
                out.update(_flatten(value, name))
            elif isinstance(value, list) and all(not isinstance(v, (dict, list)) for v in value):
                out[name] = "\n".join(str(v) for v in value)
            else:
                out[name] = value
    return out


def _looks_like_article_key(key: str) -> bool:
    return bool(_ARTICLE_VALUE.match(normalize_digits(str(key))) or _PREAMBLE.match(str(key)))


def _json_rows(data: Any, notes: list[str]) -> list[dict[str, Any]]:
    if isinstance(data, list):
        if all(isinstance(item, dict) for item in data):
            return [_flatten(item) for item in data]
        raise ValueError("JSON array does not contain objects")
    if isinstance(data, dict):
        keys = list(data)
        if keys and sum(_looks_like_article_key(k) for k in keys) >= 0.8 * len(keys):
            notes.append("JSON object keyed by article number: the key is exposed as column '(key)'")
            rows = []
            for key, value in data.items():
                row = _flatten(value) if isinstance(value, dict) else {"(value)": value}
                rows.append({"(key)": key, **row})
            return rows
        lists = [(k, v) for k, v in data.items() if isinstance(v, list) and v and all(isinstance(i, dict) for i in v)]
        if len(lists) == 1:
            notes.append(f"records taken from the top-level list '{lists[0][0]}'")
            return [_flatten(item) for item in lists[0][1]]
        if len(lists) > 1:
            raise MappingRequired({
                "status": "needs_mapping", "message": "several lists of records found in the JSON file",
                "candidate_lists": {k: len(v) for k, v in lists},
                "how_to_fix": "add \"records_path\": \"<one of the names above>\" to the mapping file",
            })
    raise ValueError("JSON layout not recognised: expected a list of objects or an object of articles")


def split_pages(text: str) -> tuple[list[str], str | None]:
    """Split an OCR/text export into pages if it carries page markers; index = page number."""
    if "\f" in text:
        return text.split("\f"), "form_feed"
    for pattern in _PAGE_MARKERS:
        marks = list(pattern.finditer(text))
        if len(marks) >= 2:
            highest = max(int(normalize_digits(m.group(1))) for m in marks)
            if highest > 5000:
                continue
            pages = [""] * highest
            head = text[: marks[0].start()].strip()
            for n, mark in enumerate(marks):
                end = marks[n + 1].start() if n + 1 < len(marks) else len(text)
                number = int(normalize_digits(mark.group(1)))
                pages[number - 1] += text[mark.end():end]
            if head:
                pages[0] = head + "\n" + pages[0]
            return pages, "page_markers"
    return [text], None


@dataclass
class Loaded:
    kind: str                                   # 'table' (rows of fields) or 'document' (parsed text)
    rows: list[dict[str, Any]]
    columns: list[str]
    format: str
    notes: list[str] = field(default_factory=list)
    pages: int | None = None
    page_source: str | None = None


def _document_rows(pages: list[str]) -> list[dict[str, Any]]:
    articles, malformed = ingest.parse_articles(pages)
    rows = []
    for a in articles:
        rows.append({"article_no": a.article_no, "title": None if a.article_no in malformed else a.title,
                     "text": a.body, "part_no": a.part_no, "part_title": a.part_title,
                     "chapter": a.chapter_title, "pages": a.pages_label, "(line)": a.line_no})
    return rows


def refuse_quarantined(path: Path) -> None:
    """The legacy Santali fragments are quarantined (unknown provenance); never import them."""
    resolved = path.resolve()
    if "legacy" in {part.lower() for part in resolved.parts} or resolved.name.lower().endswith((".gz", ".zip")):
        raise ValueError(f"{path}: quarantined legacy data and compressed archives are not imported by this tool")


def read_records(path: Path, *, records_path: str | None = None) -> Loaded:
    """Load a file or folder into rows. No interpretation of meaning happens here."""
    refuse_quarantined(path)
    notes: list[str] = []
    if path.is_dir():
        rows = []
        for child in sorted(p for p in path.iterdir() if p.is_file() and p.suffix.lower() in (".txt", ".md")):
            text, _ = _decode(child.read_bytes())
            rows.append({"(file name)": child.stem, "(file text)": text})
        notes.append("folder of text files: one record per file; the article number must come from the file name")
        return Loaded("table", rows, ["(file name)", "(file text)"], "folder", notes)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        pages, kind = ingest.read_pages(path)
        return Loaded("document", _document_rows(pages), list(_DOC_COLUMNS), f"pdf ({kind})", notes, len(pages), "pdf")
    text, encoding = _decode(path.read_bytes())
    if encoding != "utf-8-sig":
        notes.append(f"decoded as {encoding}")
    if suffix in (".csv", ".tsv"):
        sample = text[:20000]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel_tab if suffix == ".tsv" else csv.excel
        reader = csv.reader(io.StringIO(text, newline=""), dialect)
        table = [row for row in reader if any(cell.strip() for cell in row)]
        if not table:
            return Loaded("table", [], [], "csv", notes)
        header = [h.strip() for h in table[0]]
        first_is_data = _looks_like_article_key(header[0]) or any(len(h) > 80 for h in header)
        if first_is_data:
            notes.append("no header row detected: columns are named column_1, column_2 …")
            header = [f"column_{n + 1}" for n in range(max(len(r) for r in table))]
            body = table
        else:
            body = table[1:]
            seen: Counter[str] = Counter()
            for n, name in enumerate(header):
                name = name or f"column_{n + 1}"
                seen[name] += 1
                header[n] = name if seen[name] == 1 else f"{name}__{seen[name]}"
        rows = [{header[n]: (row[n] if n < len(row) else "") for n in range(len(header))} for row in body]
        return Loaded("table", rows, header, f"csv (delimiter {dialect.delimiter!r})", notes)
    if suffix in (".jsonl", ".ndjson"):
        rows = [_flatten(json.loads(line)) for line in text.splitlines() if line.strip()]
        return Loaded("table", rows, _columns(rows), "jsonl", notes)
    if suffix == ".json":
        data = json.loads(text)
        if records_path:
            for part in records_path.split("."):
                data = data[part]
        rows = _json_rows(data, notes)
        return Loaded("table", rows, _columns(rows), "json", notes)
    if suffix in (".txt", ".md", ".text", ""):
        pages, page_source = split_pages(text)
        return Loaded("document", _document_rows(pages), list(_DOC_COLUMNS), "text", notes, len(pages), page_source)
    raise ValueError(f"unsupported file type: {suffix}")


_DOC_COLUMNS = ("article_no", "title", "text", "part_no", "part_title", "chapter", "pages")


def _columns(rows: list[dict[str, Any]]) -> list[str]:
    seen: list[str] = []
    for row in rows:
        for key in row:
            if key not in seen:
                seen.append(key)
    return seen


# ------------------------------------------------------------------------------- mapping
def _values(rows: list[dict[str, Any]], column: str, limit: int = 300) -> list[str]:
    out = []
    for row in rows[:limit]:
        value = row.get(column)
        if value is not None and str(value).strip():
            out.append(str(value))
    return out


def _column_profile(rows: list[dict[str, Any]], column: str) -> dict[str, Any]:
    values = _values(rows, column)
    if not values:
        return {"filled": 0, "avg_length": 0, "article_like": 0.0, "language_like": 0.0, "scripts": {}}
    scripts: Counter[str] = Counter()
    for value in values[:60]:
        scripts.update(script_counts(value))
    known = {l.code for l in languages.REGISTRY} | {l.english_name.lower() for l in languages.REGISTRY}
    return {
        "filled": len(values),
        "avg_length": round(sum(len(v) for v in values) / len(values)),
        "article_like": round(sum(_looks_like_article_key(v) for v in values) / len(values), 2),
        "language_like": round(sum(v.strip().lower() in known for v in values) / len(values), 2),
        "scripts": dict(scripts.most_common(3)),
        "sample": values[0][:60],
    }


def infer_mapping(loaded: Loaded, language: str | None, explicit: dict[str, Any] | None = None,
                  accept_inferred: bool = False) -> dict[str, Any]:
    """Decide which column feeds which field, or say exactly why that cannot be decided."""
    if loaded.kind == "document":
        return {"status": "ok", "fields": {c: {"column": c, "basis": "parsed from the document"} for c in _DOC_COLUMNS},
                "unmapped_columns": [], "ambiguous": {}, "missing_required": [], "notes": loaded.notes}
    profiles = {c: _column_profile(loaded.rows, c) for c in loaded.columns}
    explicit = dict(explicit or {})
    constants = explicit.pop("constants", {}) or {}
    explicit.pop("records_path", None)
    fields: dict[str, dict[str, Any]] = {}
    ambiguous: dict[str, list[str]] = {}
    for name, column in explicit.items():
        if name not in FIELDS:
            raise ValueError(f"mapping names an unknown field {name!r}; allowed: {', '.join(FIELDS)}")
        if column not in loaded.columns:
            raise ValueError(f"mapping for {name!r} names column {column!r}, which is not in the file")
        fields[name] = {"column": column, "basis": "explicit mapping"}

    structural = {"(key)": ("article_no", "the JSON object key"), "(file name)": ("article_no", "the file name"),
                  "(value)": ("text", "the JSON value"), "(file text)": ("text", "the file content")}
    for column, (name, basis) in structural.items():
        if column in loaded.columns and name not in fields:
            fields[name] = {"column": column, "basis": basis}
    used = {f["column"] for f in fields.values()}
    by_field: dict[str, list[tuple[str, str]]] = {}
    for column in loaded.columns:
        if column in used:
            continue
        header = column.strip("()")
        suffix_lang = None
        match = _LANG_SUFFIX.match(header)
        if match and languages.is_known(match.group("lang").lower()):
            header, suffix_lang = match.group("base"), match.group("lang").lower()
        if suffix_lang and language and suffix_lang != language:
            continue                               # another language's column: never used
        key = _norm_header(header.split(".")[-1])
        for name, aliases in _ALIASES.items():
            if name in fields:
                continue
            if key in aliases:
                by_field.setdefault(name, []).append((column, "header name" + (f" + language suffix '{suffix_lang}'" if suffix_lang else "")))
    for name, candidates in by_field.items():
        suffixed = [c for c in candidates if "language suffix" in c[1]]
        chosen = suffixed if len(suffixed) == 1 else candidates
        if len(chosen) == 1:
            fields[name] = {"column": chosen[0][0], "basis": chosen[0][1]}
        else:
            ambiguous[name] = [c[0] for c in chosen]

    inferred: list[str] = []
    used = {f["column"] for f in fields.values()} | {c for cols in ambiguous.values() for c in cols}
    free = [c for c in loaded.columns if c not in used]
    if "article_no" not in fields and "article_no" not in ambiguous:
        candidates = [c for c in free if profiles[c]["article_like"] >= 0.9 and profiles[c]["filled"]]
        if len(candidates) == 1:
            fields["article_no"] = {"column": candidates[0], "basis": "content: values look like article numbers"}
            inferred.append("article_no")
        elif candidates:
            ambiguous["article_no"] = candidates
    if "text" not in fields and "text" not in ambiguous:
        used = {f["column"] for f in fields.values()}
        candidates = sorted((c for c in free if c not in used and profiles[c]["avg_length"] >= 40),
                            key=lambda c: -profiles[c]["avg_length"])
        if len(candidates) == 1:
            fields["text"] = {"column": candidates[0], "basis": "content: the only long-text column"}
            inferred.append("text")
        elif candidates:
            ambiguous["text"] = candidates

    for name, value in constants.items():
        if name not in FIELDS:
            raise ValueError(f"constants names an unknown field {name!r}")
        fields[name] = {"constant": value, "basis": "constant from mapping file"}

    missing = [name for name in REQUIRED if name not in fields]
    used = {f.get("column") for f in fields.values()}
    status = "ok"
    reasons = []
    if missing:
        status = "needs_mapping"
        reasons.append("required field not identified: " + ", ".join(missing))
    blocking_ambiguity = {k: v for k, v in ambiguous.items() if k in REQUIRED or k in ("language", "pages", "part_no")}
    if blocking_ambiguity:
        status = "needs_mapping"
        reasons.append("more than one column could be: " + "; ".join(f"{k} ← {v}" for k, v in blocking_ambiguity.items()))
    if inferred and not accept_inferred and status == "ok":
        status = "needs_mapping"
        reasons.append("identified from content only (no recognisable header): " + ", ".join(inferred)
                       + " — confirm with a mapping file or --accept-inferred")
    template = {name: info["column"] for name, info in fields.items() if "column" in info}
    for name, cols in ambiguous.items():
        template[name] = f"<choose one of: {' | '.join(cols)}>"
    for name in missing:
        template.setdefault(name, "<column name>")
    return {
        "status": status, "message": "; ".join(reasons) or "every field was identified from the header names",
        "format": loaded.format, "records": len(loaded.rows), "fields": fields, "ambiguous": ambiguous,
        "missing_required": missing, "inferred_from_content": inferred,
        "unmapped_columns": [c for c in loaded.columns if c not in used],
        "column_profiles": profiles, "mapping_template": template, "notes": loaded.notes,
    }


# ----------------------------------------------------------------------------- normalise
def parse_article_no(value: Any) -> tuple[str | None, str | None]:
    """'૨૧ક' is NOT converted (unknown letter); '૨૧', '21-A', 'Article 243ZA' are."""
    if value is None or not str(value).strip():
        return None, "missing_article_number"
    raw = normalize_digits(unicodedata.normalize("NFC", str(value))).strip()
    if isinstance(value, float) and value.is_integer():
        raw = str(int(value))
    if _PREAMBLE.match(raw):
        return "Preamble", None
    match = _ARTICLE_VALUE.match(raw)
    if not match:
        return None, "invalid_article_number"
    number = int(match.group(1))
    if not 1 <= number <= ingest.MAX_ARTICLE_NUMBER:
        return None, "invalid_article_number"
    return f"{number}{match.group(2).upper()}", None


def parse_part(value: Any) -> tuple[str | None, str | None]:
    if value is None or not str(value).strip():
        return None, None
    raw = normalize_digits(str(value)).strip()
    raw = re.sub(r"(?i)^(part|ભાગ|भाग)\s*[-:.]?\s*", "", raw).strip().upper()
    if _ROMAN.match(raw):
        return raw, None
    if raw.isdigit() and 0 < int(raw) < 40:
        return ingest._roman(int(raw)), None
    return None, "part_not_recognised"


def parse_pages(*values: Any) -> tuple[str | None, int | None, int | None, str | None]:
    numbers: list[int] = []
    seen_any = False
    for value in values:
        if value is None or not str(value).strip():
            continue
        seen_any = True
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        found = re.findall(r"\d{1,4}", normalize_digits(str(value)))
        if not found:
            return None, None, None, "page_reference_invalid"
        numbers += [int(n) for n in found]
    if not seen_any:
        return None, None, None, None
    first, last = min(numbers), max(numbers)
    if first < 1 or last - first > 60:
        return None, None, None, "page_reference_invalid"
    return (str(first) if first == last else f"{first}-{last}"), first, last, None


def parse_language(value: Any) -> str | None:
    if value is None or not str(value).strip():
        return None
    raw = str(value).strip().lower()
    for lang in languages.REGISTRY:
        if raw in (lang.code, lang.tag.lower(), lang.iso639_3, lang.english_name.lower(), lang.native_name.lower()):
            return lang.code
    return "?"


# ------------------------------------------------------------------------------ OCR checks
_VIRAMAS = frozenset("\u094D\u09CD\u0A4D\u0ACD\u0B4D\u0BCD\u0C4D\u0CCD\u0D4D")


def ocr_observations(text: str, script: str) -> dict[str, Any]:
    """Count the defects typical of Indic OCR and legacy-font text layers. Nothing is changed."""
    letters = detached = broken_conjunct = stray_marks = 0
    previous = ""
    for ch in text:
        category = unicodedata.category(ch)
        if category[0] == "L":
            letters += 1
        elif category in ("Mn", "Mc"):
            if previous in (" ", "\t", "\n", "\u00a0", ""):
                detached += 1
            elif unicodedata.category(previous)[0] not in ("L", "M") and previous not in "\u200c\u200d":
                stray_marks += 1
        if previous in _VIRAMAS and (ch.isspace() or category[0] == "P"):
            broken_conjunct += 1
        previous = ch
    counts = script_counts(text)
    total = sum(counts.values()) or 1
    per_1000 = lambda n: round(1000.0 * n / max(1, letters), 2)  # noqa: E731
    obs = {
        "letters": letters,
        "detached_vowel_signs": detached, "detached_per_1000": per_1000(detached),
        "broken_conjuncts": broken_conjunct, "broken_conjuncts_per_1000": per_1000(broken_conjunct),
        "stray_marks": stray_marks,
        "dotted_circles": text.count("\u25cc"),
        "replacement_characters": text.count("\ufffd"),
        "control_characters": sum(1 for ch in text if ord(ch) < 32 and ch not in "\n\r\t"),
        "expected_script_share": round(counts.get(script, 0) / total, 3),
        "other_scripts": {k: v for k, v in counts.items() if k != script},
    }
    score = (obs["detached_per_1000"] + obs["broken_conjuncts_per_1000"]
             + per_1000(obs["dotted_circles"] + obs["replacement_characters"] + stray_marks))
    obs["grade"] = "clean" if score == 0 else ("minor" if score <= 2 else ("poor" if score <= 20 else "unusable"))
    return obs


def normalise_ocr(text: str) -> tuple[str, list[dict[str, Any]]]:
    """A conservative, separate clean-up copy. The caller keeps the original.

    Only mechanical, script-independent repairs are made: Unicode NFC; a vowel sign that was
    separated from its consonant by spaces is re-attached; runs of spaces collapse. A sign that
    OCR recognised as the *wrong* sign cannot be repaired this way and is left as it is.
    """
    operations: list[dict[str, Any]] = []
    nfc = unicodedata.normalize("NFC", text)
    if nfc != text:
        operations.append({"op": "unicode_nfc", "changed_characters": sum(a != b for a, b in zip(text, nfc)) + abs(len(text) - len(nfc))})
    out: list[str] = []
    joined = 0
    for ch in nfc:
        if unicodedata.category(ch) in ("Mn", "Mc"):
            gap = 0
            while out and out[-1] in (" ", "\t", "\u00a0"):
                gap += 1
                out.pop()
            if gap and out and unicodedata.category(out[-1])[0] in ("L", "M"):
                joined += 1
            elif gap:
                out.extend(" " * gap)             # nothing to attach to: leave untouched
        out.append(ch)
    result = "".join(out)
    if joined:
        operations.append({"op": "reattach_detached_vowel_signs", "count": joined})
    collapsed = re.sub(r"[ \t\u00a0]{2,}", " ", result)
    if collapsed != result:
        operations.append({"op": "collapse_repeated_spaces", "count": len(result) - len(collapsed)})
    return collapsed, operations


# -------------------------------------------------------------------------------- records
@dataclass
class Record:
    row: int
    article_no: str | None
    text: str
    title: str | None = None
    part_no: str | None = None
    part_title: str | None = None
    chapter: str | None = None
    pages: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    source: str | None = None
    row_language: str | None = None
    claimed_status: str | None = None
    row_method: str | None = None
    edition: str | None = None
    warnings: list[str] = field(default_factory=list)
    rejected: str | None = None
    ocr: dict[str, Any] | None = None
    normalized: str | None = None
    normalization: list | None = None


def _get(row: dict[str, Any], mapping: dict[str, Any], name: str) -> Any:
    info = mapping["fields"].get(name)
    if not info:
        return None
    return info["constant"] if "constant" in info else row.get(info["column"])


def build_records(loaded: Loaded, mapping: dict[str, Any], language: str, extraction_method: str | None,
                  normalize: bool = False) -> tuple[list[Record], dict[str, int]]:
    """Rows -> records for one language. Rows explicitly in another language are left out."""
    script = languages.get(language).script
    skipped = Counter()
    records: list[Record] = []
    for index, row in enumerate(loaded.rows, start=1):
        row_language = parse_language(_get(row, mapping, "language"))
        if row_language and row_language != language:
            skipped["other_language_rows" if row_language != "?" else "unknown_language_rows"] += 1
            continue
        raw_text = _get(row, mapping, "text")
        text = "" if raw_text is None else str(raw_text)
        number, problem = parse_article_no(_get(row, mapping, "article_no"))
        rec = Record(row=index, article_no=number, text=text, row_language=row_language)
        title = _get(row, mapping, "title")
        rec.title = str(title).strip() if title is not None and str(title).strip() else None
        rec.part_no, part_problem = parse_part(_get(row, mapping, "part_no"))
        for name in ("part_title", "chapter", "source", "edition"):
            value = _get(row, mapping, name)
            setattr(rec, name, str(value).strip() if value is not None and str(value).strip() else None)
        rec.pages, rec.page_start, rec.page_end, page_problem = parse_pages(
            _get(row, mapping, "pages"), _get(row, mapping, "page_start"), _get(row, mapping, "page_end"))
        status = _get(row, mapping, "verification_status")
        rec.claimed_status = str(status).strip().lower() if status is not None and str(status).strip() else None
        method = _get(row, mapping, "extraction_method")
        rec.row_method = str(method).strip().lower() if method is not None and str(method).strip() else None
        for warning in (part_problem, page_problem):
            if warning:
                rec.warnings.append(warning)
        if rec.pages is None and not page_problem:
            rec.warnings.append("no_page_reference")
        if rec.part_no is None and not part_problem:
            rec.warnings.append("no_part")
        if rec.title is None:
            rec.warnings.append("no_title")
        if rec.claimed_status in ("verified", "true", "yes", "1", "human_verified"):
            rec.warnings.append("claimed_verified_ignored")      # a file cannot verify itself
        if problem:
            rec.rejected = problem
        elif not text.strip():
            rec.rejected = "empty_text"
        elif text.lstrip().upper().startswith("PLACEHOLDER"):
            rec.rejected = "template_placeholder"               # the sample templates are not data
        elif len(text) > 20000:
            rec.rejected = "longer_than_20000_characters"       # would be cut silently otherwise
        elif rec.row_method and rec.row_method not in IMPORT_METHODS:
            rec.rejected = "unknown_extraction_method"
        else:
            method_used = rec.row_method or extraction_method
            rec.ocr = ocr_observations(text, script)
            share = rec.ocr["expected_script_share"]
            foreign_limit = 0.01 if script == "Latn" else 0.35
            if rec.ocr["letters"] and (1 - share) > foreign_limit:
                rec.rejected = "mixed_language_content" if share >= 0.3 else "wrong_script"
            elif rec.ocr["grade"] == "unusable":
                rec.rejected = "ocr_unusable"
            elif rec.ocr["grade"] in ("minor", "poor") and method_used != "ocr":
                rec.rejected = "damaged_text_not_declared_as_ocr"
            elif rec.ocr["grade"] == "poor":
                rec.warnings.append("ocr_poor_quality")
            elif rec.ocr["grade"] == "minor":
                rec.warnings.append("ocr_minor_defects")
            if len(text.strip()) < 25 and not rec.rejected:
                rec.warnings.append("very_short_text")
            if normalize and method_used == "ocr" and not rec.rejected:
                cleaned, operations = normalise_ocr(text)
                if operations:
                    rec.normalized, rec.normalization = cleaned, operations
        records.append(rec)

    # duplicates inside the file: identical text is collapsed, different text rejects all copies
    groups: dict[str, list[Record]] = {}
    for rec in records:
        if rec.article_no and not rec.rejected:
            groups.setdefault(rec.article_no, []).append(rec)
    for number, group in groups.items():
        if len(group) < 2:
            continue
        if len({g.text.strip() for g in group}) == 1:
            for extra in group[1:]:
                extra.rejected = "duplicate_identical"
        else:
            for item in group:
                item.rejected = "duplicate_conflicting_text"
    return records, dict(skipped)


# -------------------------------------------------------------------------------- report
def _base(number: str) -> int | None:
    match = re.match(r"\d+", number or "")
    return int(match.group()) if match else None


def quality_report(*, path: Path, loaded: Loaded, mapping: dict[str, Any], records: list[Record],
                   skipped: dict[str, int], language: str, extraction_method: str | None,
                   source_key: str | None, expected: list[str] | None = None,
                   existing: dict[str, str] | None = None) -> dict[str, Any]:
    """The data-quality dashboard for one file and one language (JSON-serialisable)."""
    accepted = [r for r in records if not r.rejected]
    rejected = [r for r in records if r.rejected]
    numbers = [r.article_no for r in accepted]
    bases = sorted({b for b in (_base(n) for n in numbers) if b is not None})
    gaps = [str(n) for n in range(bases[0], bases[-1] + 1) if n not in set(bases)] if bases else []
    duplicate_numbers = sorted({r.article_no for r in rejected if r.rejected.startswith("duplicate") and r.article_no},
                               key=lambda n: (_base(n) or 0, n))
    by_part = Counter(r.part_no or "(no part given)" for r in accepted)
    by_grade = Counter((r.ocr or {}).get("grade", "n/a") for r in accepted)
    warnings = Counter(w for r in accepted for w in r.warnings)
    reasons = Counter(r.rejected for r in rejected)
    with_pages = sum(1 for r in accepted if r.pages)
    page_numbers = [p for r in accepted for p in (r.page_start, r.page_end) if p]
    order_breaks = []
    last_page = 0
    for r in accepted:
        if r.page_start:
            if r.page_start < last_page:
                order_breaks.append(r.article_no)
            last_page = max(last_page, r.page_start)
    report: dict[str, Any] = {
        "file": {"name": path.name, "sha256": sha256_of(path), "format": loaded.format,
                 "pages_in_file": loaded.pages, "page_markers": loaded.page_source},
        "language": language, "language_name": languages.get(language).english_name,
        "source_key": source_key, "extraction_method": extraction_method,
        "content_status_on_import": ingest.content_status_for(extraction_method) if extraction_method else None,
        "verification_status_on_import": "requires_human_verification",
        "mapping": {k: mapping[k] for k in ("status", "message", "fields", "ambiguous", "unmapped_columns") if k in mapping},
        "totals": {
            "records_discovered": len(loaded.rows),
            "records_for_this_language": len(records),
            "skipped": skipped,
            "import_ready": len(accepted),
            "rejected": len(rejected),
            "unique_article_numbers": len(set(numbers)),
        },
        "numbering": {
            "lowest": numbers and min(numbers, key=lambda n: (_base(n) or 0, n)) or None,
            "highest": numbers and max(numbers, key=lambda n: (_base(n) or 0, n)) or None,
            "lettered_articles": sorted((n for n in set(numbers) if not n.isdigit() and n != "Preamble"),
                                        key=lambda n: (_base(n) or 0, n)),
            "gaps_in_sequence": gaps,
            "gaps_note": ("Numbers absent between the lowest and highest number found. A gap is not proof of "
                          "missing data: omitted/repealed articles leave gaps in the publication itself."),
            "duplicate_article_numbers": duplicate_numbers,
        },
        "parts": dict(sorted(by_part.items())),
        "ocr_quality": {"grades": dict(by_grade), "warnings": dict(warnings),
                        "worst_records": [
                            {"article_no": r.article_no, "row": r.row, "grade": r.ocr["grade"],
                             "detached_vowel_signs": r.ocr["detached_vowel_signs"],
                             "broken_conjuncts": r.ocr["broken_conjuncts"]}
                            for r in sorted((r for r in records if r.ocr and r.ocr["grade"] not in ("clean",)),
                                            key=lambda r: -(r.ocr["detached_per_1000"] + r.ocr["broken_conjuncts_per_1000"]))[:15]],
                        "normalised_copies_prepared": sum(1 for r in accepted if r.normalized)},
        "coverage": {"with_page_reference": with_pages, "without_page_reference": len(accepted) - with_pages,
                     "page_range": [min(page_numbers), max(page_numbers)] if page_numbers else None,
                     "page_order_breaks": order_breaks,
                     "with_title": sum(1 for r in accepted if r.title), "with_part": sum(1 for r in accepted if r.part_no),
                     "with_chapter": sum(1 for r in accepted if r.chapter)},
        "rejections": {"by_reason": dict(reasons),
                       "records": [{"row": r.row, "article_no": r.article_no, "reason": r.rejected} for r in rejected[:200]]},
        "claimed_verified_ignored": warnings.get("claimed_verified_ignored", 0),
    }
    if expected is not None:
        want = {parse_article_no(n)[0] for n in expected} - {None}
        have = set(numbers)
        key = lambda n: (_base(n) or 0, n)  # noqa: E731
        report["numbering"]["expected_list"] = {
            "expected": len(want), "missing": sorted(want - have, key=key), "not_expected": sorted(have - want, key=key)}
    if existing is not None:
        same = sum(1 for r in accepted if existing.get(r.article_no, "").strip() == r.text.strip() and r.article_no in existing)
        differ = sorted(r.article_no for r in accepted if r.article_no in existing and existing[r.article_no].strip() != r.text.strip())
        report["database"] = {"already_stored_identical": same, "stored_with_different_text": differ,
                              "new": len(accepted) - same - len(differ)}
    blocking = []
    if mapping.get("status") != "ok":
        blocking.append("mapping_not_confirmed")
    if not accepted:
        blocking.append("no_importable_records")
    if rejected and len(rejected) > 0.2 * max(1, len(records)):
        blocking.append("more_than_20_percent_rejected")
    if reasons.get("duplicate_conflicting_text"):
        blocking.append("conflicting_duplicates")
    report["blocking_reasons"] = blocking
    report["ready_to_apply"] = not blocking
    return report


def render_markdown(report: dict[str, Any]) -> str:
    t, n, c = report["totals"], report["numbering"], report["coverage"]
    lines = [
        f"# Data quality report — {report['file']['name']} ({report['language_name']})", "",
        f"* SHA-256: `{report['file']['sha256']}`", f"* Format: {report['file']['format']}",
        f"* Extraction method declared: **{report['extraction_method'] or 'not declared'}** → stored as "
        f"`{report['content_status_on_import'] or '—'}`, `{report['verification_status_on_import']}`",
        f"* Field mapping: **{report['mapping']['status']}** — {report['mapping']['message']}",
        f"* Ready to apply: **{'yes' if report['ready_to_apply'] else 'NO — ' + ', '.join(report['blocking_reasons'])}**", "",
        "| Measure | Value |", "|---|---|",
        f"| Records discovered in the file | {t['records_discovered']} |",
        f"| Records for this language | {t['records_for_this_language']} |",
        f"| Skipped (other language) | {sum(t['skipped'].values())} |",
        f"| Import-ready | {t['import_ready']} |", f"| Rejected | {t['rejected']} |",
        f"| Unique article numbers | {t['unique_article_numbers']} |",
        f"| Lowest – highest | {n['lowest']} – {n['highest']} |",
        f"| Lettered articles | {len(n['lettered_articles'])} |",
        f"| Gaps in the number sequence | {len(n['gaps_in_sequence'])} |",
        f"| Duplicate article numbers | {len(n['duplicate_article_numbers'])} |",
        f"| With page reference | {c['with_page_reference']} of {t['import_ready']} |",
        f"| With title / Part / Chapter | {c['with_title']} / {c['with_part']} / {c['with_chapter']} |", "",
        "## Numbering", "", f"Gaps: {', '.join(n['gaps_in_sequence'][:80]) or 'none'}", "", f"_{n['gaps_note']}_", "",
        f"Duplicates: {', '.join(n['duplicate_article_numbers']) or 'none'}", "",
    ]
    if "expected_list" in n:
        e = n["expected_list"]
        lines += [f"Against the supplied expected list ({e['expected']} numbers): missing {', '.join(e['missing']) or 'none'}; "
                  f"not expected {', '.join(e['not_expected']) or 'none'}", ""]
    lines += ["## Part-wise distribution", "", "| Part | Articles |", "|---|---|"]
    lines += [f"| {part} | {count} |" for part, count in report["parts"].items()]
    lines += ["", "## Text / OCR quality", "", "| Grade | Records |", "|---|---|"]
    lines += [f"| {grade} | {count} |" for grade, count in report["ocr_quality"]["grades"].items()]
    lines += ["", "| Warning | Records |", "|---|---|"]
    lines += [f"| {w} | {count} |" for w, count in report["ocr_quality"]["warnings"].items()] or ["| none | 0 |"]
    lines += ["", "## Source and page coverage", "",
              f"Pages referenced: {c['page_range'] or 'none'}; page order breaks at: {', '.join(c['page_order_breaks']) or 'none'}", "",
              "## Rejected records", "", "| Reason | Records |", "|---|---|"]
    lines += [f"| {reason} | {count} |" for reason, count in report["rejections"]["by_reason"].items()] or ["| none | 0 |"]
    if "database" in report:
        d = report["database"]
        lines += ["", "## Against the database", "",
                  f"New: {d['new']} · already stored and identical: {d['already_stored_identical']} · "
                  f"stored with different text: {len(d['stored_with_different_text'])}"]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------------- apply
@dataclass
class ApplyCounters:
    articles_written: int = 0
    articles_unchanged: int = 0
    articles_conflicting: int = 0
    articles_skipped_verified: int = 0


def existing_texts(conn, language: str) -> dict[str, str]:
    out = {r["article_no"]: r["body"] or "" for r in conn.execute(
        "SELECT a.article_no, t.body FROM article_texts t JOIN constitution_articles a ON a.id = t.article_id"
        " WHERE t.language = ?", (language,))}
    if language in ("en", "gu"):
        for r in conn.execute(f"SELECT article_no, text_{language} AS body FROM constitution_articles"
                              f" WHERE text_status = 'verified_source_text' AND TRIM(COALESCE(text_{language},'')) <> ''"):
            out.setdefault(r["article_no"], r["body"])
    return out


def apply(conn, records: list[Record], report: dict[str, Any], *, language: str, source_key: str,
          source_file: str, extraction_method: str, edition: str | None = None,
          replace_existing: bool = False, backup_path: str | None = None) -> dict[str, Any]:
    """Write the accepted records in ONE transaction and journal every change."""
    from ..db import transaction

    if extraction_method not in IMPORT_METHODS:
        raise ValueError(f"extraction method must be one of {', '.join(IMPORT_METHODS)}")
    if not report.get("ready_to_apply"):
        raise ValueError("report is not ready to apply: " + ", ".join(report.get("blocking_reasons", [])))
    accepted = [r for r in records if not r.rejected]
    counters = ApplyCounters()
    with transaction(conn):
        run_id = conn.execute("INSERT INTO ingest_runs (source_key, source_file, status) VALUES (?,?,'running')",
                              (source_key, source_file)).lastrowid
        by_method: dict[str, list[ingest.ParsedArticle]] = {}
        for r in accepted:
            by_method.setdefault(r.row_method or extraction_method, []).append(ingest.ParsedArticle(
                article_no=r.article_no, title=r.title or "", body=r.text, line_no=r.row,
                page_start=r.page_start or 0, page_end=r.page_end or 0, part_no=r.part_no,
                part_title=r.part_title, chapter_title=r.chapter, pages=r.pages or "",
                locator=f"{'pages ' + r.pages + ' of ' if r.pages else ''}{r.source or source_file} (record {r.row} of {source_file})",
                normalized_body=r.normalized, normalization=r.normalization))
        for method, articles in by_method.items():
            preamble = [a for a in articles if a.article_no == "Preamble"]
            ingest.write_articles(conn, [a for a in articles if a.article_no != "Preamble"] + preamble, counters,
                                  source_key=source_key, source_file=source_file, language=language,
                                  replace_existing=replace_existing, extraction_method=method,
                                  edition=edition or next((r.edition for r in accepted if r.edition), None),
                                  run_id=run_id)
        log = {**report, "run_id": run_id, "backup": backup_path, "result": vars(counters)}
        conn.execute(
            """UPDATE ingest_runs SET finished_at = datetime('now'), articles_found = ?, articles_written = ?,
                   duplicates = ?, missing_numbers = ?, report_json = ?, status = 'completed' WHERE id = ?""",
            (len(records), counters.articles_written, len(report["numbering"]["duplicate_article_numbers"]),
             json.dumps(report["numbering"]["gaps_in_sequence"]), json.dumps(log, ensure_ascii=False), run_id))
    return {"run_id": run_id, **vars(counters)}
