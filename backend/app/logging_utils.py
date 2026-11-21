"""Structured logging with PII redaction.

Never log a raw complaint, query, phone number, token or API key. ``redact`` is applied
to every log record and to the copies we keep in ``query_logs``/``error_log``.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

REDACTED = "[redacted]"

_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)(authorization|api[-_]?key|token|password|secret)\s*[:=]\s*\S+"), r"\1=" + REDACTED),
    (re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-]+"), r"\1 " + REDACTED),
    # Indian mobile numbers
    (re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)"), REDACTED),
    # e-mail addresses
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), REDACTED),
    # long digit strings: account / Aadhaar / card-like numbers
    (re.compile(r"(?<!\d)\d{9,18}(?!\d)"), REDACTED),
)

MAX_LOGGED_TEXT = 300


def redact(text: str | None) -> str | None:
    if text is None:
        return None
    out = str(text)
    for pattern, repl in _PATTERNS:
        out = pattern.sub(repl, out)
    return out


def redact_and_truncate(text: str | None, limit: int = MAX_LOGGED_TEXT) -> str | None:
    out = redact(text)
    if out is None:
        return None
    return out if len(out) <= limit else out[:limit] + "…"


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.msg = redact(record.getMessage())
        record.args = ()
        base = super().format(record)
        return f"[req={request_id_ctx.get()}] {base}"


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if getattr(root, "_nyaymitra_configured", False):
        root.setLevel(level.upper())
        return
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(
        RedactingFormatter("%(asctime)s %(levelname)s %(name)s %(message)s", "%Y-%m-%dT%H:%M:%S")
    )
    root.handlers = [handler]
    root.setLevel(level.upper())
    logging.getLogger("uvicorn.access").disabled = False
    root._nyaymitra_configured = True  # type: ignore[attr-defined]


def log_event(event: str, **fields: object) -> None:
    payload = {k: (redact(v) if isinstance(v, str) else v) for k, v in fields.items()}
    logging.getLogger("nyaymitra").info("%s %s", event, json.dumps(payload, ensure_ascii=False))
