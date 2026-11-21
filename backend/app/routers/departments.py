"""Department / official complaint-channel directory."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Path, Query

from ..deps import db_dependency
from ..errors import AppError
from ..models import DepartmentListResponse, DepartmentOut
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


@router.get("/{department_key}", response_model=DepartmentOut)
def get_department(
    department_key: str = Path(..., min_length=2, max_length=64, pattern=r"^[a-z0-9\-]+$"),
    conn: sqlite3.Connection = Depends(db_dependency),
) -> dict:
    item = departments.get_department(conn, department_key)
    if item is None:
        raise AppError("not_found", "No such department.").to_http()
    return item
