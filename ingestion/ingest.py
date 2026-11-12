"""Gated import of extracted official text into SQLite.

* Dry-run is the default and opens the database read-only.
* ``apply`` refuses to run unless every quality gate passed.
* Rows go to a NEW table (``official_constitution_articles``); the existing
  ``constitution_articles`` seed/summary table is never read-modified or written.
* Every row is stored with verification_status = 'requires_human_verification'.
  This module contains no code path that sets any other status.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from . import VERIFICATION_STATUS
from .extract import Article

TABLE = "official_constitution_articles"
SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    language TEXT NOT NULL CHECK (language IN ('en','gu')),
    article_label_raw TEXT NOT NULL,
    article_base_no INTEGER NOT NULL,
    occurrence INTEGER NOT NULL DEFAULT 1,
    title_raw TEXT NOT NULL,
    text_raw TEXT NOT NULL,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    verification_status TEXT NOT NULL DEFAULT '{VERIFICATION_STATUS}',
    verified_by TEXT,
    verified_at TEXT,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source_sha256, article_label_raw, occurrence)
)"""


class GateError(Exception):
    pass


def plan(db_path: Path, batches: dict) -> dict:
    """Dry-run: count what an apply would do. Does not write. ``batches`` = {source_id: (sha256, [Article])}."""
    existing: set[tuple] = set()
    seed_rows = None
    if Path(db_path).exists():
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if TABLE in tables:
                existing = set(conn.execute(f"SELECT source_sha256, article_label_raw, occurrence FROM {TABLE}"))
            if "constitution_articles" in tables:
                seed_rows = conn.execute("SELECT count(*) FROM constitution_articles").fetchone()[0]
        finally:
            conn.close()
    out = {"mode": "dry-run", "table": TABLE, "rows_written": 0,
           "existing_seed_rows_untouched": seed_rows, "sources": {}}
    for sid, (sha, arts) in batches.items():
        new = sum((sha, a.label_raw, a.occurrence) not in existing for a in arts)
        out["sources"][sid] = {"would_insert": new, "already_present": len(arts) - new,
                               "verification_status": VERIFICATION_STATUS}
    return out


def apply(db_path: Path, batches: dict, gates: dict) -> dict:
    failed = [name for name, g in gates.items() if not g["passed"]]
    if failed:
        raise GateError("import refused; failing quality gates: " + ", ".join(failed))
    conn = sqlite3.connect(db_path)
    out = {"mode": "apply", "table": TABLE, "sources": {}}
    try:
        with conn:  # single transaction
            conn.execute(SCHEMA)
            for sid, (sha, arts) in batches.items():
                before = conn.total_changes
                conn.executemany(
                    f"INSERT OR IGNORE INTO {TABLE} (source_id, source_sha256, language, article_label_raw,"
                    " article_base_no, occurrence, title_raw, text_raw, page_start, page_end, verification_status)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    [(sid, sha, a.language, a.label_raw, a.base_no, a.occurrence, a.title_raw, a.text_raw,
                      a.page_start, a.page_end, VERIFICATION_STATUS) for a in arts])
                out["sources"][sid] = {"inserted": conn.total_changes - before,
                                       "verification_status": VERIFICATION_STATUS}
    finally:
        conn.close()
    return out
