"""Shared FastAPI dependencies."""
from __future__ import annotations

import sqlite3
from typing import Iterator

from fastapi import Depends, Request

from .config import Settings, get_settings
from .db import get_db
from .errors import AppError
from .security import resolve_role


def db_dependency() -> Iterator[sqlite3.Connection]:
    settings = get_settings()
    with get_db(settings.db_path) as conn:
        yield conn


def settings_dependency() -> Settings:
    return get_settings()


def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def require_role(minimum: str = "monitor"):
    """Dependency factory enforcing the admin/monitor roles.

    ``monitor`` may read everything and change nothing; ``admin`` may also mutate
    verification state and trigger backups.
    """

    def _dep(request: Request, settings: Settings = Depends(settings_dependency)) -> str:
        if not settings.admin_enabled and not settings.monitor_token:
            raise AppError("forbidden", "Administration is not enabled on this server.").to_http()
        role = resolve_role(request, settings)
        if role is None:
            raise AppError("unauthorized", "A valid admin token is required.").to_http()
        if minimum == "admin" and role != "admin":
            raise AppError("forbidden", "This action requires the admin role.").to_http()
        return role

    return _dep
