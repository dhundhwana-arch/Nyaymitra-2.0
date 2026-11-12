"""Grounded AI explanation and terminology endpoints."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query, Request

from ..ai.rag import answer_question
from ..config import Settings
from ..deps import db_dependency, request_id, settings_dependency
from ..models import ExplainRequest, ExplainResponse, TerminologyRequest, TerminologyResponse
from ..services import glossary

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/explain", response_model=ExplainResponse)
def explain(
    payload: ExplainRequest,
    request: Request,
    conn: sqlite3.Connection = Depends(db_dependency),
    settings: Settings = Depends(settings_dependency),
) -> dict:
    return answer_question(
        conn,
        settings,
        question=payload.question,
        language=payload.language,
        category=payload.category,
        request_id=request_id(request),
    )


@router.post("/terminology", response_model=TerminologyResponse)
def terminology(payload: TerminologyRequest) -> dict:
    return glossary.as_response(payload.term)


@router.get("/glossary", response_model=list[dict])
def glossary_list(
    language: str = Query("gu", pattern="^(gu|en)$"),
) -> list[dict]:
    key = "term_en" if language == "en" else "term_gu"
    explanation = "explanation_en" if language == "en" else "explanation_gu"
    return [
        {"key": t["key"], "term": t[key], "explanation": t[explanation]}
        for t in glossary.all_terms()
    ]
