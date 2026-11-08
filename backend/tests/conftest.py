"""Shared fixtures.

Each test session gets its own SQLite file, storage directory and backup directory in a
temp folder, so the developer's real database is never touched.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

ADMIN_TOKEN = "test-admin-token"
MONITOR_TOKEN = "test-monitor-token"


@pytest.fixture(scope="session", autouse=True)
def test_environment(tmp_path_factory: pytest.TempPathFactory) -> Path:
    base = tmp_path_factory.mktemp("nyaymitra-test")
    os.environ.update(
        {
            "NYAYMITRA_ENV": "test",
            "NYAYMITRA_DB_PATH": str(base / "test.db"),
            "NYAYMITRA_STORAGE_DIR": str(base / "documents"),
            "NYAYMITRA_BACKUP_DIR": str(base / "backups"),
            "NYAYMITRA_ADMIN_TOKEN": ADMIN_TOKEN,
            "NYAYMITRA_MONITOR_TOKEN": MONITOR_TOKEN,
            "NYAYMITRA_AI_PROVIDER": "auto",
            "NYAYMITRA_AI_API_KEY": "",
            "NYAYMITRA_AI_BASE_URL": "",
            "NYAYMITRA_AI_MODEL": "",
            "NYAYMITRA_RATE_LIMIT_READ": "1000",
            "NYAYMITRA_RATE_LIMIT_WRITE": "1000",
            "NYAYMITRA_RATE_LIMIT_AI": "1000",
            "NYAYMITRA_RATE_LIMIT_ADMIN": "1000",
            "NYAYMITRA_LOG_LEVEL": "WARNING",
        }
    )
    from backend.app.config import reset_settings_cache

    reset_settings_cache()
    yield base


@pytest.fixture()
def settings(test_environment):
    from backend.app.config import get_settings

    return get_settings()


@pytest.fixture()
def app(test_environment):
    from backend.app.main import create_app
    from backend.app.config import get_settings

    return create_app(get_settings())


@pytest.fixture()
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def admin_headers() -> dict:
    return {"X-Admin-Token": ADMIN_TOKEN}


@pytest.fixture()
def monitor_headers() -> dict:
    return {"X-Admin-Token": MONITOR_TOKEN}


@pytest.fixture()
def db(settings):
    from backend.app.db import get_db

    with get_db(settings.db_path) as conn:
        yield conn


def complaint_payload(*, unique: bool = True, **overrides) -> dict:
    """A valid complaint payload.

    Each call gets a unique marker by default, because the API treats an *identical*
    payload without an idempotency key as a retry of the same submission (409). Tests
    that want to exercise that behaviour pass ``unique=False``.
    """
    payload = {
        "language": "en",
        "category": "cyber_fraud",
        "title": "Unauthorised withdrawal from my bank account",
        "description": (
            "On 5 November 2026 an unknown person withdrew 25000 rupees from my savings account "
            "without any OTP being shared. I informed the bank the same day and they gave me a "
            "complaint number."
        ),
        "incident_date": "2026-11-05",
        "location": "Jamnagar",
        "district": "Jamnagar",
        "state": "Gujarat",
        "consent": True,
        "confirmed": True,
    }
    if unique:
        payload["description"] = payload["description"] + (
            f" Case note {os.urandom(4).hex()} recorded for this test run."
        )
        payload.setdefault("client_request_id", f"test-{os.urandom(8).hex()}")
    payload.update(overrides)
    return payload


@pytest.fixture()
def isolated_settings(test_environment, tmp_path):
    """A throw-away database file so ingestion tests never pollute the shared one."""
    from dataclasses import replace

    from backend.app.config import get_settings
    from backend.app.db import init_database
    from backend.app.services.seed import seed_all

    settings = replace(
        get_settings(),
        db_path=tmp_path / "ingest.db",
        storage_dir=tmp_path / "docs",
        backup_dir=tmp_path / "backups",
    )
    init_database(settings)
    seed_all(settings)
    return settings
