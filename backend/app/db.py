"""SQLite access, schema migrations and backups.

Design notes
------------
* One connection per request/operation, WAL journal, foreign keys ON.
* Migrations are plain ``NNN_name.sql`` files applied in lexical order and recorded in
  ``schema_migrations`` with a checksum. A ``NNN_name.down.sql`` sibling enables rollback.
* Every statement uses parameters; nothing is interpolated into SQL except identifiers
  that come from the migration directory itself.
"""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

from .config import Settings, get_settings

MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    name        TEXT PRIMARY KEY,
    checksum    TEXT NOT NULL,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


class MigrationError(RuntimeError):
    pass


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    settings = get_settings()
    path = Path(db_path) if db_path is not None else settings.db_path
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(path), timeout=15.0, isolation_level=None, check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    if str(path) != ":memory:":
        try:
            conn.execute("PRAGMA journal_mode = WAL")
        except sqlite3.DatabaseError:  # pragma: no cover - exotic filesystems
            pass
    return conn


@contextmanager
def get_db(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    conn.execute("BEGIN")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def _migration_files(migrations_dir: Path) -> list[Path]:
    return sorted(
        p for p in migrations_dir.glob("*.sql") if not p.name.endswith(".down.sql")
    )


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def applied_migrations(conn: sqlite3.Connection) -> list[str]:
    conn.execute(MIGRATIONS_TABLE)
    return [r["name"] for r in conn.execute("SELECT name FROM schema_migrations ORDER BY name")]


def pending_migrations(conn: sqlite3.Connection, migrations_dir: Path) -> list[Path]:
    done = set(applied_migrations(conn))
    return [p for p in _migration_files(migrations_dir) if p.name not in done]


def apply_migrations(conn: sqlite3.Connection, migrations_dir: Path | None = None) -> list[str]:
    """Apply all pending migrations. Returns the names applied."""
    settings = get_settings()
    directory = Path(migrations_dir or settings.migrations_dir)
    conn.execute(MIGRATIONS_TABLE)
    done = set(applied_migrations(conn))
    applied: list[str] = []
    for path in _migration_files(directory):
        if path.name in done:
            continue
        sql = path.read_text(encoding="utf-8")
        try:
            conn.executescript(sql)
        except sqlite3.Error as exc:  # pragma: no cover - surfaces as 500 / startup error
            raise MigrationError(f"migration {path.name} failed: {exc}") from exc
        conn.execute(
            "INSERT INTO schema_migrations(name, checksum, applied_at) VALUES (?,?,?)",
            (path.name, _checksum(path), utcnow()),
        )
        applied.append(path.name)
    return applied


def rollback_migrations(
    conn: sqlite3.Connection,
    migrations_dir: Path | None = None,
    target: int = 0,
) -> list[str]:
    """Roll back migrations until ``target`` remain applied."""
    settings = get_settings()
    directory = Path(migrations_dir or settings.migrations_dir)
    rolled: list[str] = []
    names = applied_migrations(conn)
    while len(names) > target:
        name = names[-1]
        down = directory / name.replace(".sql", ".down.sql")
        if not down.exists():
            raise MigrationError(f"no down migration for {name}; refusing to guess")
        conn.executescript(down.read_text(encoding="utf-8"))
        conn.execute("DELETE FROM schema_migrations WHERE name = ?", (name,))
        rolled.append(name)
        names = applied_migrations(conn)
    return rolled


def init_database(settings: Settings | None = None) -> list[str]:
    """Create/upgrade the database. Idempotent; safe to call on every startup."""
    settings = settings or get_settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    with get_db(settings.db_path) as conn:
        return apply_migrations(conn, settings.migrations_dir)


def backup_database(
    dest_dir: Path | None = None,
    db_path: Path | None = None,
    verify: bool = True,
) -> Path:
    """Consistent online backup using sqlite3's backup API."""
    settings = get_settings()
    source = Path(db_path or settings.db_path)
    if not source.exists():
        raise FileNotFoundError(source)
    target_dir = Path(dest_dir or settings.backup_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = target_dir / f"nyaymitra-{stamp}.db"
    with sqlite3.connect(str(source)) as src, sqlite3.connect(str(target)) as dst:
        src.backup(dst)
    if verify:
        with sqlite3.connect(str(target)) as check:
            result = check.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise MigrationError(f"backup verification failed: {result}")
    return target


def restore_database(backup_file: Path, db_path: Path | None = None) -> Path:
    """Restore a backup *after* taking a safety copy of the current database."""
    settings = get_settings()
    target = Path(db_path or settings.db_path)
    if target.exists():
        safety = backup_database(settings.backup_dir, target, verify=True)
        print(f"[restore] current database saved to {safety}")
    target.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("-wal", "-shm"):
        side = Path(str(target) + suffix)
        if side.exists():
            side.unlink()
    shutil.copy2(backup_file, target)
    return target


def table_counts(conn: sqlite3.Connection, tables: Iterable[str] | None = None) -> dict[str, int]:
    if tables is None:
        tables = [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
    counts: dict[str, int] = {}
    for table in tables:
        try:
            counts[table] = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        except sqlite3.Error:
            counts[table] = -1
    return counts
