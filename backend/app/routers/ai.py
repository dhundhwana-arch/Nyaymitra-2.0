"""Grounded AI explanation and terminology endpoints."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query, Request

from .. import languages
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
    requested = payload.language
    detected = languages.detect(payload.question, hint=requested)
    # Answers exist in Gujarati and English. The selected language wins when it is one of
    # them; otherwise a question typed in Gujarati script is answered in Gujarati and
    # everything else in English — and the response says that a fallback happened.
    if requested in languages.CONTENT_LANGUAGES:
        answer_language = requested
    else:
        answer_language = "gu" if detected["language"] == "gu" else languages.DEFAULT_CONTENT_LANGUAGE
    result = answer_question(
        conn,
        settings,
        question=payload.question,
        language=answer_language,
        category=payload.category,
        request_id=request_id(request),
    )
    fallback = requested != answer_language
    result["requested_language"] = requested
    result["detected_language"] = detected
    result["language_fallback"] = fallback
    if fallback:
        result["language_notice"] = (
            f"Answers are not yet available in {languages.get(requested).english_name}. "
            f"This answer is in {languages.get(answer_language).english_name}. "
            "Nothing was machine-translated."
        )
        result["warnings"] = sorted(set(result["warnings"]) | {"answer_language_fallback"})
    return result


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
