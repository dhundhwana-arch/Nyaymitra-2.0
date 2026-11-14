"""ASGI middleware: request id, security headers, body-size limit, rate limiting.

Order matters (outermost first when added last in Starlette):
rate limit → body limit → security headers → request id.
"""
from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .config import Settings, get_settings
from .errors import error_body
from .metrics import metrics
from .logging_utils import request_id_ctx
from .security import client_ip, rate_limiter

log = logging.getLogger("nyaymitra.http")


def _classify(path: str, method: str, settings: Settings) -> tuple[str, int]:
    """Pick a rate-limit bucket. Admin paths get their own, much smaller bucket so a
    stolen or guessed token cannot be brute-forced at the public read rate."""
    if "/admin/" in path:
        return "admin", settings.rate_limit_admin
    if "/ai/" in path:
        return "ai", settings.rate_limit_ai
    if method in {"GET", "HEAD", "OPTIONS"}:
        return "read", settings.rate_limit_read
    return "write", settings.rate_limit_write


SENSITIVE_PREFIXES = ("/api/v1/complaints", "/api/v1/documents", "/api/v1/admin", "/admin")


def _is_sensitive(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in SENSITIVE_PREFIXES)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        token = request_id_ctx.set(request_id)
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-ms"] = str(int((time.perf_counter() - started) * 1000))
        metrics.inc("http.requests_total")
        metrics.inc(f"http.status_{response.status_code // 100}xx")
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings | None = None) -> None:
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
            "Permissions-Policy": "geolocation=(), microphone=(self), camera=()",
            "Cross-Origin-Opener-Policy": "same-origin",
            # No external script/style/font/CDN: the app is fully self-hosted.
            "Content-Security-Policy": (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; "
                "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
            ),
        }
        if _is_sensitive(request.url.path):
            # Complaint text, document bytes and admin data must never sit in a shared
            # cache or be restored from the back/forward cache on a shared kiosk.
            headers["Cache-Control"] = "no-store"
            headers["Pragma"] = "no-cache"
        if self.settings.environment == "production":
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        for key, value in headers.items():
            response.headers.setdefault(key, value)
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject oversized bodies before they are buffered in memory.

    ``Content-Length`` is checked for every request. A body sent with
    ``Transfer-Encoding: chunked`` has no length we can trust, so mutating requests
    without a declared length are refused rather than streamed into memory — browsers
    and normal clients always send a length. Document uploads get the larger limit.
    """

    def __init__(self, app, settings: Settings | None = None) -> None:
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(self, request: Request, call_next) -> Response:
        limit = self.settings.max_body_bytes
        if request.url.path.endswith("/documents"):
            limit = self.settings.max_upload_bytes + 4096
        rid = getattr(request.state, "request_id", "-")
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            return JSONResponse(
                status_code=413,
                content=error_body("payload_too_large", f"Request body exceeds {limit} bytes.", rid),
            )
        chunked = "chunked" in request.headers.get("transfer-encoding", "").lower()
        if chunked and request.method not in {"GET", "HEAD", "OPTIONS"}:
            return JSONResponse(
                status_code=411,
                content=error_body(
                    "length_required",
                    "Send a Content-Length header: streaming bodies cannot be size-checked.",
                    rid,
                ),
            )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings | None = None) -> None:
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path in {"/health", "/api/v1/health"} or path.startswith(("/assets/", "/locales/")):
            return await call_next(request)
        bucket, limit = _classify(path, request.method, self.settings)
        ip = client_ip(request, self.settings)
        allowed, retry_after = rate_limiter.hit(
            f"{bucket}:{ip}", limit, self.settings.rate_limit_window_s
        )
        if not allowed:
            rid = getattr(request.state, "request_id", "-")
            metrics.inc("http.rate_limited_total")
            log.warning("rate limit hit bucket=%s path=%s", bucket, path)
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content=error_body(
                    "rate_limited",
                    f"Too many requests. Try again in {retry_after}s.",
                    rid,
                ),
            )
        return await call_next(request)


class LanguageFallbackMiddleware(BaseHTTPMiddleware):
    """Accept any registry language on ``?language=`` and say honestly what was served.

    Seed content exists in Gujarati and English only. A request for another registered
    language is served in the fallback content language and labelled with response headers,
    instead of being rejected (422) or silently answered in the wrong language. Unknown codes
    are still rejected by the endpoint's own validation.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        from urllib.parse import urlencode

        from . import languages

        requested = request.query_params.get("language")
        served = None
        if (request.method == "GET" and requested and languages.is_known(requested)
                and requested not in languages.CONTENT_LANGUAGES):
            served = languages.content_language(requested)
            pairs = [(k, served if k == "language" else v) for k, v in request.query_params.multi_items()]
            pairs.append(("requested_language", requested))
            request.scope["query_string"] = urlencode(pairs).encode("utf-8")
        response = await call_next(request)
        if served:
            response.headers["Content-Language"] = served
            response.headers["X-Requested-Language"] = requested
            response.headers["X-Language-Fallback"] = "true"
        return response


class ApiNotFoundMiddleware(BaseHTTPMiddleware):
    """Return the JSON error envelope for unknown /api paths (never HTML)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if response.status_code == 404 and request.url.path.startswith("/api/"):
            rid = getattr(request.state, "request_id", "-")
            return JSONResponse(status_code=404, content=error_body("not_found", None, rid))
        return response
