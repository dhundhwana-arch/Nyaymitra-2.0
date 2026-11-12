"""NYAYMITRA 2.0 — FastAPI application factory.

Run locally:
    uvicorn backend.app.main:app --reload
or
    python -m backend.app.main
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api import api_router
from .config import Settings, get_settings
from .db import get_db, init_database
from .errors import AppError, error_body
from .logging_utils import configure_logging, log_event
from .middleware import (
    ApiNotFoundMiddleware,
    BodySizeLimitMiddleware,
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from .services import monitoring
from .services.seed import seed_all

log = logging.getLogger("nyaymitra")


def _auto_seed() -> bool:
    return os.environ.get("NYAYMITRA_AUTO_SEED", "true").strip().lower() in {"1", "true", "yes", "on"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    configure_logging(settings.log_level)
    applied = init_database(settings)
    if applied:
        log_event("db.migrations_applied", migrations=applied)
    if _auto_seed():
        counts = seed_all(settings)
        log_event("db.seeded", **counts)
    log_event("app.started", version=settings.version, environment=settings.environment,
              ai_provider=settings.ai_provider)
    yield
    log_event("app.stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    problems = settings.production_problems()
    if problems:
        raise RuntimeError(
            "refusing to start with an unsafe production configuration: "
            + "; ".join(problems)
        )

    app = FastAPI(
        title="NYAYMITRA 2.0 API",
        version=settings.version,
        description=(
            "Inclusive justice-access and navigation API. Provides legal *information* with "
            "source references, complaint intake, document handling and department navigation. "
            "It does not give legal decisions."
        ),
        lifespan=lifespan,
        # Swagger UI loads its JS/CSS from a CDN, which the CSP blocks and which cannot
        # work on an offline rural connection. The machine-readable schema is still
        # served at /api/openapi.json; docs/API_DOCUMENTATION.md is the human reference.
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.settings = settings

    # Middleware (added last = outermost)
    app.add_middleware(ApiNotFoundMiddleware)
    app.add_middleware(RateLimitMiddleware, settings=settings)
    app.add_middleware(BodySizeLimitMiddleware, settings=settings)
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    app.add_middleware(RequestContextMiddleware)

    app.include_router(api_router, prefix=settings.api_prefix)
    app.include_router(api_router, prefix="/api", include_in_schema=False)

    _mount_web(app, settings)
    _install_error_handlers(app, settings)
    return app


def _mount_web(app: FastAPI, settings: Settings) -> None:
    web_dir: Path = settings.web_dir
    if settings.serve_web and web_dir.exists():
        assets = web_dir / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        index = web_dir / "index.html"

        @app.get("/", include_in_schema=False)
        def root() -> FileResponse:
            return FileResponse(index, media_type="text/html")

        @app.get("/app.js", include_in_schema=False)
        def app_js() -> FileResponse:
            return FileResponse(web_dir / "app.js", media_type="application/javascript")

        @app.get("/styles.css", include_in_schema=False)
        def styles() -> FileResponse:
            return FileResponse(web_dir / "styles.css", media_type="text/css")

        @app.get("/admin.js", include_in_schema=False)
        def admin_js() -> FileResponse:
            return FileResponse(web_dir / "admin.js", media_type="application/javascript")

        @app.get("/manifest.webmanifest", include_in_schema=False)
        def manifest() -> FileResponse:
            return FileResponse(web_dir / "manifest.webmanifest", media_type="application/manifest+json")

        @app.get("/favicon.svg", include_in_schema=False)
        def favicon() -> FileResponse:
            return FileResponse(web_dir / "favicon.svg", media_type="image/svg+xml")

        @app.get("/admin", include_in_schema=False)
        def admin_page() -> FileResponse:
            return FileResponse(web_dir / "admin.html", media_type="text/html")


def _install_error_handlers(app: FastAPI, settings: Settings) -> None:
    def _record(method: str, path: str, code: int, error_type: str, message: str | None) -> None:
        try:
            with get_db(settings.db_path) as conn:
                monitoring.log_error(
                    conn,
                    request_id="-",
                    method=method,
                    path=path,
                    status_code=code,
                    error_type=error_type,
                    message=message,
                )
        except Exception:  # pragma: no cover - logging must never break a response
            log.warning("could not persist error record")

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:  # noqa: D401
        rid = getattr(request.state, "request_id", "-")
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, rid, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        rid = getattr(request.state, "request_id", "-")
        details = {
            "fields": [
                {
                    "field": ".".join(str(p) for p in err["loc"][1:]) or "body",
                    "message": err["msg"],
                }
                for err in exc.errors()[:10]
            ]
        }
        return JSONResponse(
            status_code=422,
            content=error_body(
                "validation_failed",
                "Some fields are missing or invalid. Please check the highlighted fields.",
                rid,
                details,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        rid = getattr(request.state, "request_id", "-")
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail:
            return JSONResponse(
                status_code=exc.status_code,
                content=error_body(detail.get("code"), detail.get("message"), rid, detail.get("details")),
                headers=getattr(exc, "headers", None),
            )
        code = {400: "bad_request", 401: "unauthorized", 403: "forbidden",
                404: "not_found", 405: "bad_request", 413: "payload_too_large",
                415: "unsupported_media_type", 429: "rate_limited"}.get(exc.status_code, "bad_request")
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(code, str(detail) if isinstance(detail, str) else None, rid),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        rid = getattr(request.state, "request_id", "-")
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        _record(request.method, request.url.path, 500, type(exc).__name__, str(exc))
        return JSONResponse(
            status_code=500,
            content=error_body("internal_error", None, rid),
        )


app = create_app()


def main() -> None:  # pragma: no cover - manual entry point
    import uvicorn

    configure_logging(get_settings().log_level)
    uvicorn.run(
        "backend.app.main:app",
        host=os.environ.get("NYAYMITRA_HOST", "0.0.0.0"),
        port=int(os.environ.get("NYAYMITRA_PORT", "8000")),
        reload=os.environ.get("NYAYMITRA_RELOAD", "0") == "1",
    )


if __name__ == "__main__":  # pragma: no cover
    main()
