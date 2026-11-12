"""Official source definitions and source-manifest handling."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
REPORT_DIR = ROOT / "data" / "reports"
MANIFEST_PATH = ROOT / "data" / "sources" / "manifest.json"
EXCEPTIONS_PATH = ROOT / "data" / "sources" / "accepted_exceptions.json"
DB_PATH = ROOT / "backend" / "justice_access.db"

# "claimed_*" values were supplied by the project owner and are NOT verified by
# this pipeline until the PDF itself has been downloaded and inspected by a human.
SOURCES = {
    "constitution-en": {
        "language": "en",
        "publisher": "Legislative Department, Ministry of Law and Justice, Government of India",
        "url": "https://www.legislative.gov.in/static/uploads/2025/08/b9a933fb88c0a5afba254256bc55a3f0.pdf",
        "local_path": "data/raw/constitution-of-india-en.pdf",
        "claimed_edition": "As on 10 September 2026",
        "claimed_amendments_incorporated": "Up to the Constitution (One Hundred and Sixth Amendment) Act, 2023",
    },
    "constitution-gu": {
        "language": "gu",
        "publisher": "Legislative Department, Ministry of Law and Justice, Government of India",
        "url": "https://www.legislative.gov.in/static/uploads/2025/07/316140f5938919bbbce4c22f1bf3d5ff.pdf",
        "local_path": "data/raw/samvidhan-gu.pdf",
        "claimed_edition": "Fifth edition, February 2026",
        "claimed_amendments_incorporated": "Up to the Constitution (One Hundred and Sixth Amendment) Act, 2023",
    },
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_manifest(path: Path = MANIFEST_PATH) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"schema_version": 1, "sources": {}}


def save_manifest(manifest: dict, path: Path = MANIFEST_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
