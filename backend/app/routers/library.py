"""Legal Library: listing, filters, keyword search and item detail over existing data."""
from __future__ import annotations

import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, Path, Query

from ..deps import db_dependency
from ..errors import AppError
from ..models import Language
from ..services import library

router = APIRouter(prefix="/library", tags=["library"])

Category = Literal["constitution", "guide", "department", "glossary"]


@router.get("")
def list_library(
    q: str | None = Query(None, max_length=200, description="Keyword (Gujarati or English)"),
    language: Language = Query("gu", description="Display language"),
    category: Category | None = Query(None),
    content_language: Language | None = Query(None, description="Only items with content in this language"),
    page: int = Query(1, ge=1, le=100),
    page_size: int = Query(20, ge=1, le=50),
    conn: sqlite3.Connection = Depends(db_dependency),
) -> dict:
    return library.search(conn, query=q, language=language, category=category,
                          content_language=content_language, page=page, page_size=page_size)


@router.get("/{category}/{key}")
def library_item(
    category: Category,
    key: str = Path(..., min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$"),
    conn: sqlite3.Connection = Depends(db_dependency),
) -> dict:
    item = library.get_item(conn, category, key)
    if item is None:
        raise AppError("not_found")
    return item
