#!/usr/bin/env python3
"""Read-only inventory of Constitution data files on the owner's own device.

Run it where the files actually are (e.g. Termux on the phone, or a PC):

    python scripts/inventory_local_data.py ~/NYAYMITRA-AI ~/storage/shared/Download \\
        --out data/reports/local-data-inventory.json

It only READS files: nothing is modified, moved, uploaded, OCR'd or imported. For each
candidate file it records path, size, SHA-256 and a few facts that decide whether the file
can be imported (rows/columns for CSV, record counts for JSON, page count for PDF, tables for
SQLite, and the script mix of the text: Gujarati / Latin / Ol Chiki). Standard library only;
PDF page counts need the optional ``pypdf`` package.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

EXTENSIONS = {".pdf", ".csv", ".tsv", ".json", ".jsonl", ".txt", ".md", ".db", ".sqlite", ".sqlite3", ".xlsx", ".gz", ".zip"}
NAME_HINT = re.compile(r"constitution|samvidhan|bandharan|gujarati|article|ocr|master|index|mapping|nyaymitra|બંધારણ|સંવિધાન", re.I)
SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "__pycache__", "site-packages", ".cache", "Android"}
SAMPLE_BYTES = 2_000_000
ARTICLE_NO = re.compile(r"^\s*([0-9\u0AE6-\u0AEF]{1,3})\s*[-–]?\s*([A-Za-z\u0A95-\u0AB9]{0,2})\s*$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def script_mix(text: str) -> dict:
    counts: Counter = Counter()
    for ch in text:
        code = ord(ch)
        if 0x0A80 <= code <= 0x0AFF:
            counts["gujarati"] += 1
        elif 0x1C50 <= code <= 0x1C7F:
            counts["ol_chiki_santali"] += 1
        elif 0x0900 <= code <= 0x097F:
            counts["devanagari"] += 1
        elif ch.isalpha() and code < 0x250:
            counts["latin"] += 1
        elif ch == "\ufffd":
            counts["replacement_char"] += 1
        elif 0xE000 <= code <= 0xF8FF:
            counts["private_use"] += 1
    total = sum(counts.values()) or 1
    return {k: round(v / total, 4) for k, v in counts.most_common()}


def article_stats(values: list[str]) -> dict:
    """Duplicates / gaps for a column or key that looks like article numbers."""
    parsed, bad = [], 0
    for value in values:
        match = ARTICLE_NO.match(str(value).replace("Article", "").replace("અનુચ્છેદ", ""))
        if match:
            parsed.append((int(match.group(1)), match.group(2).upper()))
        else:
            bad += 1
    labels = Counter(f"{n}{s}" for n, s in parsed)
    bases = {n for n, _ in parsed}
    top = max(bases) if bases else 0
    return {
        "values": len(values), "parsed_as_article_numbers": len(parsed), "unparsed": bad,
        "distinct_labels": len(labels), "duplicates": sorted(l for l, c in labels.items() if c > 1)[:100],
        "highest_base_number": top,
        "missing_base_numbers_1_to_395": [n for n in range(1, 396) if n not in bases][:400] if bases else None,
    }


def looks_like_article_column(name: str) -> bool:
    return bool(re.search(r"article|art_?no|anuchhed|કલમ|અનુચ્છેદ|number", str(name), re.I))


def inspect_csv(path: Path, delimiter: str) -> dict:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        rows = list(csv.reader(handle, delimiter=delimiter))
    if not rows:
        return {"rows": 0}
    header, body = rows[0], rows[1:]
    info = {"rows": len(body), "columns": header,
            "script_mix": script_mix(" ".join(" ".join(r) for r in body[:2000]))}
    for index, name in enumerate(header):
        if looks_like_article_column(name):
            info.setdefault("article_columns", {})[name] = article_stats([r[index] for r in body if index < len(r)])
    return info


def inspect_json(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    info: dict = {"script_mix": script_mix(raw[:SAMPLE_BYTES])}
    try:
        data = [json.loads(line) for line in raw.splitlines() if line.strip()] if path.suffix == ".jsonl" else json.loads(raw)
    except ValueError as exc:
        return info | {"parse_error": str(exc)[:120]}
    records = data if isinstance(data, list) else None
    if isinstance(data, dict):
        info["top_level_keys"] = list(data)[:40]
        lists = {k: v for k, v in data.items() if isinstance(v, list)}
        info["list_lengths"] = {k: len(v) for k, v in lists.items()}
        records = max(lists.values(), key=len) if lists else None
    if records and isinstance(records[0], dict):
        info["records"] = len(records)
        info["record_keys"] = list(records[0])[:40]
        for key in records[0]:
            if looks_like_article_column(key):
                info.setdefault("article_columns", {})[key] = article_stats([r.get(key, "") for r in records if isinstance(r, dict)])
    elif records is not None:
        info["records"] = len(records)
    return info


def inspect_sqlite(path: Path) -> dict:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        tables = {}
        for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            try:
                count = conn.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
                columns = [r[1] for r in conn.execute(f'PRAGMA table_info("{name}")')]
            except sqlite3.Error as exc:
                count, columns = f"error: {exc}", []
            tables[name] = {"rows": count, "columns": columns}
        return {"tables": tables}
    finally:
        conn.close()


def inspect_pdf(path: Path) -> dict:
    try:
        from pypdf import PdfReader
    except ImportError:
        return {"note": "install pypdf to record page count and text-layer facts"}
    reader = PdfReader(str(path))
    pages = len(reader.pages)
    sample = [reader.pages[i].extract_text() or "" for i in sorted({0, pages // 4, pages // 2, (3 * pages) // 4, pages - 1}) if 0 <= i < pages]
    return {"pages": pages, "sampled_pages_with_text": sum(1 for s in sample if s.strip()),
            "sampled_pages": len(sample), "script_mix_of_text_layer": script_mix(" ".join(sample)),
            "note": "no text on sampled pages = scanned PDF (text exists only in separate OCR output)"
                    if not any(s.strip() for s in sample) else None}


def inspect(path: Path) -> dict:
    suffix = path.suffix.lower()
    entry = {"path": str(path), "format": suffix.lstrip("."), "size_bytes": path.stat().st_size}
    try:
        entry["sha256"] = sha256(path)
        if suffix in {".csv", ".tsv"}:
            entry.update(inspect_csv(path, "\t" if suffix == ".tsv" else ","))
        elif suffix in {".json", ".jsonl"}:
            entry.update(inspect_json(path))
        elif suffix in {".db", ".sqlite", ".sqlite3"}:
            entry.update(inspect_sqlite(path))
        elif suffix == ".pdf":
            entry.update(inspect_pdf(path))
        elif suffix in {".txt", ".md"}:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                sample = handle.read(SAMPLE_BYTES)
            entry.update({"script_mix": script_mix(sample), "lines_in_sample": sample.count("\n")})
    except Exception as exc:  # one unreadable file must not stop the inventory
        entry["error"] = f"{type(exc).__name__}: {exc}"[:200]
    return entry


def candidates(roots: list[Path], everything: bool):
    for root in roots:
        if root.is_file():
            yield root
            continue
        for path in sorted(root.rglob("*")):
            if any(part in SKIP_DIRS for part in path.parts) or not path.is_file():
                continue
            if path.suffix.lower() in EXTENSIONS and (everything or NAME_HINT.search(str(path))):
                yield path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("roots", nargs="+", type=Path, help="folders or files to inspect")
    parser.add_argument("--all", action="store_true", help="include data files whose path has no Constitution-related word")
    parser.add_argument("--out", type=Path, help="write the JSON inventory here (default: print)")
    args = parser.parse_args(argv)
    missing = [str(r) for r in args.roots if not r.exists()]
    files = [inspect(p) for p in candidates([r for r in args.roots if r.exists()], args.all)]
    report = {"roots": [str(r) for r in args.roots], "roots_not_found": missing, "files_found": len(files), "files": files}
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"{len(files)} file(s) inventoried -> {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
