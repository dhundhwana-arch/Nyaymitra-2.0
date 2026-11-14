"""Liveness, readiness and service metadata."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from .. import languages
from ..ai.registry import describe
from ..config import Settings, get_settings
from ..db import applied_migrations, get_db
from ..deps import db_dependency, settings_dependency
from ..models import Capabilities, HealthResponse, MetaResponse, ReadinessResponse
from ..services import constitution

router = APIRouter(tags=["service"])

DISCLAIMERS = [
    "NYAYMITRA is not an AI judge. It does not decide cases, declare anyone guilty or innocent, "
    "or guarantee an outcome.",
    "It helps you describe a problem, understand legal information, find the right department and "
    "prepare a complaint you submit yourself.",
    "Final legal decisions rest with authorised human professionals and institutions.",
    "Legal content in this build has NOT been fully verified by a qualified legal professional.",
]


@router.get("/health", response_model=HealthResponse)
def health() -> dict:
    settings = get_settings()
    return {"status": "ok", "version": settings.version, "checks": {"api": "ok"}}


@router.get("/ready", response_model=ReadinessResponse)
def ready(settings: Settings = Depends(settings_dependency)) -> dict:
    checks: dict[str, str] = {}
    ready_flag = True
    try:
        with get_db(settings.db_path) as conn:
            conn.execute("SELECT 1").fetchone()
            applied = applied_migrations(conn)
            checks["database"] = "ok"
            checks["migrations"] = "ok" if applied else "pending"
            if not applied:
                ready_flag = False
    except sqlite3.Error as exc:
        checks["database"] = f"error: {type(exc).__name__}"
        ready_flag = False

    try:
        settings.storage_dir.mkdir(parents=True, exist_ok=True)
        probe = settings.storage_dir / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        checks["storage"] = "ok"
    except OSError:
        checks["storage"] = "not_writable"
        ready_flag = False

    info = describe(settings)
    checks["ai_provider"] = "live" if info.live else "offline"
    return {"ready": ready_flag, "checks": checks}


@router.get("/meta", response_model=MetaResponse)
def meta(settings: Settings = Depends(settings_dependency), conn: sqlite3.Connection = Depends(db_dependency)) -> dict:
    info = describe(settings)
    coverage = constitution.coverage(conn)
    return {
        "app_name": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "api_prefix": settings.api_prefix,
        "capabilities": {
            "ai_provider": info.name,
            "ai_live": info.live,
            "ai_fallback_mode": info.fallback_mode,
            "languages": ["gu", "en"],
            "interface_languages": list(languages.CODES),
            "admin_enabled": settings.admin_enabled,
            "max_upload_bytes": settings.max_upload_bytes,
            "allowed_upload_types": list(settings.allowed_upload_types),
        },
        "corpus": {
            "articles": coverage["total_articles"],
            "verified_text": coverage["verified_text"],
            "owner_summaries": coverage["owner_summaries"],
            "requires_human_verification": coverage["requires_human_verification"],
            "expected_article_count": coverage["expected_article_count"],
        },
        "disclaimers": DISCLAIMERS,
    }
