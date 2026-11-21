"""Language registry and honest per-language availability."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from .. import languages
from ..config import Settings
from ..deps import db_dependency, settings_dependency
from ..errors import AppError
from ..models import StrictModel
from typing import Annotated
from pydantic import StringConstraints

router = APIRouter(prefix="/languages", tags=["languages"])

STATUS_LEGEND = {
    "UI_READY": "All essential interface labels exist in this language (see ui.translation_status for who wrote them).",
    "UI_PARTIAL": "Some essential interface labels exist; the rest are shown in English.",
    "SAMPLE_CONTENT_AVAILABLE": "Owner-written explanations exist in this language. They are not the text of the law.",
    "OFFICIAL_TEXT_AVAILABLE": "At least one article has text imported from a registered official source.",
    "HUMAN_VERIFIED": "At least one article text in this language has been verified by a person.",
    "ASSISTANT_SUPPORTED": "The assistant answers in this language. For other languages it detects the script and answers in the fallback language, saying so.",
}


@router.get("")
def list_languages(
    conn: sqlite3.Connection = Depends(db_dependency),
    settings: Settings = Depends(settings_dependency),
) -> dict:
    items = languages.describe(conn, settings.web_dir / "locales")
    return {
        "default_language": "gu",
        "content_languages": list(languages.CONTENT_LANGUAGES),
        "fallback_language": languages.DEFAULT_CONTENT_LANGUAGE,
        "essential_ui_keys": list(languages.ESSENTIAL_UI_KEYS),
        "status_legend": STATUS_LEGEND,
        "total": len(items),
        "items": items,
        "notice": (
            "Interface translation, machine translation, official text and verified text are "
            "separate states. No Constitution text has been machine-translated."
        ),
    }


class DetectRequest(StrictModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)]
    hint: Annotated[str, StringConstraints(pattern=r"^[a-z]{2,3}$")] | None = None


@router.post("/detect")
def detect_language(payload: DetectRequest) -> dict:
    return languages.detect(payload.text, payload.hint)


@router.get("/{code}")
def one_language(
    code: str,
    conn: sqlite3.Connection = Depends(db_dependency),
    settings: Settings = Depends(settings_dependency),
) -> dict:
    for item in languages.describe(conn, settings.web_dir / "locales"):
        if item["code"] == code:
            return item
    raise AppError("not_found", "Unknown language code.").to_http()
