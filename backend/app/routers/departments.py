"""Department / official complaint-channel directory."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from ..deps import db_dependency
from ..models import DepartmentListResponse
from ..services import departments

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=DepartmentListResponse)
def list_departments(
    jurisdiction: str | None = Query(None, max_length=32),
    limit: int = Query(50, ge=1, le=100),
    conn: sqlite3.Connection = Depends(db_dependency),
) -> dict:
    items = departments.list_departments(conn, jurisdiction=jurisdiction, limit=limit)
    return {"items": items, "count": len(items), "notice": departments.NOTICE}
