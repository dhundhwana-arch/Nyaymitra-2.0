#!/usr/bin/env python3
"""Read-only inventory (and optional transfer package) of Constitution data on the owner's device.

Run it where the files actually are (Termux on the tablet, or a PC). Standard library only.

    # 1. Inventory: JSON for the machine, Markdown for you
    python scripts/inventory_local_data.py ~/NYAYMITRA-AI \\
        --search ~/storage/shared \\
        --out ~/nyaymitra-inventory.json --markdown ~/nyaymitra-inventory.md

    # 2. Same, and also COPY the relevant files into a transfer package (+ .tar.gz)
    python scripts/inventory_local_data.py ~/NYAYMITRA-AI --search ~/storage/shared \\
        --package ~/nyaymitra-transfer

    # 3. Check a package (or an unpacked copy of it) against its manifest
    python scripts/inventory_local_data.py --verify-package ~/nyaymitra-transfer

What the two kinds of folder mean
    positional folders   your project folders: every data file in them is listed
    --search folders     broad places (shared storage, Download): ONLY files whose path contains
                         constitution / samvidhan / bandharan / nyaymitra / સંવિધાન / બંધારણ are
                         listed. Other files are not opened, not hashed and not named anywhere.
    (A positional folder that is shared storage, Download or Documents is treated as --search.)

Guarantees
    * Original files are opened for reading only. Nothing is modified, renamed, moved, deleted,
      uploaded, OCR'd or imported. After the run the tool re-checks size and modification time
      of every file it touched (and, when packaging, the SHA-256) and reports the result.
    * Files that look like credentials or personal data (complaints, users, chats), SQLite
      databases and .zip/.gz archives are listed with a checksum but never copied into a package.
    * Language and "OCR or PDF text" labels are GUESSES from file names and letters, marked as
      such. You confirm them in SOURCE_INFO.md.

PDF page counts need the optional ``pypdf`` package; without it the PDF is still hashed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import tarfile
import time
from collections import Counter
from pathlib import Path

TOOL_VERSION = "2.1"
EXTENSIONS = {".pdf", ".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".txt", ".text", ".md", ".log", ".yaml", ".yml",
              ".db", ".sqlite", ".sqlite3", ".xlsx", ".gz", ".zip"}
DATABASES = {".db", ".sqlite", ".sqlite3"}
TEXT_LIKE = {".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".txt", ".text", ".md", ".log", ".yaml", ".yml"}
# Words that make a file relevant inside a project folder.
NAME_HINT = re.compile(r"constitution|samvidhan|sanvidhan|bandharan|gujarati|article|ocr|master|index|mapping|nyaymitra|બંધારણ|સંવિધાન", re.I)
# Words that make a file relevant ANYWHERE (used for shared storage).
STRONG_HINT = re.compile(r"constitution|samvidhan|sanvidhan|bandharan|nyaymitra|બંધારણ|સંવિધાન", re.I)
SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "env", "__pycache__", "site-packages", ".cache", ".npm",
             "Android", "DCIM", "Pictures", "Movies", "Music", ".thumbnails", ".trash", ".Trash"}
PACKAGE_MARKER = "NYAYMITRA_TRANSFER_PACKAGE"
BROAD_NAMES = {"shared", "download", "downloads", "documents", "sdcard", "emulated", "0"}
SECRET_NAME = re.compile(r"(^\.env)|(\.pem$)|(\.key$)|(\.p12$)|(\.keystore$)|(\.jks$)|credential|secret|token|password|passwd|id_rsa|service[-_]?account", re.I)
# Key prefixes are assembled from pieces so that this detector is not itself reported by secret scanners.
_KEY_PREFIXES = ("s" + "k-", "AI" + "za", "g" + "sk_")
SECRET_CONTENT = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
    + r"|\b" + re.escape(_KEY_PREFIXES[0]) + r"[A-Za-z0-9_-]{20,}"
    + r"|\b" + re.escape(_KEY_PREFIXES[1]) + r"[0-9A-Za-z_-]{30,}"
    + r"|\b" + re.escape(_KEY_PREFIXES[2]) + r"[A-Za-z0-9]{20,}"
    + r"|\bgh[pousr]_[A-Za-z0-9]{30,}|\bxox[baprs]-[A-Za-z0-9-]{10,}"
    + r"|(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|password|passwd)\"?\s*[:=]\s*\"?[^\s\"',]{8,}", re.I)
# Names that suggest data about people (complaints, users, chats). Such files are listed with a
# checksum only: their content is not inspected and they are never copied into a package.
PERSONAL_NAME = re.compile(r"complaint|grievance|citizen|(^|[_\-./])users?([_\-./]|$)|feedback|chat|conversation|session"
                           r"|contact|aadhaar|aadhar|personal|private|ફરિયાદ", re.I)
ARCHIVES = {".gz", ".zip"}
OWNER_NOTES = "SOURCE_INFO.md"          # edited by the owner after packaging, so it is not checksummed
SAMPLE_BYTES = 2_000_000
ARTICLE_NO = re.compile(r"^\s*([0-9\u0AE6-\u0AEF\u0966-\u096F]{1,3})\s*[-–]?\s*([A-Za-z\u0A85-\u0AB9]{0,2})\s*\.?\s*$")
_DIGITS = {ord(c): str(i) for base in (0x0AE6, 0x0966) for i, c in enumerate(map(chr, range(base, base + 10)))}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:                      # read-only
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
    """Duplicates and gaps for a column that looks like article numbers. Nothing is converted
    except digits: a Gujarati letter suffix is reported as written, never mapped to A/B/C."""
    parsed, bad = [], 0
    for value in values:
        cleaned = re.sub(r"(?i)article|અનુચ્છેદ|કલમ|अनुच्छेद", "", str(value))
        match = ARTICLE_NO.match(cleaned)
        if match:
            parsed.append((int(match.group(1).translate(_DIGITS)), match.group(2).upper()))
        else:
            bad += 1
    labels = Counter(f"{n}{s}" for n, s in parsed)
    bases = {n for n, _ in parsed}
    low, top = (min(bases), max(bases)) if bases else (0, 0)
    return {
        "values": len(values), "parsed_as_article_numbers": len(parsed), "unparsed": bad,
        "distinct_labels": len(labels), "duplicates": sorted(l for l, c in labels.items() if c > 1)[:100],
        "lowest_base_number": low, "highest_base_number": top,
        "gaps_between_lowest_and_highest": [n for n in range(low, top + 1) if n not in bases][:500] if bases else None,
        "gaps_note": "A gap is not proof of missing data: omitted/repealed articles leave gaps in the publication itself.",
        "gujarati_letter_suffixes": sorted({s for _, s in parsed if s and not s.isascii()}),
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
        data = ([json.loads(line) for line in raw.splitlines() if line.strip()]
                if path.suffix.lower() in (".jsonl", ".ndjson") else json.loads(raw))
    except ValueError as exc:
        return info | {"parse_error": str(exc)[:120]}
    records = data if isinstance(data, list) else None
    if isinstance(data, dict):
        info["top_level_keys"] = [str(k)[:60] for k in list(data)[:40]]
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
    # immutable=1: SQLite takes no locks and creates no -wal/-shm/-journal file next to the database.
    conn = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
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
        return {"note": "page count not recorded (optional: pip install pypdf)"}
    reader = PdfReader(str(path))
    pages = len(reader.pages)
    sample = [reader.pages[i].extract_text() or "" for i in sorted({0, pages // 4, pages // 2, (3 * pages) // 4, pages - 1}) if 0 <= i < pages]
    meta = {}
    try:
        meta = {k.lstrip("/"): str(v)[:200] for k, v in (reader.metadata or {}).items()
                if k in ("/Title", "/Producer", "/Creator", "/CreationDate", "/ModDate")}
    except Exception:
        pass
    return {"pages": pages, "pdf_metadata": meta, "sampled_pages_with_text": sum(1 for s in sample if s.strip()),
            "sampled_pages": len(sample), "script_mix_of_text_layer": script_mix(" ".join(sample)),
            "note": "no text on sampled pages = scanned PDF (text exists only in separate OCR output)"
                    if not any(s.strip() for s in sample) else None}


# ----------------------------------------------------------------------------- labels (guesses)
def guess_language(path: Path, mix: dict) -> tuple[str, str]:
    gu, la, de = mix.get("gujarati", 0), mix.get("latin", 0), mix.get("devanagari", 0)
    if mix:
        if gu >= 0.3:
            return "gujarati", f"letters in the file: {gu:.0%} Gujarati"
        if de >= 0.2 and la >= 0.2:
            return "unclassified", f"mixed Devanagari ({de:.0%}) and Latin ({la:.0%}) letters — possibly a Hindi–English diglot"
        if la >= 0.9 and gu < 0.02:
            name = str(path).lower()
            if re.search(r"gujarati|guj[_\-. ]|[_\-.]gu[_\-.]|samvidhan|bandharan", name):
                return "gujarati", "file name says Gujarati but the content sampled is Latin letters only (index or log?)"
            return "english", f"letters in the file: {la:.0%} Latin"
    name = str(path).lower()
    if re.search(r"gujarati|guj[_\-. ]|[_\-.]gu[_\-.]|samvidhan|sanvidhan|bandharan|બંધારણ|સંવિધાન", name):
        return "gujarati", "file name only"
    if re.search(r"english|[_\-.]en[_\-.]|[_\-.]eng[_\-.]", name):
        return "english", "file name only"
    return "unclassified", "could not tell from the name or the letters"


def guess_kind(path: Path) -> str:
    name, suffix = path.name.lower(), path.suffix.lower()
    if suffix == ".pdf":
        return "source_pdf"
    if suffix in DATABASES:
        return "database"
    if suffix == ".log" or re.search(r"(^|[_\-.])logs?([_\-.]|$)", name):
        return "log"
    if re.search(r"index|mapping|master|\bmap\b|toc|contents", name):
        return "index_or_mapping"
    if re.search(r"ocr", str(path).lower()):
        return "ocr_output"
    if suffix in (".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".xlsx"):
        return "article_data"
    if suffix in (".gz", ".zip"):
        return "archive"
    return "text"


def guess_derivation(path: Path) -> tuple[str, str]:
    text = str(path).lower()
    if path.suffix.lower() == ".pdf":
        return "original_document", "it is a PDF"
    if re.search(r"ocr|tesseract|vision|scan", text):
        return "ocr_derived", "the path contains ocr/tesseract/vision/scan"
    if re.search(r"pdftotext|text[_-]?layer|pymupdf|fitz|pypdf|pdfminer|pdfplumber|extract|parsed|parse", text):
        return "pdf_text_derived", "the path contains extract/parsed/pdftotext or a PDF library name"
    return "unknown", "nothing in the path says how the file was made"


def looks_secret(path: Path) -> str | None:
    if SECRET_NAME.search(path.name):
        return "file name looks like a credential file"
    if path.suffix.lower() in TEXT_LIKE or path.suffix == "":
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                if SECRET_CONTENT.search(handle.read(SAMPLE_BYTES)):
                    return "content contains something that looks like a key, token or password"
        except OSError:
            return None
    return None


def inspect(path: Path, root: Path, mode: str) -> dict:
    suffix = path.suffix.lower()
    stat = path.stat()
    try:
        relative = str(path.relative_to(root)) if root.is_dir() else path.name
    except ValueError:
        relative = path.name
    entry = {"path": str(path), "root": str(root), "relative_path": relative, "found_by": mode,
             "format": suffix.lstrip("."), "size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns,
             "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))}
    try:
        entry["sha256"] = sha256(path)
        secret = looks_secret(path)
        if secret:
            entry["possible_secret"] = secret          # no content facts are recorded for such a file
        elif PERSONAL_NAME.search(relative):
            entry["possible_personal_data"] = "the name suggests data about people (complaints, users, chats…)"
        elif suffix in {".csv", ".tsv"}:
            entry.update(inspect_csv(path, "\t" if suffix == ".tsv" else ","))
        elif suffix in {".json", ".jsonl", ".ndjson"}:
            entry.update(inspect_json(path))
        elif suffix in DATABASES:
            entry.update(inspect_sqlite(path))
        elif suffix == ".pdf":
            entry.update(inspect_pdf(path))
        elif suffix in TEXT_LIKE:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                sample = handle.read(SAMPLE_BYTES)
            entry.update({"script_mix": script_mix(sample), "lines_in_sample": sample.count("\n")})
    except Exception as exc:  # one unreadable file must not stop the inventory
        entry["error"] = f"{type(exc).__name__}: {exc}"[:200]
    mix = entry.get("script_mix") or entry.get("script_mix_of_text_layer") or {}
    entry["language_guess"], entry["language_basis"] = guess_language(path, mix)
    entry["kind_guess"] = guess_kind(path)
    entry["derivation_guess"], entry["derivation_basis"] = guess_derivation(path)
    return entry


def is_broad(root: Path) -> bool:
    try:
        resolved = root.resolve()
    except OSError:
        resolved = root
    return (resolved == Path.home() or root.name.lower() in BROAD_NAMES or resolved.name.lower() in BROAD_NAMES
            or str(resolved).startswith(("/storage/", "/sdcard")) or str(resolved) in ("/storage", "/sdcard", "/"))


def candidates(roots: list[tuple[Path, str]], everything: bool, counters: Counter):
    """Yield (path, root, mode). Directories are walked without following links; nothing is opened here."""
    seen: set[str] = set()
    for root, mode in roots:
        if root.is_file():
            yield root, root.parent, mode
            continue
        for folder, dirs, files in os.walk(root, onerror=lambda e: counters.update(unreadable_folders=1)):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS
                             and not os.path.exists(os.path.join(folder, d, PACKAGE_MARKER)))
            if os.path.exists(os.path.join(folder, PACKAGE_MARKER)):
                dirs[:] = []
                continue
            for name in sorted(files):
                path = Path(folder) / name
                if path.suffix.lower() not in EXTENSIONS or path.is_symlink() or not path.is_file():
                    continue
                if name.startswith("nyaymitra-transfer") or name.startswith("nyaymitra-inventory"):
                    continue                              # this tool's own output
                wanted = (STRONG_HINT.search(str(path)) if mode == "search"
                          else (everything or NAME_HINT.search(str(path))))
                if not wanted:
                    counters["data_files_not_listed_no_matching_name"] += 1
                    continue
                key = os.path.realpath(path)
                if key in seen:
                    continue
                seen.add(key)
                yield path, root, mode


def unchanged(files: list[dict], rehash: bool) -> dict:
    """Prove the originals are as they were when first read."""
    changed = []
    for entry in files:
        path = Path(entry["path"])
        try:
            stat = path.stat()
            same = stat.st_size == entry["size_bytes"] and stat.st_mtime_ns == entry["mtime_ns"]
            if same and rehash and "sha256" in entry:
                same = sha256(path) == entry["sha256"]
        except OSError:
            same = False
        if not same:
            changed.append(entry["path"])
    return {"checked": len(files), "method": "size + modification time" + (" + SHA-256" if rehash else ""),
            "unchanged": not changed, "changed_files": changed}


# ----------------------------------------------------------------------------- markdown
def _size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return str(n)


def _facts(e: dict) -> str:
    bits = []
    if "pages" in e:
        bits.append(f"{e['pages']} pages")
        if e.get("sampled_pages") and not e.get("sampled_pages_with_text"):
            bits.append("no text layer on sampled pages (scan)")
    if "rows" in e:
        bits.append(f"{e['rows']} rows; columns: {', '.join(map(str, e.get('columns', [])[:12]))}")
    if "records" in e:
        bits.append(f"{e['records']} records; keys: {', '.join(map(str, e.get('record_keys', [])[:12]))}")
    if "tables" in e:
        bits.append("tables: " + ", ".join(f"{k} ({v['rows']})" for k, v in list(e["tables"].items())[:12]))
    for column, s in (e.get("article_columns") or {}).items():
        bits.append(f"`{column}`: {s['distinct_labels']} distinct numbers, {len(s['duplicates'])} duplicated, "
                    f"{len(s['gaps_between_lowest_and_highest'] or [])} gaps between {s['lowest_base_number']} and "
                    f"{s['highest_base_number']}" + (f", Gujarati letter suffixes: {' '.join(s['gujarati_letter_suffixes'])}"
                                                     if s["gujarati_letter_suffixes"] else ""))
    if e.get("possible_secret"):
        bits.append("**POSSIBLE SECRET — not inspected, never packaged**")
    if e.get("possible_personal_data"):
        bits.append("**POSSIBLE PERSONAL DATA — not inspected, never packaged**")
    if e.get("error"):
        bits.append("error: " + e["error"])
    return "; ".join(bits).replace("|", "\\|") or "—"


def render_markdown(report: dict) -> str:
    files = report["files"]
    lines = ["# NYAYMITRA 2.0 — local Constitution data inventory", "",
             f"Made on {report['generated_at']} by `inventory_local_data.py` {TOOL_VERSION}. Read-only: no file was changed.", "",
             f"* Project folders: {', '.join(f'`{r}`' for r in report['project_roots']) or 'none'}",
             f"* Searched by name only: {', '.join(f'`{r}`' for r in report['search_roots']) or 'none'}",
             f"* Folders not found: {', '.join(f'`{r}`' for r in report['roots_not_found']) or 'none'}",
             f"* Files listed: **{len(files)}** ({_size(sum(f['size_bytes'] for f in files))})",
             f"* Other data files seen but not listed (name not related): {report['not_listed']['data_files_not_listed_no_matching_name']}",
             f"* Originals unchanged after the run: **{'yes' if report['originals']['unchanged'] else 'NO — see JSON'}** "
             f"({report['originals']['method']}, {report['originals']['checked']} files)", "",
             "Language, kind and \"how it was made\" are **guesses** from names and letters. Please correct them.", ""]
    for language, title in (("gujarati", "Gujarati"), ("english", "English"), ("unclassified", "Not classified")):
        group = [f for f in files if f["language_guess"] == language]
        lines += [f"## {title} ({len(group)})", ""]
        if not group:
            lines += ["Nothing found.", ""]
            continue
        lines += ["| File | Size | Kind (guess) | Made by (guess) | Facts | SHA-256 |", "|---|---|---|---|---|---|"]
        for f in group:
            lines.append(f"| `{f['path']}` | {_size(f['size_bytes'])} | {f['kind_guess']} | {f['derivation_guess']} | "
                         f"{_facts(f)} | `{f.get('sha256', '—')[:16]}…` |")
        lines.append("")
    if report.get("package"):
        p = report["package"]
        lines += ["## Transfer package", "", f"* Folder: `{p['folder']}`", f"* Archive: `{p['archive']}`",
                  f"* Archive SHA-256: `{p['archive_sha256']}`", f"* Files copied: {p['files_copied']} ({_size(p['bytes_copied'])})",
                  f"* Copies identical to originals: **{'yes' if p['copies_verified'] else 'NO'}**", ""]
        if p["not_packaged"]:
            lines += ["Listed but NOT copied:", ""] + [f"* `{x['path']}` — {x['reason']}" for x in p["not_packaged"]] + [""]
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------- package
SOURCE_INFO = """# Source information — please fill in (plain answers are fine)

Nobody but you knows these facts. Without them the text can be imported only as "needs review".

## Gujarati
- Title printed on the PDF's title page:
- Edition / "as on" date printed in it:
- Publisher printed in it:
- Where the PDF was downloaded from (web address) and roughly when:
- Number of pages in the PDF:
- How the Gujarati text files were made (tick one):  [ ] OCR   [ ] copied from the PDF's text   [ ] typed   [ ] not sure
- OCR program and language setting used (e.g. tesseract, guj):
- Do article numbers in this edition carry Gujarati letters (for example 21 + a Gujarati letter for 21A)? Which letters did you see?
- Has anyone proof-read any part of it? Which articles?

## English
- Title printed on the PDF's title page:
- Edition / "as on" date printed in it:
- Is it English only, or Hindi and English together (diglot)?
- Where it was downloaded from and roughly when:
- How the English article data was made:  [ ] OCR   [ ] copied from the PDF's text   [ ] typed   [ ] not sure
- Script or program that split it into Parts and Articles (file name):

## Corrections to the guesses in INVENTORY.md
- (file) → (correct language / how it was made)
"""


def build_package(report: dict, dest: Path, max_mb: float, include_databases: bool, include_archives: bool = False) -> dict:
    if dest.exists() and any(dest.iterdir()):
        raise SystemExit(f"{dest} already exists and is not empty. Choose a new folder name; nothing was changed.")
    for existing in (Path(str(dest) + ".tar.gz"), Path(str(dest) + ".tar.gz.sha256")):
        if existing.exists():
            raise SystemExit(f"{existing} already exists and will not be overwritten. Choose a new folder name; nothing was changed.")
    dest.mkdir(parents=True, exist_ok=True)
    (dest / PACKAGE_MARKER).write_text("Created by scripts/inventory_local_data.py. Copies only; originals untouched.\n", encoding="utf-8")
    copied, skipped, manifest, used = [], [], [], set()
    for entry in report["files"]:
        src = Path(entry["path"])
        reason = None
        if entry.get("possible_secret"):
            reason = "possible secret: " + entry["possible_secret"]
        elif entry.get("possible_personal_data"):
            reason = "possible personal data: " + entry["possible_personal_data"]
        elif "." + entry["format"] in ARCHIVES and not include_archives:
            reason = "archive: its contents cannot be checked by this tool; unpack it and list the folder, or use --include-archives"
        elif entry["format"] in {s.lstrip(".") for s in DATABASES} and not include_databases:
            reason = "database (may hold personal or complaint data); use --include-databases only if it holds Constitution data alone"
        elif entry.get("error") and "sha256" not in entry:
            reason = "could not be read"
        elif max_mb and entry["size_bytes"] > max_mb * 1024 * 1024:
            reason = f"larger than {max_mb:g} MB (checksum recorded; raise --max-file-mb to include it)"
        if reason:
            skipped.append({"path": entry["path"], "sha256": entry.get("sha256"), "size_bytes": entry["size_bytes"], "reason": reason})
            continue
        root_label = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(entry["root"]).name or "root")
        relative = Path(entry["language_guess"]) / root_label / entry["relative_path"]
        while str(relative) in used:
            relative = relative.with_name(relative.stem + "_dup" + relative.suffix)
        used.add(str(relative))
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)                       # copy, never move
        digest = sha256(target)
        entry["packaged_as"] = str(relative)
        copied.append({"original": entry["path"], "packaged_as": str(relative), "sha256": digest,
                       "matches_original": digest == entry["sha256"], "size_bytes": entry["size_bytes"]})
        manifest.append(f"{digest}  {relative.as_posix()}")
    report["package"] = {
        "folder": str(dest), "files_copied": len(copied), "bytes_copied": sum(c["size_bytes"] for c in copied),
        "copies_verified": all(c["matches_original"] for c in copied), "files": copied, "not_packaged": skipped,
        "labels_are_guesses": True, "archive": str(dest) + ".tar.gz", "archive_sha256": None,
    }
    (dest / "SOURCE_INFO.md").write_text(SOURCE_INFO, encoding="utf-8")
    return manifest and {"manifest": manifest} or {"manifest": []}


def finish_package(report: dict, dest: Path, manifest: list[str]) -> None:
    archive = Path(str(dest) + ".tar.gz")
    package = report["package"]
    (dest / "inventory.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (dest / "INVENTORY.md").write_text(render_markdown(report), encoding="utf-8")
    for extra in ("inventory.json", "INVENTORY.md"):
        manifest.append(f"{sha256(dest / extra)}  {extra}")
    (dest / "MANIFEST.sha256").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(dest, arcname=dest.name)
    package["archive_sha256"] = sha256(archive)
    package["archive_size_bytes"] = archive.stat().st_size
    Path(str(archive) + ".sha256").write_text(f"{package['archive_sha256']}  {archive.name}\n", encoding="utf-8")


def verify_package(folder: Path) -> int:
    manifest = folder / "MANIFEST.sha256"
    if not manifest.exists():
        print(f"no MANIFEST.sha256 in {folder}", file=sys.stderr)
        return 2
    bad = total = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        total += 1
        target = folder / name
        if not target.is_file() or sha256(target) != digest:
            bad += 1
            print(f"MISMATCH  {name}")
    listed = {line.split("  ", 1)[1] for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()}
    extra = sorted(str(p.relative_to(folder).as_posix()) for p in folder.rglob("*") if p.is_file()
                   and p.relative_to(folder).as_posix() not in listed | {"MANIFEST.sha256", PACKAGE_MARKER, OWNER_NOTES})
    for name in extra:
        print(f"NOT IN MANIFEST  {name}")
    print(f"{total - bad} of {total} files match the manifest; {len(extra)} unlisted file(s)")
    print(f"({OWNER_NOTES} is your own notes file: it may be edited and is not checksummed.)")
    return 0 if not bad and not extra else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("roots", nargs="*", type=Path, help="project folders (or single files) to inventory")
    parser.add_argument("--search", action="append", default=[], type=Path, metavar="DIR",
                        help="broad folder: list only files whose path names the Constitution or NYAYMITRA (repeatable)")
    parser.add_argument("--all", action="store_true", help="in project folders, list every data file regardless of its name")
    parser.add_argument("--out", type=Path, help="write the JSON inventory here (default: print)")
    parser.add_argument("--markdown", type=Path, help="write the readable Markdown report here")
    parser.add_argument("--package", type=Path, metavar="NEW_DIR", help="also COPY the listed files into this new folder and make NEW_DIR.tar.gz")
    parser.add_argument("--max-file-mb", type=float, default=25, help="do not copy files larger than this into the package (0 = no limit; default 25)")
    parser.add_argument("--include-databases", action="store_true", help="copy SQLite databases into the package too")
    parser.add_argument("--include-archives", action="store_true", help="copy .zip/.gz files into the package too (their contents are not checked)")
    parser.add_argument("--verify-package", type=Path, metavar="DIR", help="check a package folder against MANIFEST.sha256 and exit")
    args = parser.parse_args(argv)
    if args.verify_package:
        return verify_package(args.verify_package)
    if not args.roots and not args.search:
        parser.error("give at least one project folder or --search folder")

    roots: list[tuple[Path, str]] = []
    for root in args.roots:
        roots.append((root, "search" if root.is_dir() and is_broad(root) else "project"))
    roots += [(root, "search") for root in args.search]
    missing = [str(r) for r, _ in roots if not r.exists()]
    present = [(r, m) for r, m in roots if r.exists()]
    if args.package:
        for root, _ in present:
            try:
                args.package.resolve().relative_to(root.resolve())
            except ValueError:
                continue
            if root.is_dir() and not is_broad(root):
                parser.error(f"--package {args.package} is inside the project folder {root}; choose a folder outside it (e.g. ~/nyaymitra-transfer)")

    counters: Counter = Counter()
    files = [inspect(path, root, mode) for path, root, mode in candidates(present, args.all, counters)]
    report = {
        "tool": "inventory_local_data.py", "tool_version": TOOL_VERSION,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "roots": [str(r) for r, _ in roots],
        "project_roots": [str(r) for r, m in roots if m == "project"],
        "search_roots": [str(r) for r, m in roots if m == "search"],
        "roots_not_found": missing,
        "not_listed": {"data_files_not_listed_no_matching_name": counters["data_files_not_listed_no_matching_name"],
                       "unreadable_folders": counters["unreadable_folders"]},
        "labels_are_guesses": True, "files_found": len(files), "files": files,
    }
    manifest: list[str] = []
    if args.package:
        manifest = build_package(report, args.package, args.max_file_mb, args.include_databases, args.include_archives)["manifest"]
    report["originals"] = unchanged(files, rehash=bool(args.package))
    if args.package:
        finish_package(report, args.package, manifest)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(render_markdown(report), encoding="utf-8")
    if not args.out and not args.markdown and not args.package:
        print(text)
    else:
        print(f"{len(files)} file(s) inventoried" + (f" -> {args.out}" if args.out else "")
              + (f" , {args.markdown}" if args.markdown else ""))
        by_language = Counter(f["language_guess"] for f in files)
        print("  " + ", ".join(f"{k}: {v}" for k, v in sorted(by_language.items())) if files else "  nothing matched")
        print(f"  originals unchanged: {'yes' if report['originals']['unchanged'] else 'NO'} ({report['originals']['method']})")
        if args.package:
            p = report["package"]
            print(f"  package: {p['folder']}  ({p['files_copied']} files copied, {len(p['not_packaged'])} listed but not copied)")
            print(f"  archive: {p['archive']}  ({_size(p['archive_size_bytes'])})")
            print(f"  archive sha256: {p['archive_sha256']}")
            for item in p["not_packaged"]:
                print(f"  NOT COPIED: {item['path']} ({_size(item['size_bytes'])}) — {item['reason']}")
            if not p["copies_verified"]:
                print("  ERROR: a copy differs from its original (did a file change during the run?). Do not send this package.", file=sys.stderr)
    copies_ok = not args.package or report["package"]["copies_verified"]
    return 0 if report["originals"]["unchanged"] and copies_ok else 1


if __name__ == "__main__":
    sys.exit(main())
