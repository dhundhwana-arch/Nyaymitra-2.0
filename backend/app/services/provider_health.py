"""Provider health: one place that answers "will the AI actually answer right now?".

Used by two callers:

* ``GET /api/v1/admin/ai/health`` (monitor token) for the operator and any uptime checker,
* ``scripts/verify_ai_provider.py`` for a full end-to-end probe from a shell.

The distinction that matters: **configured** is not **reachable**, and **reachable** is not
**answering with grounded output**. This module reports the first two; the script reports the
third. Neither ever returns a canned answer, and no key is ever echoed.
"""
from __future__ import annotations

import time

from ..ai.registry import describe
from ..config import Settings

STATUS_OK = "ok"
STATUS_NOT_CONFIGURED = "not_configured"
STATUS_UNREACHABLE = "unreachable"


def probe_endpoint(settings: Settings, *, timeout: float = 3.0) -> dict:
    """Ask the configured base URL for its model list. No answer is generated here."""
    info: dict = {"reachable": False, "models": [], "detail": "", "latency_ms": None}
    if not settings.ai_base_url:
        info["detail"] = "no base URL configured"
        return info
    try:
        import httpx
    except ImportError:  # pragma: no cover - httpx is a runtime dependency
        info["detail"] = "httpx is not installed"
        return info

    url = settings.ai_base_url.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {settings.ai_api_key}"} if settings.ai_api_key else {}
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers)
    except Exception as exc:  # noqa: BLE001 - transport errors come in many types
        info["detail"] = f"could not reach the endpoint ({type(exc).__name__})"
        info["latency_ms"] = int((time.perf_counter() - started) * 1000)
        return info
    info["latency_ms"] = int((time.perf_counter() - started) * 1000)

    if response.status_code >= 400:
        # 404/405 means "this gateway does not implement /models" — reachable, but opaque.
        info["reachable"] = response.status_code in {404, 405}
        info["detail"] = f"/models returned HTTP {response.status_code}"
        return info

    info["reachable"] = True
    info["detail"] = "/models returned HTTP 200"
    try:
        payload = response.json()
    except ValueError:
        info["detail"] = "/models did not return JSON"
        return info
    rows = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(rows, list):
        info["models"] = [
            row.get("id") for row in rows if isinstance(row, dict) and row.get("id")
        ]
    return info


def health(settings: Settings, *, probe: bool = True, timeout: float = 3.0) -> dict:
    """Shape the health payload. ``probe=False`` reports configuration only."""
    info = describe(settings)
    payload: dict = {
        "provider": info.name,
        "live": info.live,
        "configured": bool(settings.ai_configured),
        "model": info.model,
        "fallback_mode": info.fallback_mode,
        "preference": settings.ai_provider,
        "base_url_set": bool(settings.ai_base_url),
        "api_key_set": bool(settings.ai_api_key),
        "status": STATUS_OK if info.live else STATUS_NOT_CONFIGURED,
        "detail": "live provider configured" if info.live else "offline grounded provider in use",
        "endpoint": None,
    }
    if not info.live:
        return payload
    if not probe:
        payload["detail"] = "configured; endpoint not probed"
        return payload

    endpoint = probe_endpoint(settings, timeout=timeout)
    payload["endpoint"] = endpoint
    if endpoint["reachable"]:
        payload["status"] = STATUS_OK
        payload["detail"] = endpoint["detail"]
        models = endpoint.get("models") or []
        if models and settings.ai_model and settings.ai_model not in models:
            # Reachable but the requested model is not installed: a very common failure that
            # otherwise shows up as an opaque 404 on the first real question.
            payload["status"] = STATUS_UNREACHABLE
            payload["detail"] = (
                f"endpoint is reachable but does not list the configured model "
                f"'{settings.ai_model}' (available: {', '.join(models[:5])})"
            )
    else:
        payload["status"] = STATUS_UNREACHABLE
        payload["detail"] = endpoint["detail"]
    return payload
