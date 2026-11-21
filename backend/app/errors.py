"""Error model: one safe envelope for every failure.

The client always receives ``{error: {code, message, request_id, details?}}`` — never a
traceback, never an internal path, never a provider secret.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException

ERROR_STATUS = {
    "bad_request": 400,
    "validation_failed": 422,
    "not_found": 404,
    "unauthorized": 401,
    "forbidden": 403,
    "rate_limited": 429,
    "payload_too_large": 413,
    "unsupported_media_type": 415,
    "provider_unavailable": 503,
    "ai_disabled": 503,
    "conflict": 409,
    "internal_error": 500,
}

PUBLIC_MESSAGES = {
    "bad_request": "The request could not be understood.",
    "validation_failed": "Some fields are missing or invalid. Please check the highlighted fields.",
    "not_found": "The requested item was not found.",
    "unauthorized": "An access token is required for this action.",
    "forbidden": "You do not have permission to perform this action.",
    "rate_limited": "Too many requests. Please wait and try again.",
    "payload_too_large": "The upload is larger than the permitted size.",
    "unsupported_media_type": "That file type is not accepted. Allowed types: PDF, JPEG, PNG, WEBP.",
    "provider_unavailable": "The AI service is not available right now, so no answer was generated.",
    "ai_disabled": "AI assistance is not configured on this server.",
    "conflict": "The request conflicts with the current state.",
    "internal_error": "Something went wrong on our side. Your data was not lost.",
}


class AppError(Exception):
    """Domain error carrying a stable machine-readable code."""

    def __init__(
        self,
        code: str,
        message: str | None = None,
        *,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code or ERROR_STATUS.get(code, 400)
        self.message = message or PUBLIC_MESSAGES.get(code, "Request failed.")
        self.details = details or {}
        super().__init__(self.message)

    def to_http(self) -> HTTPException:
        return HTTPException(
            status_code=self.status_code,
            detail={"code": self.code, "message": self.message, "details": self.details},
        )


def error_body(code: str, message: str | None, request_id: str, details: dict | None = None) -> dict:
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message or PUBLIC_MESSAGES.get(code, "Request failed."),
            "request_id": request_id,
        }
    }
    if details:
        body["error"]["details"] = details
    return body
