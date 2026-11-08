"""Application configuration.

All configuration comes from environment variables prefixed with ``NYAYMITRA_``.
No secret is ever hard-coded; absence of a secret disables the feature that needs it
instead of falling back to a default credential.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

TRUTHY = {"1", "true", "yes", "on"}


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(f"NYAYMITRA_{name}")
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    try:
        return int(raw) if raw is not None else default
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name)
    if raw is None:
        return default
    return raw.lower() in TRUTHY


def _env_path(name: str, default: Path) -> Path:
    raw = _env(name)
    return Path(raw).expanduser().resolve() if raw else default


def _env_list(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = _env(name)
    if not raw:
        return default
    return tuple(part.strip() for part in raw.split(",") if part.strip())


@dataclass(frozen=True)
class Settings:
    app_name: str = "NYAYMITRA 2.0"
    version: str = "2.1.0"
    environment: str = "development"
    api_prefix: str = "/api/v1"

    repo_root: Path = REPO_ROOT
    db_path: Path = REPO_ROOT / "data" / "nyaymitra.db"
    migrations_dir: Path = REPO_ROOT / "backend" / "migrations"
    storage_dir: Path = REPO_ROOT / "storage" / "documents"
    seed_dir: Path = REPO_ROOT / "data" / "seed"
    legacy_dir: Path = REPO_ROOT / "data" / "legacy"
    backup_dir: Path = REPO_ROOT / "backups"
    web_dir: Path = REPO_ROOT / "web"

    # --- auth -----------------------------------------------------------------
    admin_token: str | None = None
    monitor_token: str | None = None

    # --- ai -------------------------------------------------------------------
    ai_provider: str = "auto"  # auto | offline | openai_compatible
    ai_base_url: str | None = None
    ai_model: str | None = None
    ai_api_key: str | None = None
    ai_timeout_s: float = 20.0
    ai_max_output_tokens: int = 700
    # Retry policy for the live provider.
    ai_max_attempts: int = 2
    ai_retry_backoff_s: float = 0.5
    # strict  -> 503 when the configured provider fails
    # offline_grounded -> deterministic, citation-only fallback (never invented text)
    ai_fallback_mode: str = "offline_grounded"

    # --- http -----------------------------------------------------------------
    allowed_origins: tuple[str, ...] = ()
    serve_web: bool = True
    request_id_header: str = "X-Request-ID"
    max_body_bytes: int = 512 * 1024
    max_upload_bytes: int = 10 * 1024 * 1024
    allowed_upload_types: tuple[str, ...] = (
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
    )
    rate_limit_window_s: int = 60
    rate_limit_read: int = 120
    rate_limit_write: int = 30
    rate_limit_ai: int = 20
    rate_limit_admin: int = 10
    trust_proxy_headers: bool = False
    log_level: str = "INFO"
    pii_retention_days: int = 180
    duplicate_window_s: int = 600

    extra: dict = field(default_factory=dict)

    # -- derived ---------------------------------------------------------------
    @property
    def ai_configured(self) -> bool:
        return bool(self.ai_api_key and self.ai_base_url and self.ai_model)

    @property
    def admin_enabled(self) -> bool:
        return bool(self.admin_token)

    def public_url(self) -> str:
        return self.allowed_origins[0] if self.allowed_origins else "http://localhost:8000"

    # -- production preflight --------------------------------------------------
    def production_problems(self) -> list[str]:
        """Configuration that must fail loudly in production, never silently."""
        if self.environment.strip().lower() not in {"production", "prod"}:
            return []
        problems: list[str] = []
        placeholders = ("replace", "changeme", "change-me", "todo", "example", "test", "demo",
                        "secret", "password")

        def check_token(label: str, value: str | None) -> None:
            token = (value or "").strip()
            if not token:
                problems.append(f"{label} is not set")
                return
            if len(token) < 24:
                problems.append(f"{label} is shorter than 24 characters")
            lowered = token.lower()
            if any(word in lowered for word in placeholders):
                problems.append(f"{label} looks like a placeholder value")
            if len(set(token)) < 8:
                problems.append(f"{label} has too little variety to be random")

        check_token("NYAYMITRA_ADMIN_TOKEN", self.admin_token)
        check_token("NYAYMITRA_MONITOR_TOKEN", self.monitor_token)
        if self.admin_token and self.monitor_token and self.admin_token == self.monitor_token:
            problems.append("NYAYMITRA_ADMIN_TOKEN and NYAYMITRA_MONITOR_TOKEN are identical")

        try:
            db_path = Path(self.db_path).resolve()
            db_path.relative_to(REPO_ROOT)
        except ValueError:
            pass  # outside the repository: good
        else:
            problems.append(
                "NYAYMITRA_DB_PATH is inside the repository; point it at a data directory "
                "outside the checkout"
            )

        if self.trust_proxy_headers and not self.allowed_origins:
            problems.append(
                "NYAYMITRA_TRUST_PROXY_HEADERS is on but NYAYMITRA_ALLOWED_ORIGINS is empty; "
                "X-Forwarded-For would be trusted from any client"
            )
        return problems


def load_settings() -> Settings:
    provider = (_env("AI_PROVIDER", "auto") or "auto").lower()
    if provider not in {"auto", "offline", "openai_compatible"}:
        provider = "auto"
    fallback = (_env("AI_FALLBACK_MODE", "offline_grounded") or "offline_grounded").lower()
    if fallback not in {"strict", "offline_grounded"}:
        fallback = "offline_grounded"

    return Settings(
        environment=(_env("ENV", "development") or "development").lower(),
        api_prefix=_env("API_PREFIX", "/api/v1") or "/api/v1",
        db_path=_env_path("DB_PATH", REPO_ROOT / "data" / "nyaymitra.db"),
        migrations_dir=_env_path("MIGRATIONS_DIR", REPO_ROOT / "backend" / "migrations"),
        storage_dir=_env_path("STORAGE_DIR", REPO_ROOT / "storage" / "documents"),
        seed_dir=_env_path("SEED_DIR", REPO_ROOT / "data" / "seed"),
        legacy_dir=_env_path("LEGACY_DIR", REPO_ROOT / "data" / "legacy"),
        backup_dir=_env_path("BACKUP_DIR", REPO_ROOT / "backups"),
        web_dir=_env_path("WEB_DIR", REPO_ROOT / "web"),
        admin_token=_env("ADMIN_TOKEN"),
        monitor_token=_env("MONITOR_TOKEN"),
        ai_provider=provider,
        ai_base_url=_env("AI_BASE_URL"),
        ai_model=_env("AI_MODEL"),
        ai_api_key=_env("AI_API_KEY"),
        ai_timeout_s=float(_env_int("AI_TIMEOUT_S", 20)),
        ai_max_output_tokens=_env_int("AI_MAX_OUTPUT_TOKENS", 700),
        ai_max_attempts=max(1, min(_env_int("AI_MAX_ATTEMPTS", 2), 5)),
        ai_retry_backoff_s=max(0.0, min(float(_env_int("AI_RETRY_BACKOFF_MS", 500)) / 1000.0, 5.0)),
        ai_fallback_mode=fallback,
        allowed_origins=_env_list("ALLOWED_ORIGINS", ()),
        serve_web=_env_bool("SERVE_WEB", True),
        max_body_bytes=_env_int("MAX_BODY_BYTES", 512 * 1024),
        max_upload_bytes=_env_int("MAX_UPLOAD_BYTES", 10 * 1024 * 1024),
        rate_limit_window_s=_env_int("RATE_LIMIT_WINDOW_S", 60),
        rate_limit_read=_env_int("RATE_LIMIT_READ", 120),
        rate_limit_write=_env_int("RATE_LIMIT_WRITE", 30),
        rate_limit_ai=_env_int("RATE_LIMIT_AI", 20),
        rate_limit_admin=_env_int("RATE_LIMIT_ADMIN", 10),
        trust_proxy_headers=_env_bool("TRUST_PROXY_HEADERS", False),
        log_level=(_env("LOG_LEVEL", "INFO") or "INFO").upper(),
        pii_retention_days=_env_int("PII_RETENTION_DAYS", 180),
        duplicate_window_s=_env_int("DUPLICATE_WINDOW_S", 600),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


def reset_settings_cache() -> None:
    """Test helper — clears the memoised settings after env changes."""
    get_settings.cache_clear()
