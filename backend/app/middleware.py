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
from .logging_utils import request_id_ctx
from .security import client_ip, rate_limiter

log = logging.getLogger("nyaymitra.http")


def _classify(path: str, method: str) -> tuple[str, int]:
    settings = get_settings()
    if "/ai/" in path:
        return "ai", settings.rate_limit_ai
    if method in {"GET", "HEAD", "OPTIONS"}:
        return "read", settings.rate_limit_read
    return "write", settings.rate_limit_write


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
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; "
                "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
            ),
        }
        if self.settings.environment == "production":
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        for key, value in headers.items():
            response.headers.setdefault(key, value)
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings | None = None) -> None:
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(self, request: Request, call_next) -> Response:
        limit = self.settings.max_body_bytes
        if request.url.path.endswith("/documents"):
            limit = self.settings.max_upload_bytes + 4096
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            rid = getattr(request.state, "request_id", "-")
            return JSONResponse(
                status_code=413,
                content=error_body("payload_too_large", f"Request body exceeds {limit} bytes.", rid),
            )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings | None = None) -> None:
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path in {"/health", "/api/v1/health"} or path.startswith("/assets/"):
            return await call_next(request)
        bucket, limit = _classify(path, request.method)
        ip = client_ip(request, self.settings)
        allowed, retry_after = rate_limiter.hit(
            f"{bucket}:{ip}", limit, self.settings.rate_limit_window_s
        )
        if not allowed:
            rid = getattr(request.state, "request_id", "-")
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


class ApiNotFoundMiddleware(BaseHTTPMiddleware):
    """Return the JSON error envelope for unknown /api paths (never HTML)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if response.status_code == 404 and request.url.path.startswith("/api/"):
            rid = getattr(request.state, "request_id", "-")
            return JSONResponse(status_code=404, content=error_body("not_found", None, rid))
        return response
