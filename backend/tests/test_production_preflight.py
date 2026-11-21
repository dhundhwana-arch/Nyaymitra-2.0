"""Config preflight and monitoring edges — closes the coverage gaps the new reliability code left."""
from __future__ import annotations

import os

import pytest

from backend.app.config import Settings, REPO_ROOT


def _env(**kwargs):
    """Return a context manager that sets env vars; or a simple override via replace()."""
    return None


def _settings(*, environment="development", **overrides):
    from backend.app.config import load_settings, reset_settings_cache

    env = {"NYAYMITRA_ENV": environment,
           "NYAYMITRA_ADMIN_TOKEN": "alpha-admin-token-1234567890",
           "NYAYMITRA_MONITOR_TOKEN": "beta-monitor-token-1234567890"}
    env.update(overrides)
    previous = {key: os.environ.get(key) for key in env}
    for key, value in env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    try:
        reset_settings_cache()
        return load_settings()
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        reset_settings_cache()


def test_production_preflight_ok():
    s = _settings(environment="production",
                  NYAYMITRA_DB_PATH="/var/lib/nyaymitra/nyaymitra.db")
    assert s.production_problems() == [], s.production_problems()


def test_production_preflight_skipped_in_development():
    s = _settings(environment="development")
    assert s.production_problems() == []


def test_production_preflight_missing_tokens():
    s = _settings(environment="production", NYAYMITRA_ADMIN_TOKEN="",
                  NYAYMITRA_MONITOR_TOKEN="")
    problems = s.production_problems()
    assert any("not set" in p for p in problems)


def test_production_preflight_short_token():
    s = _settings(environment="production", NYAYMITRA_ADMIN_TOKEN="short")
    assert any("shorter than 24 characters" in p for p in s.production_problems())


def test_production_preflight_placeholder_token():
    s = _settings(environment="production", NYAYMITRA_ADMIN_TOKEN="replace-with-secret")
    assert any("placeholder" in p for p in s.production_problems())


def test_production_preflight_low_entropy_token():
    s = _settings(environment="production", NYAYMITRA_ADMIN_TOKEN="aaaaaaaaaaaaaaaaaaaaaaaa")
    assert any("too little variety" in p for p in s.production_problems())


def test_production_preflight_identical_tokens():
    s = _settings(environment="production",
                  NYAYMITRA_ADMIN_TOKEN="sharedtoken1234567890",
                  NYAYMITRA_MONITOR_TOKEN="sharedtoken1234567890")
    assert any("identical" in p for p in s.production_problems())


def test_production_preflight_db_inside_repo():
    s = _settings(environment="production", NYAYMITRA_DB_PATH=str(REPO_ROOT / "data" / "x.db"))
    assert any("inside the repository" in p for p in s.production_problems())


def test_production_preflight_proxy_without_origins():
    s = _settings(environment="production", NYAYMITRA_TRUST_PROXY_HEADERS="true",
                  NYAYMITRA_ALLOWED_ORIGINS="")
    assert any("X-Forwarded-For" in p for p in s.production_problems())


def test_production_preflight_multiple_problems_reported():
    s = _settings(environment="production", NYAYMITRA_ADMIN_TOKEN="x",
                  NYAYMITRA_MONITOR_TOKEN="x")
    problems = s.production_problems()
    assert len(problems) >= 2


# -------------------------------------------------------- monitoring usage edges
def test_usage_summary_handles_no_answers(isolated_settings):
    from backend.app.db import get_db
    from backend.app.services import monitoring
    with get_db(isolated_settings.db_path) as conn:
        summary = monitoring.usage_summary(conn, days=7)
    assert summary["totals"]["answers"] == 0
    assert summary["totals"]["prompt_tokens"] == 0
    assert summary["latency"]["answers"] == 0
    assert summary["providers"] == []


def test_usage_summary_days_validation(db):
    from backend.app.services import monitoring
    summary = monitoring.usage_summary(db, days=1)
    assert summary["days"] == 1
    summary = monitoring.usage_summary(db, days=365)
    assert summary["days"] == 365


def test_usage_summary_counts_grounded_and_degraded(isolated_settings):
    from backend.app.db import get_db
    from backend.app.services import monitoring
    with get_db(isolated_settings.db_path) as db:
        q = monitoring.log_query(db, request_id="r", language="en", query_text="q",
                                 category=None, provider="openai_compatible", latency_ms=5,
                                 status="ok", error_code=None)
        monitoring.log_answer(db, query_log_id=q, provider="openai_compatible", model="m",
                              grounded=True, degraded=False, citations=[], answer_text="a",
                              warnings=[], usage={"prompt_tokens": 1, "completion_tokens": 2})
        monitoring.log_answer(db, query_log_id=q, provider="openai_compatible", model="m",
                              grounded=False, degraded=True, citations=[], answer_text="a",
                              warnings=["unable to ground"], usage={})
        summary = monitoring.usage_summary(db, days=30)
    assert summary["totals"]["grounded"] == 1
    assert summary["totals"]["degraded"] == 1
    assert summary["totals"]["prompt_tokens"] == 1
    assert summary["providers"][0]["answers"] == 2


# -------------------------------------------------------- provider health edges
def test_provider_health_no_endpoint_details():
    from backend.app.services import provider_health
    s = _settings(environment="production", NYAYMITRA_AI_PROVIDER="openai_compatible",
                  NYAYMITRA_AI_BASE_URL="http://127.0.0.1:1/v1", NYAYMITRA_AI_API_KEY="k",
                  NYAYMITRA_AI_MODEL="m")
    payload = provider_health.health(s, probe=True)
    assert payload["live"] is True
    assert payload["status"] in {provider_health.STATUS_OK, provider_health.STATUS_UNREACHABLE}
    assert payload["endpoint"]["reachable"] is False
    assert "could not reach" in payload["endpoint"]["detail"]


def test_provider_health_probe_disabled_skips_endpoint():
    from backend.app.services import provider_health
    s = _settings(environment="production", NYAYMITRA_AI_PROVIDER="openai_compatible",
                  NYAYMITRA_AI_BASE_URL="http://127.0.0.1:9/v1", NYAYMITRA_AI_API_KEY="k",
                  NYAYMITRA_AI_MODEL="m")
    payload = provider_health.health(s, probe=False)
    assert payload["endpoint"] is None
    assert payload["detail"] == "configured; endpoint not probed"


def test_provider_health_not_live_probe_skipped():
    from backend.app.services import provider_health
    s = _settings(environment="production")  # offline provider
    payload = provider_health.health(s, probe=True)
    assert payload["live"] is False
    assert payload["endpoint"] is None
    assert payload["status"] == provider_health.STATUS_NOT_CONFIGURED
