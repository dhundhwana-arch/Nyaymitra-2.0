"""Provider registry and routing.

``build_provider`` decides, per request, which provider serves the call:

* ``NYAYMITRA_AI_PROVIDER=offline``  → deterministic provider, always.
* ``NYAYMITRA_AI_PROVIDER=openai_compatible`` with credentials → live provider.
* ``auto`` (default) → live provider when credentials exist, otherwise offline.

Routing is intentionally trivial (one task type today: "explain"), but the function is
the single place to add a second model/provider for a different task later.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings, get_settings
from .base import AIProvider, ProviderUnavailable
from .offline import OfflineGroundedProvider
from .openai_compatible import OpenAICompatibleProvider

TASKS = ("explain", "summarise_document")


@dataclass(frozen=True)
class ProviderInfo:
    name: str
    live: bool
    model: str | None
    fallback_mode: str


def build_provider(settings: Settings | None = None, task: str = "explain") -> AIProvider:
    settings = settings or get_settings()
    preference = settings.ai_provider
    if preference == "offline":
        return OfflineGroundedProvider()
    if preference in {"auto", "openai_compatible"}:
        candidate = OpenAICompatibleProvider(settings)
        if candidate.available():
            return candidate
        if preference == "openai_compatible":
            # Explicitly requested but not configured: fail loudly at call time so the
            # operator sees a configuration error instead of a silent downgrade.
            raise ProviderUnavailable("AI provider requested but credentials are missing")
    return OfflineGroundedProvider()


def describe(settings: Settings | None = None) -> ProviderInfo:
    settings = settings or get_settings()
    if settings.ai_provider == "offline":
        return ProviderInfo("offline", False, None, settings.ai_fallback_mode)
    if settings.ai_configured:
        return ProviderInfo(
            "openai_compatible", True, settings.ai_model, settings.ai_fallback_mode
        )
    return ProviderInfo("offline", False, None, settings.ai_fallback_mode)
