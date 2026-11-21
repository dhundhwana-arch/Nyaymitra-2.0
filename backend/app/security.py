"""Security primitives: tokens, rate limiting, upload validation, client identity."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import threading
import time
import unicodedata
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from fastapi import Request

from .config import Settings

# --------------------------------------------------------------------- tokens
TOKEN_BYTES = 24
ADMIN_HEADER = "X-Admin-Token"


def new_token() -> str:
    """A URL-safe, high-entropy user token. Shown once; only its hash is stored."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_equals(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def resolve_role(request: Request, settings: Settings) -> str | None:
    """Return 'admin' / 'monitor' / None from the admin header.

    The two roles exist so that monitoring can be delegated without granting the
    ability to change legal-source verification state.
    """
    supplied = request.headers.get(ADMIN_HEADER) or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not supplied:
        return None
    if constant_time_equals(supplied, settings.admin_token):
        return "admin"
    if constant_time_equals(supplied, settings.monitor_token):
        return "monitor"
    return None


def hash_ip(ip: str | None) -> str:
    if not ip:
        return "unknown"
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()[:16]


def client_ip(request: Request, settings: Settings) -> str:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# --------------------------------------------------------------- rate limits
class RateLimiter:
    """Fixed-window counter held in memory.

    Deliberately simple and dependency-free: the deployment target is a single
    process on a modest machine. Swap for Redis if the app is ever scaled out
    (documented in docs/SECURITY_AUDIT.md).
    """

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_s: int) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits.setdefault(key, deque())
            cutoff = now - window_s
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(1, int(window_s - (now - bucket[0])))
                return False, retry_after
            bucket.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


rate_limiter = RateLimiter()


# ----------------------------------------------------------- upload handling
MAGIC_SIGNATURES: tuple[tuple[str, tuple[bytes, ...]], ...] = (
    ("application/pdf", (b"%PDF-",)),
    ("image/jpeg", (b"\xff\xd8\xff",)),
    ("image/png", (b"\x89PNG\r\n\x1a\n",)),
    ("image/webp", (b"RIFF",)),
)

SAFE_EXTENSIONS = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_original_name(name: str | None) -> str:
    """Keep the display name only; never use it to build a path."""
    if not name:
        return "unnamed"
    base = Path(name.replace("\\", "/")).name
    base = unicodedata.normalize("NFKC", base)
    base = CONTROL_CHARS.sub("", base).strip()
    base = base.lstrip(".") or "unnamed"
    return base[:120]


def sniff_mime(head: bytes) -> str | None:
    for mime, signatures in MAGIC_SIGNATURES:
        if any(head.startswith(sig) for sig in signatures):
            if mime == "image/webp" and head[8:12] != b"WEBP":
                continue
            return mime
    return None


@dataclass
class UploadCheck:
    ok: bool
    code: str | None = None
    message: str | None = None
    mime: str | None = None


def validate_upload(
    *,
    original_name: str | None,
    declared_mime: str | None,
    size: int,
    head: bytes,
    settings: Settings,
) -> UploadCheck:
    if size <= 0:
        return UploadCheck(False, "bad_request", "The file is empty.")
    if size > settings.max_upload_bytes:
        return UploadCheck(
            False,
            "payload_too_large",
            f"The file is larger than {settings.max_upload_bytes // (1024 * 1024)} MB.",
        )
    declared = (declared_mime or "").split(";")[0].strip().lower()
    if declared and declared not in settings.allowed_upload_types:
        return UploadCheck(False, "unsupported_media_type")
    sniffed = sniff_mime(head)
    if sniffed is None:
        return UploadCheck(False, "unsupported_media_type")
    if declared and sniffed != declared:
        # Browser MIME can be wrong; content wins, but conflict is suspicious.
        return UploadCheck(
            False,
            "unsupported_media_type",
            "The file content does not match its declared type.",
        )
    return UploadCheck(True, mime=sniffed)


def storage_name_for(mime: str) -> str:
    return f"{secrets.token_hex(16)}{SAFE_EXTENSIONS.get(mime, '.bin')}"
