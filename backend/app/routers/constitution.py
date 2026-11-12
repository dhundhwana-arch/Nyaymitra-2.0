"""Constitution of India: search, article detail, parts, coverage."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Path, Query

from ..deps import db_dependency
from ..errors import AppError
from ..models import (
    ArticleDetail,
    CoverageResponse,
    Language,
    PartSummary,
    SearchResponse,
    VerificationStatus,
)
from ..services import constitution

router = APIRouter(prefix="/constitution", tags=["constitution"])


@router.get("/articles", response_model=SearchResponse)
def search_articles(
    q: str | None = Query(None, max_length=200, description="Search text (Gujarati or English)"),
    language: Language = Query("gu"),
    page: int = Query(1, ge=1, le=100),
    page_size: int = Query(20, ge=1, le=50),
    part: str | None = Query(None, max_length=8, description="Part number, e.g. III"),
    verification_status: VerificationStatus | None = Query(None),
    conn: sqlite3.Connection = Depends(db_dependency),
) -> dict:
    return constitution.search(
        conn,
        query=q,
        language=language,
        page=page,
        page_size=page_size,
        part_no=part,
        verification_status=verification_status,
    )


@router.get("/parts", response_model=list[PartSummary])
def list_parts(conn: sqlite3.Connection = Depends(db_dependency)) -> list[dict]:
    return constitution.parts(conn)


@router.get("/coverage", response_model=CoverageResponse)
def corpus_coverage(conn: sqlite3.Connection = Depends(db_dependency)) -> dict:
    return constitution.coverage(conn)


@router.get("/articles/{identifier}", response_model=ArticleDetail)
def article_detail(
    identifier: str = Path(..., min_length=1, max_length=32, pattern=r"^[A-Za-z0-9\-]+$"),
    conn: sqlite3.Connection = Depends(db_dependency),
) -> dict:
    article = constitution.get_article(conn, identifier)
    if article is None:
        raise AppError("not_found", "No article with that number is loaded in the corpus.").to_http()
    return article
